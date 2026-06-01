#!/usr/bin/env python3
"""
================================================================================
[04] Collect Logs - F5 AWAF Test Lab Factory
================================================================================
BIG-IP에서 WAF 보안 로그, Audit 로그, 요청 로그를 수집합니다.
  - Security Policy violations 로그 수집
  - ASM/WAF 공격 로그 수집
  - 로그를 JSON 파일로 저장 (output/logs/ 디렉토리)
  - 나중에 리포트 생성 시 활용

사용법:
    python 04_collect_logs.py

사전 조건:
    - 03_run_attack_tests.py 완료 (공격 테스트 실행)
================================================================================
"""

import sys
import json
import os
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta

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
logger = logging.getLogger("collect_logs")


def load_config() -> dict:
    """lab.yml 설정 파일을 로드합니다."""
    config_path = Path(__file__).resolve().parent.parent / "lab.yml"
    if not config_path.exists():
        logger.error(f"설정 파일을 찾을 수 없습니다: {config_path}")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def collect_security_logs(bigip: dict, config: dict) -> list:
    """WAF Security 로그를 수집합니다."""
    host = bigip["host"]
    port = bigip.get("port", 443)
    username = bigip["username"]
    password = bigip["password"]
    verify = bigip.get("validate_certs", False)

    log_config = config["log_collection"]
    lookback_minutes = log_config.get("lookback_minutes", 30)

    # ASM 로그 조회 API
    url = f"https://{host}:{port}/mgmt/tm/asm/log/attacks"
    params = {
        "$filter": f"generationTime+ge+{int((datetime.now() - timedelta(minutes=lookback_minutes)).timestamp() * 1000)}",
        "$top": 500,
        "$orderby": "generationTime+desc",
    }

    logger.info(f"Security 로그 수집 중 (최근 {lookback_minutes}분)...")

    try:
        resp = requests.get(
            url,
            auth=(username, password),
            params=params,
            verify=verify,
            timeout=30
        )

        if resp.status_code == 200:
            data = resp.json()
            items = data.get("items", [])
            logger.info(f"✅ Security 로그 수집 완료: {len(items)}개 발견")

            # 로그 요약 출력
            if items:
                violation_counts = {}
                for item in items:
                    sig_name = item.get("signatureName", "Unknown")
                    violation_counts[sig_name] = violation_counts.get(sig_name, 0) + 1

                print("\n  [탐지된 공격 유형]")
                for sig_name, count in sorted(violation_counts.items(), key=lambda x: -x[1])[:10]:
                    print(f"    - {sig_name}: {count}회")

            return items
        else:
            logger.warning(f"⚠️ Security 로그 수집 실패 (HTTP {resp.status_code})")
            return []

    except Exception as e:
        logger.warning(f"⚠️ Security 로그 수집 오류: {e}")
        return []


def collect_audit_logs(bigip: dict, config: dict) -> list:
    """Audit 로그를 수집합니다."""
    host = bigip["host"]
    port = bigip.get("port", 443)
    username = bigip["username"]
    password = bigip["password"]
    verify = bigip.get("validate_certs", False)

    log_config = config["log_collection"]
    lookback_minutes = log_config.get("lookback_minutes", 30)

    url = f"https://{host}:{port}/mgmt/tm/sys/log/audit"
    params = {
        "$filter": f"creationTime+ge+{int((datetime.now() - timedelta(minutes=lookback_minutes)).timestamp())}",
        "$top": 200,
    }

    logger.info("Audit 로그 수집 중...")

    try:
        resp = requests.get(
            url,
            auth=(username, password),
            params=params,
            verify=verify,
            timeout=30
        )

        if resp.status_code == 200:
            data = resp.json()
            items = data.get("items", [])
            logger.info(f"✅ Audit 로그 수집 완료: {len(items)}개 발견")
            return items
        else:
            logger.warning(f"⚠️ Audit 로그 수집 실패 (HTTP {resp.status_code})")
            return []

    except Exception as e:
        logger.warning(f"⚠️ Audit 로그 수집 오류: {e}")
        return []


def collect_request_logs(bigip: dict, config: dict) -> list:
    """HTTP Request 로그를 수집합니다."""
    host = bigip["host"]
    port = bigip.get("port", 443)
    username = bigip["username"]
    password = bigip["password"]
    verify = bigip.get("validate_certs", False)

    log_config = config["log_collection"]
    lookback_minutes = log_config.get("lookback_minutes", 30)

    url = f"https://{host}:{port}/mgmt/tm/asm/log/requests"
    params = {
        "$filter": f"requestTime+ge+{int((datetime.now() - timedelta(minutes=lookback_minutes)).timestamp() * 1000)}",
        "$top": 500,
        "$orderby": "requestTime+desc",
    }

    logger.info("HTTP Request 로그 수집 중...")

    try:
        resp = requests.get(
            url,
            auth=(username, password),
            params=params,
            verify=verify,
            timeout=30
        )

        if resp.status_code == 200:
            data = resp.json()
            items = data.get("items", [])
            logger.info(f"✅ Request 로그 수집 완료: {len(items)}개 발견")
            return items
        else:
            logger.warning(f"⚠️ Request 로그 수집 실패 (HTTP {resp.status_code})")
            return []

    except Exception as e:
        logger.warning(f"⚠️ Request 로그 수집 오류: {e}")
        return []


def save_logs(logs: dict, config: dict):
    """수집된 로그를 JSON 파일로 저장합니다."""
    output_dir = Path(__file__).resolve().parent.parent / "output" / "logs"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for log_type, entries in logs.items():
        if entries:
            output_path = output_dir / f"{log_type}_{timestamp}.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump({
                    "type": log_type,
                    "collected_at": datetime.now().isoformat(),
                    "target_vip": config["target"]["vip_address"],
                    "count": len(entries),
                    "entries": entries,
                }, f, indent=2, ensure_ascii=False, default=str)
            logger.info(f"✅ {log_type} 로그 저장 완료: {output_path}")

    # 최신 로그 심볼릭 링크 (latest)
    for log_type, entries in logs.items():
        if entries:
            latest_path = output_dir / f"{log_type}_latest.json"
            actual_path = output_dir / f"{log_type}_{timestamp}.json"
            try:
                if latest_path.exists():
                    latest_path.unlink()
                os.link(str(actual_path), str(latest_path))  # 하드링크 (Windows)
            except Exception:
                pass


def main():
    """메인 함수: 로그 수집 파이프라인을 실행합니다."""
    logger.info("=" * 60)
    logger.info("[04] Collect Logs 시작")
    logger.info("=" * 60)

    config = load_config()
    bigip = config["bigip"]

    # 수집할 로그 타입 결정
    log_types = config.get("log_collection", {}).get("types", ["security"])

    logs = {}

    if "security" in log_types:
        logs["security"] = collect_security_logs(bigip, config)

    if "audit" in log_types:
        logs["audit"] = collect_audit_logs(bigip, config)

    if "request" in log_types:
        logs["request"] = collect_request_logs(bigip, config)

    # 저장
    save_logs(logs, config)

    # 요약
    total = sum(len(entries) for entries in logs.values())
    print("\n" + "=" * 60)
    print(f"📋 로그 수집 완료: 총 {total}개 로그")
    print("=" * 60)
    for log_type, entries in logs.items():
        print(f"  - {log_type}: {len(entries)}개")

    print("\n다음 단계: python 05_generate_report.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
