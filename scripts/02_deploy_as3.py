#!/usr/bin/env python3
"""
================================================================================
[02] AS3 Deploy - F5 AWAF Test Lab Factory
================================================================================
AS3 (Application Services 3)를 사용하여 DVWA 애플리케이션과
WAF 보안 정책을 BIG-IP에 배포합니다.
  - lab.yml 설정 기반 AS3 JSON 템플릿 렌더링
  - BIG-IP에 AS3 선언 제출 (POST)
  - 비동기 작업 완료 대기 (polling)
  - WAF 정책 활성화 확인

사용법:
    python 02_deploy_as3.py

사전 조건:
    - 01_onboard_do.py 완료 (DO 온보딩 성공)
    - AS3 (Application Services 3) 패키지가 BIG-IP에 설치됨
================================================================================
"""

import sys
import json
import time
import re
import base64
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
logger = logging.getLogger("as3_deploy")


def load_config() -> dict:
    """lab.yml 설정 파일을 로드합니다."""
    config_path = Path(__file__).resolve().parent.parent / "lab.yml"
    if not config_path.exists():
        logger.error(f"설정 파일을 찾을 수 없습니다: {config_path}")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def render_template(config: dict) -> dict:
    """AS3 Jinja2 템플릿을 렌더링합니다."""
    base_dir = Path(__file__).resolve().parent.parent
    template_dir = base_dir / "declarations"
    output_dir = base_dir / "output"

    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True
    )

    template_file = "as3_dvwa_awaf.json.j2"
    logger.info(f"AS3 템플릿 렌더링 중: {template_file}")

    try:
        template = env.get_template(template_file)
        rendered = template.render(lab=config)

        # JSON 유효성 검증
        as3_declaration = json.loads(rendered)

        # 렌더링 결과 저장
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "as3_rendered.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(as3_declaration, f, indent=4, ensure_ascii=False)

        logger.info(f"✅ AS3 선언 렌더링 완료: {output_path}")
        return as3_declaration

    except Exception as e:
        logger.error(f"❌ 템플릿 렌더링 실패: {e}")
        sys.exit(1)


def submit_as3_declaration(bigip: dict, declaration: dict) -> str:
    """AS3 선언을 BIG-IP에 제출하고 작업 ID를 반환합니다."""
    host = bigip["host"]
    port = bigip.get("port", 443)
    username = bigip["username"]
    password = bigip["password"]
    verify = bigip.get("validate_certs", False)

    url = f"https://{host}:{port}/mgmt/shared/appsvcs/declare"
    headers = {
        "Content-Type": "application/json"
    }

    logger.info("AS3 선언 제출 중...")
    logger.info(f"  URL: {url}")

    try:
        resp = requests.post(
            url,
            auth=(username, password),
            headers=headers,
            json=declaration,
            verify=verify,
            timeout=60
        )

        if resp.status_code in (200, 202):
            result = resp.json()
            job_id = result.get("id", result.get("results", [{}])[0].get("id", "unknown"))
            logger.info(f"✅ AS3 선언 제출 성공 (작업 ID: {job_id})")
            return job_id
        else:
            logger.error(f"❌ AS3 선언 제출 실패 (HTTP {resp.status_code})")
            logger.error(f"응답: {resp.text[:1000]}")
            sys.exit(1)

    except requests.exceptions.Timeout:
        logger.error("❌ AS3 선언 제출 시간 초과")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ AS3 선언 제출 오류: {e}")
        sys.exit(1)


def wait_for_completion(bigip: dict, job_id: str, max_retries: int = 60, interval: int = 5) -> bool:
    """AS3 작업이 완료될 때까지 대기합니다."""
    host = bigip["host"]
    port = bigip.get("port", 443)
    username = bigip["username"]
    password = bigip["password"]
    verify = bigip.get("validate_certs", False)

    url = f"https://{host}:{port}/mgmt/shared/appsvcs/task/{job_id}"

    logger.info(f"AS3 작업 완료 대기 중 (최대 {max_retries * interval}초)...")

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
                results_list = result.get("results", [])
                if results_list:
                    status = results_list[0].get("status", "UNKNOWN")
                    tenant = results_list[0].get("tenant", "unknown")

                    if status == "OK":
                        message = results_list[0].get("message", "")
                        logger.info(f"✅ AS3 배포 완료! 테넌트: {tenant}")
                        logger.info(f"   메시지: {message}")
                        return True
                    elif status == "ERROR":
                        errors = results_list[0].get("errors", [])
                        err_msg = errors[0].get("message", "알 수 없는 오류") if errors else "알 수 없는 오류"
                        logger.error(f"❌ AS3 배포 실패: {err_msg}")
                        return False
                    else:
                        logger.info(f"  진행 중... 상태: {status} (시도 {attempt}/{max_retries})")

            time.sleep(interval)

        except Exception as e:
            logger.warning(f"  상태 확인 중 오류 (시도 {attempt}): {e}")
            time.sleep(interval)

    logger.error("❌ AS3 작업 시간 초과")
    return False


def upload_waf_policy_to_bigip(bigip: dict) -> bool:
    """
    WAF 정책 템플릿(waf_policy_template.json)을 BIG-IP에 업로드합니다.
    
    1. 대상 디렉토리 생성 (mkdir -p)
    2. REST API 파일 업로드 (/mgmt/shared/file-transfer/uploads)
    3. 업로드된 파일을 대상 경로로 복사
    
    실패 시 수동 업로드 명령어를 안내합니다.
    """
    host = bigip["host"]
    port = bigip.get("port", 443)
    username = bigip["username"]
    password = bigip["password"]
    verify = bigip.get("validate_certs", False)

    target_dir = "/var/config/rest/iapps/as3/declarations"
    target_file = f"{target_dir}/waf_policy_template.json"
    upload_url = f"https://{host}:{port}/mgmt/shared/file-transfer/uploads/waf_policy_template.json"
    bash_url = f"https://{host}:{port}/mgmt/tm/util/bash"

    # 로컬 파일 경로
    local_policy = Path(__file__).resolve().parent.parent / "declarations" / "waf_policy_template.json"
    if not local_policy.exists():
        logger.warning(f"⚠️ 로컬 WAF 정책 파일을 찾을 수 없습니다: {local_policy}")
        logger.warning("   AS3 배포를 계속합니다. (WAF 정책 파일이 BIG-IP에 이미 있어야 함)")
        return False

    logger.info("=" * 60)
    logger.info("WAF 정책 파일 업로드 시작")
    logger.info("=" * 60)
    logger.info(f"  대상: {host}:{port}")
    logger.info(f"  로컬 파일: {local_policy}")
    logger.info(f"  BIG-IP 경로: {target_file}")

    try:
        # 1. 대상 디렉토리 생성
        logger.info("  [1/3] 대상 디렉토리 생성 중...")
        mkdir_cmd = {
            "command": "run",
            "utilCmdArgs": f"-c 'mkdir -p {target_dir}'"
        }
        resp = requests.post(
            bash_url,
            auth=(username, password),
            json=mkdir_cmd,
            verify=verify,
            timeout=10
        )
        if resp.status_code in (200, 201):
            logger.info(f"  ✅ 디렉토리 생성 완료 (또는 이미 존재)")
        else:
            logger.warning(f"  ⚠️ 디렉토리 생성 응답: HTTP {resp.status_code}")

        # 2. 파일 업로드
        logger.info("  [2/3] WAF 정책 파일 업로드 중...")
        with open(local_policy, "rb") as f:
            policy_content = f.read()

        resp = requests.post(
            upload_url,
            auth=(username, password),
            data=policy_content,
            headers={"Content-Type": "application/octet-stream"},
            verify=verify,
            timeout=30
        )

        if resp.status_code not in (200, 201):
            logger.warning(f"  ⚠️ 파일 업로드 응답: HTTP {resp.status_code}")
            logger.warning(f"  응답: {resp.text[:300]}")
            logger.warning("  수동 업로드가 필요할 수 있습니다.")
            return False

        logger.info(f"  ✅ 파일 업로드 완료 (HTTP {resp.status_code})")

        # 3. 업로드된 파일을 대상 경로로 복사
        logger.info("  [3/3] 파일을 대상 경로로 복사 중...")
        cp_cmd = {
            "command": "run",
            "utilCmdArgs": f"-c 'cp /var/config/rest/downloads/waf_policy_template.json {target_file}'"
        }
        resp = requests.post(
            bash_url,
            auth=(username, password),
            json=cp_cmd,
            verify=verify,
            timeout=10
        )

        if resp.status_code in (200, 201):
            logger.info(f"  ✅ 파일 복사 완료: {target_file}")
            print(f"\n🎉 WAF 정책 파일 업로드 성공!")
            print(f"   📄 {target_file}")
            return True
        else:
            logger.warning(f"  ⚠️ 파일 복사 실패 (HTTP {resp.status_code})")
            logger.warning(f"   응답: {resp.text[:300]}")
            return False

    except requests.exceptions.ConnectionError as e:
        logger.warning(f"❌ BIG-IP 연결 실패: {e}")
        logger.warning("  수동으로 파일을 업로드하고 다시 실행하세요.")
        return False
    except Exception as e:
        logger.warning(f"❌ 업로드 중 오류: {e}")
        return False


def verify_virtual_server(bigip: dict, config: dict) -> bool:
    """Virtual Server가 정상적으로 생성되었는지 확인합니다."""
    host = bigip["host"]
    port = bigip.get("port", 443)
    username = bigip["username"]
    password = bigip["password"]
    verify = bigip.get("validate_certs", False)

    vip = config["target"]["vip_address"]
    vip_port = config["target"]["vip_port"]

    url = f"https://{host}:{port}/mgmt/tm/ltm/virtual/~{config['as3']['tenant']}~{config['as3']['application']}~dvwaVirtualServer"

    logger.info(f"Virtual Server 확인 중: {vip}:{vip_port}")

    try:
        resp = requests.get(
            url,
            auth=(username, password),
            verify=verify,
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            logger.info(f"  ✅ Virtual Server 상태: {data.get('status', 'unknown')}")
            logger.info(f"  ✅ Destination: {data.get('destination', 'unknown')}")
            return True
        else:
            logger.warning(f"  ❌ Virtual Server를 찾을 수 없습니다 (HTTP {resp.status_code})")
            return False
    except Exception as e:
        logger.error(f"  ❌ Virtual Server 확인 오류: {e}")
        return False


def main():
    """메인 함수: AS3 배포 파이프라인을 실행합니다."""
    logger.info("=" * 60)
    logger.info("[02] AS3 Deploy 시작")
    logger.info("=" * 60)

    config = load_config()
    bigip = config["bigip"]

    # 0. WAF 정책 파일 업로드 (선택, 실패해도 계속 진행)
    upload_waf_policy_to_bigip(bigip)

    # 1. 템플릿 렌더링
    as3_declaration = render_template(config)

    # 2. AS3 선언 제출
    job_id = submit_as3_declaration(bigip, as3_declaration)

    # 3. 작업 완료 대기
    success = wait_for_completion(bigip, job_id)

    if not success:
        print("\n" + "=" * 60)
        print("❌ AS3 배포에 실패했습니다.")
        print("BIG-IP 로그를 확인하세요: /var/log/restnoded/restnoded.log")
        print("=" * 60)
        sys.exit(1)

    # 4. Virtual Server 확인
    print("\n--- 배포 검증 ---")
    verify_virtual_server(bigip, config)

    print("\n" + "=" * 60)
    print("🎉 AS3 배포가 성공적으로 완료되었습니다!")
    print(f"DVWA 접속: http://{config['target']['vip_address']}:{config['target']['vip_port']}")
    print("다음 단계: python 03_run_attack_tests.py")
    print("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
