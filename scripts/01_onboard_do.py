#!/usr/bin/env python3
"""
================================================================================
[01] Declarative Onboarding - F5 AWAF Test Lab Factory
================================================================================
DO (Declarative Onboarding)를 사용하여 BIG-IP 초기 구성을 자동화합니다.
  - lab.yml 설정 기반 DO JSON 템플릿 렌더링
  - BIG-IP에 DO 선언 제출 (POST)
  - 비동기 작업 완료 대기 (polling)
  - 렌더링된 JSON을 output/ 디렉토리에 저장

사용법:
    python 01_onboard_do.py

사전 조건:
    - 00_check_bigip_ready.py 통과
    - DO (Declarative Onboarding) 패키지가 BIG-IP에 설치됨
================================================================================
"""

import sys
import json
import time
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml
import requests
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning

disable_warnings(InsecureRequestWarning)

# --- 로깅 설정 ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("do_onboard")


def load_config() -> dict:
    """lab.yml 설정 파일을 로드합니다."""
    config_path = Path(__file__).resolve().parent.parent / "lab.yml"
    if not config_path.exists():
        logger.error(f"설정 파일을 찾을 수 없습니다: {config_path}")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def render_template(config: dict) -> dict:
    """DO Jinja2 템플릿을 렌더링합니다."""
    base_dir = Path(__file__).resolve().parent.parent
    template_dir = base_dir / "declarations"
    output_dir = base_dir / "output"

    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True
    )

    template_file = "do_awaf_lab.json.j2"
    logger.info(f"DO 템플릿 렌더링 중: {template_file}")

    try:
        template = env.get_template(template_file)
        rendered = template.render(lab=config)

        # JSON 유효성 검증
        do_declaration = json.loads(rendered)

        # 렌더링 결과 저장
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "do_rendered.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(do_declaration, f, indent=4, ensure_ascii=False)

        logger.info(f"✅ DO 선언 렌더링 완료: {output_path}")
        return do_declaration

    except Exception as e:
        logger.error(f"❌ 템플릿 렌더링 실패: {e}")
        sys.exit(1)


def submit_do_declaration(bigip: dict, declaration: dict) -> str:
    """DO 선언을 BIG-IP에 제출하고 작업 ID를 반환합니다."""
    host = bigip["host"]
    port = bigip.get("port", 443)
    username = bigip["username"]
    password = bigip["password"]
    verify = bigip.get("validate_certs", False)

    url = f"https://{host}:{port}/mgmt/shared/declarative-onboarding"
    headers = {
        "Content-Type": "application/json"
    }

    logger.info("DO 선언 제출 중...")
    logger.info(f"  URL: {url}")

    try:
        resp = requests.post(
            url,
            auth=(username, password),
            headers=headers,
            json=declaration,
            verify=verify,
            timeout=30
        )

        if resp.status_code == 200:
            result = resp.json()
            job_id = result.get("id", result.get("result", {}).get("id", "unknown"))
            logger.info(f"✅ DO 선언 제출 성공 (작업 ID: {job_id})")
            return job_id
        else:
            logger.error(f"❌ DO 선언 제출 실패 (HTTP {resp.status_code})")
            logger.error(f"응답: {resp.text[:500]}")
            sys.exit(1)

    except requests.exceptions.Timeout:
        logger.error("❌ DO 선언 제출 시간 초과")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ DO 선언 제출 오류: {e}")
        sys.exit(1)


def wait_for_completion(bigip: dict, job_id: str, max_retries: int = 60, interval: int = 10) -> bool:
    """DO 작업이 완료될 때까지 대기합니다."""
    host = bigip["host"]
    port = bigip.get("port", 443)
    username = bigip["username"]
    password = bigip["password"]
    verify = bigip.get("validate_certs", False)

    url = f"https://{host}:{port}/mgmt/shared/declarative-onboarding/{job_id}"

    logger.info(f"DO 작업 완료 대기 중 (최대 {max_retries * interval}초)...")

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(
                url,
                auth=(username, password),
                verify=verify,
                timeout=10
            )

            if resp.status_code == 200:
                result = resp.json()
                status = result.get("result", {}).get("status", "UNKNOWN")

                if status == "FINISHED":
                    logger.info(f"✅ DO 작업 완료! (시도 {attempt}회)")
                    return True
                elif status == "ERROR":
                    errors = result.get("result", {}).get("errors", [])
                    err_msg = errors[0].get("message", "알 수 없는 오류") if errors else "알 수 없는 오류"
                    logger.error(f"❌ DO 작업 실패: {err_msg}")
                    return False
                else:
                    logger.info(f"  진행 중... 상태: {status} (시도 {attempt}/{max_retries})")

            time.sleep(interval)

        except Exception as e:
            logger.warning(f"  상태 확인 중 오류 (시도 {attempt}): {e}")
            time.sleep(interval)

    logger.error("❌ DO 작업 시간 초과")
    return False


def main():
    """메인 함수: DO 온보딩 파이프라인을 실행합니다."""
    logger.info("=" * 60)
    logger.info("[01] Declarative Onboarding 시작")
    logger.info("=" * 60)

    config = load_config()
    bigip = config["bigip"]

    # 1. 템플릿 렌더링
    do_declaration = render_template(config)

    # 2. DO 선언 제출
    job_id = submit_do_declaration(bigip, do_declaration)

    # 3. 작업 완료 대기
    success = wait_for_completion(bigip, job_id)

    if success:
        print("\n" + "=" * 60)
        print("🎉 DO 온보딩이 성공적으로 완료되었습니다!")
        print("다음 단계: python 02_deploy_as3.py")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("❌ DO 온보딩에 실패했습니다.")
        print("BIG-IP 로그를 확인하세요: /var/log/restnoded/restnoded.log")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
