#!/usr/bin/env python3
"""
================================================================================
[03] Run Attack Tests - F5 AWAF Test Lab Factory
================================================================================
tests/ 디렉토리의 YAML 테스트 정의 파일을 읽어 DVWA 애플리케이션에
보안 공격을 시뮬레이션하고 WAF 탐지 결과를 수집합니다.
  - YAML 테스트 정의 로드 (SQLi, XSS, File Inclusion 등)
  - DVWA에 실제 공격 페이로드 전송
  - 각 테스트 결과를 output/test_result.json에 저장

사용법:
    python 03_run_attack_tests.py              # 모든 테스트 실행
    python 03_run_attack_tests.py --test sqli  # 특정 테스트만 실행
    python 03_run_attack_tests.py --dry-run    # 실제 전송 없이 시뮬레이션

사전 조건:
    - 02_deploy_as3.py 완료 (DVWA VIP 접속 가능)
    - DVWA 컨테이너 실행 중
================================================================================
"""

import sys
import json
import re
import time
import random
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml
import requests
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning

disable_warnings(InsecureRequestWarning)

# --- 로깅 설정 ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("attack_tests")

# 전역 통계
STATS = {
    "total": 0,
    "sent": 0,
    "failed": 0,
    "waf_triggered": 0,
    "start_time": None,
    "end_time": None,
}


def load_config() -> dict:
    """lab.yml 설정 파일을 로드합니다."""
    config_path = Path(__file__).resolve().parent.parent / "lab.yml"
    if not config_path.exists():
        logger.error(f"설정 파일을 찾을 수 없습니다: {config_path}")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_test_definitions(test_name: Optional[str] = None) -> list:
    """tests/ 디렉토리에서 YAML 테스트 정의를 로드합니다."""
    tests_dir = Path(__file__).resolve().parent.parent / "tests"
    if not tests_dir.exists():
        logger.error(f"테스트 디렉토리를 찾을 수 없습니다: {tests_dir}")
        sys.exit(1)

    test_files = sorted(tests_dir.glob("*.yml"))

    if test_name:
        test_name = test_name.lower().replace(" ", "_")
        test_files = [f for f in test_files if test_name in f.stem.lower()]
        if not test_files:
            logger.error(f"테스트를 찾을 수 없습니다: {test_name}")
            logger.info(f"사용 가능한 테스트: {[f.stem for f in sorted(tests_dir.glob('*.yml'))]}")
            sys.exit(1)

    tests = []
    for test_file in test_files:
        with open(test_file, "r", encoding="utf-8") as f:
            test_data = yaml.safe_load(f)
            tests.append(test_data)
            logger.info(f"  📄 {test_file.name}: {test_data.get('description', '')} ({len(test_data.get('tests', []))}개 케이스)")

    return tests


def login_dvwa(config: dict, session: requests.Session) -> bool:
    """DVWA에 로그인하고 세션을 설정합니다."""
    dvwa_config = config["target"]["dvwa"]
    login_url = f"{dvwa_config['url']}/login.php"

    logger.info(f"DVWA 로그인 중: {login_url}")

    try:
        # CSRF 토큰 획득
        resp = session.get(login_url, timeout=10)
        if resp.status_code != 200:
            logger.warning(f"⚠️ DVWA 로그인 페이지 로드 실패 (HTTP {resp.status_code})")
            return False

        # CSRF 토큰 추출 (DVWA 기본 방식)
        user_token = ""
        match = re.search(r'name="user_token"\s*value="([^"]+)"', resp.text)
        if match:
            user_token = match.group(1)

        # 로그인 요청
        login_data = {
            "username": dvwa_config.get("username", "admin"),
            "password": dvwa_config.get("password", "password"),
            "Login": "Login",
            "user_token": user_token,
        }

        resp = session.post(login_url, data=login_data, timeout=10)

        if "Login" not in resp.text or "failed" not in resp.text.lower():
            logger.info("✅ DVWA 로그인 성공")
            return True
        else:
            logger.warning("⚠️ DVWA 로그인 실패")
            return False

    except Exception as e:
        logger.warning(f"⚠️ DVWA 로그인 중 오류: {e}")
        return False


def set_security_level(config: dict, session: requests.Session) -> bool:
    """DVWA 보안 레벨을 설정합니다."""
    dvwa_config = config["target"]["dvwa"]
    level = dvwa_config.get("security_level", "low")
    url = f"{dvwa_config['url']}/security.php"

    logger.info(f"DVWA 보안 레벨 설정: {level}")

    try:
        resp = session.post(
            url,
            data={"security": level, "seclev_submit": "Submit"},
            timeout=10
        )
        logger.info(f"✅ 보안 레벨 '{level}' 설정 완료")
        return True
    except Exception as e:
        logger.warning(f"⚠️ 보안 레벨 설정 실패: {e}")
        return False


def execute_test_case(
    config: dict,
    session: requests.Session,
    test_def: dict,
    test_case: dict,
    dry_run: bool = False
) -> dict:
    """단일 테스트 케이스를 실행합니다."""
    app_url = config["target"]["dvwa"]["url"]
    dvwa_config = config["target"]["dvwa"]
    attack_config = config["attack_tests"]

    method = test_case.get("method", "GET").upper()
    path = test_case.get("path", "/")
    params = test_case.get("params", {})
    headers = test_case.get("headers", {})
    body = test_case.get("body", None)
    description = test_case.get("description", "")
    category = test_def.get("category", "unknown")

    url = f"{dvwa_config['url']}{path}"
    repeat = test_case.get("repeat", attack_config.get("repeat_count", 3))
    user_agent = test_case.get("user_agent", None)

    # User-Agent 랜덤 생성
    if attack_config.get("random_user_agent", True) and not user_agent:
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/17.2",
            "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Edge/120.0.0.0",
        ]
        user_agent = random.choice(user_agents)

    result = {
        "category": category,
        "test_id": test_case.get("id", ""),
        "description": description,
        "method": method,
        "url": url,
        "params": params,
        "severity": test_case.get("severity", "medium"),
        "repeat_count": 0,
        "responses": [],
        "waf_detected": False,
        "error": None,
    }

    # 요청 헤더 설정
    request_headers = {
        "User-Agent": user_agent,
    }
    request_headers.update(headers)

    # 공격 소스 IP (X-Forwarded-For)
    if "X-Forwarded-For" not in request_headers:
        request_headers["X-Forwarded-For"] = attack_config.get("source_ip", "192.168.1.10")

    logger.info(f"  [{category}] {description} ({method} {path})")

    if dry_run:
        logger.info(f"    [DRY-RUN] Params: {params}")
        result["dry_run"] = True
        return result

    # 반복 전송
    delay = attack_config.get("delay_between_tests", 1)
    timeout = attack_config.get("test_timeout", 30)

    for i in range(repeat):
        try:
            if method == "GET":
                resp = session.get(
                    url,
                    params=params,
                    headers=request_headers,
                    timeout=timeout
                )
            elif method == "POST":
                resp = session.post(
                    url,
                    data=params if not body else body,
                    headers=request_headers,
                    timeout=timeout
                )
            else:
                resp = session.request(
                    method,
                    url,
                    params=params,
                    data=params if not body else body,
                    headers=request_headers,
                    timeout=timeout
                )

            # WAF 탐지 여부 확인 (응답 코드 403 또는 응답 본문에 WAF 차단 메시지)
            waf_detected = False

            # 1) HTTP 403 응답은 WAF 차단으로 간주
            if resp.status_code == 403:
                waf_detected = True

            # 2) 응답 본문에서 WAF 차단 페이지 확인
            waf_indicators = [
                "rejected", "blocked", "malicious", "attack detected",
                "violation", "access denied", "F5 Networks", "ASM",
                "AWAF", "security policy", "illegal", "위반", "차단"
            ]
            resp_text_lower = resp.text.lower() if resp.text else ""
            for indicator in waf_indicators:
                if indicator.lower() in resp_text_lower:
                    waf_detected = True
                    break

            # 3) 응답 헤더에서 WAF 확인
            if "X-WAF-Rejected" in resp.headers or "X-ASM-Rejected" in resp.headers:
                waf_detected = True

            response_info = {
                "status_code": resp.status_code,
                "length": len(resp.text),
                "elapsed": resp.elapsed.total_seconds(),
                "headers": dict(resp.headers),
                "waf_detected": waf_detected,
            }

            result["responses"].append(response_info)
            result["repeat_count"] += 1

            if waf_detected:
                result["waf_detected"] = True

            # 로그 출력
            waf_icon = "🛡️ " if waf_detected else "⚠️ " if resp.status_code >= 400 else "  "
            logger.info(f"    [{i+1}/{repeat}] {waf_icon} HTTP {resp.status_code} ({resp.elapsed.total_seconds():.2f}s)")
            STATS["sent"] += 1

            # 짧은 지연
            if i < repeat - 1:
                time.sleep(delay)

        except requests.exceptions.Timeout:
            logger.warning(f"    [{i+1}/{repeat}] ⏱️  시간 초과")
            result["responses"].append({
                "status_code": 0,
                "error": "timeout",
                "waf_detected": False,
            })
            STATS["failed"] += 1

        except Exception as e:
            logger.warning(f"    [{i+1}/{repeat}] ❌ 오류: {e}")
            result["responses"].append({
                "status_code": 0,
                "error": str(e),
                "waf_detected": False,
            })
            STATS["failed"] += 1

    if result["waf_detected"]:
        STATS["waf_triggered"] += 1

    return result


def run_tests(config: dict, test_defs: list, dry_run: bool = False) -> list:
    """모든 테스트 정의를 실행하고 결과 목록을 반환합니다."""
    results = []
    attack_config = config["attack_tests"]
    delay = attack_config.get("delay_between_tests", 1)

    session = requests.Session()

    # DVWA 로그인
    dvwa_config = config["target"]["dvwa"]
    if dvwa_config.get("url") and not dry_run:
        login_dvwa(config, session)
        set_security_level(config, session)

    for test_def in test_defs:
        category = test_def.get("category", "unknown")
        test_cases = test_def.get("tests", [])
        total = len(test_cases)

        print(f"\n--- [{category}] {total}개 테스트 케이스 실행 ---")

        for i, test_case in enumerate(test_cases):
            STATS["total"] += 1

            result = execute_test_case(config, session, test_def, test_case, dry_run)
            results.append(result)

            # 테스트 간 지연
            if i < total - 1:
                time.sleep(delay)

    session.close()
    return results


def save_results(results: list, config: dict):
    """테스트 결과를 JSON 파일로 저장합니다."""
    output_dir = Path(__file__).resolve().parent.parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "test_result.json"

    summary = {
        "timestamp": datetime.now().isoformat(),
        "target": {
            "vip": config["target"]["vip_address"],
            "port": config["target"]["vip_port"],
            "dvwa_url": config["target"]["dvwa"]["url"],
            "security_level": config["target"]["dvwa"]["security_level"],
        },
        "stats": STATS,
        "results": results,
    }

    # datetime을 직렬화 가능하게 변환
    class DateTimeEncoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, datetime):
                return o.isoformat()
            return super().default(o)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)

    logger.info(f"\n✅ 테스트 결과 저장 완료: {output_path}")


def print_summary():
    """테스트 실행 요약을 출력합니다."""
    elapsed = datetime.now() - STATS["start_time"]
    minutes, seconds = divmod(int(elapsed.total_seconds()), 60)

    waf_rate = (STATS["waf_triggered"] / STATS["total"] * 100) if STATS["total"] > 0 else 0.0

    print("\n" + "=" * 60)
    print("📊 테스트 실행 결과 요약")
    print("=" * 60)
    print(f"  총 테스트 케이스: {STATS['total']}")
    print(f"  전송 성공:        {STATS['sent']}")
    print(f"  전송 실패:        {STATS['failed']}")
    print(f"  🛡️  WAF 탐지:     {STATS['waf_triggered']} ({waf_rate:.1f}%)")
    print(f"  소요 시간:        {minutes}분 {seconds}초")
    print("=" * 60)

    if waf_rate < 50:
        print("⚠️  WAF 탐지율이 낮습니다. WAF 정책을 확인하세요!")
    elif waf_rate < 80:
        print("📈 WAF가 대부분의 공격을 탐지했습니다.")
    else:
        print("🎉 WAF가 높은 탐지율을 보이고 있습니다!")
    print("=" * 60)


def main():
    """메인 함수: 공격 테스트를 실행합니다."""
    parser = argparse.ArgumentParser(description="F5 AWAF Test Lab - Attack Test Runner")
    parser.add_argument("--test", "-t", help="특정 테스트만 실행 (예: sqli, xss)")
    parser.add_argument("--dry-run", "-n", action="store_true", help="실제 전송 없이 시뮬레이션")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("[03] Run Attack Tests 시작")
    logger.info("=" * 60)

    config = load_config()
    STATS["start_time"] = datetime.now()

    # 1. 테스트 정의 로드
    print("\n--- 테스트 정의 로드 ---")
    test_defs = load_test_definitions(args.test)

    # 2. 테스트 실행
    print(f"\n--- 테스트 실행 (Dry-Run: {args.dry_run}) ---")
    results = run_tests(config, test_defs, args.dry_run)

    STATS["end_time"] = datetime.now()

    # 3. 결과 저장
    if not args.dry_run:
        save_results(results, config)

    # 4. 요약 출력
    print_summary()

    if args.dry_run:
        print("\n💡 실제 테스트를 실행하려면 --dry-run 옵션을 제거하세요.")
        print("   python 03_run_attack_tests.py")

    next_step = "다음 단계: python 04_collect_logs.py" if not args.dry_run else ""
    if next_step:
        print(f"\n{next_step}")


if __name__ == "__main__":
    main()
