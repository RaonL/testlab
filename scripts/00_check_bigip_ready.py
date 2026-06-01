#!/usr/bin/env python3
"""
================================================================================
[00] BIG-IP Ready Check - F5 AWAF Test Lab Factory
================================================================================
BIG-IP 장비가 DO/AS3를 실행할 준비가 되었는지 확인합니다.
  - REST API 응답 여부
  - DO/AS3 iApp 패키지 설치 여부
  - AWAF 프로비저닝 상태 확인
  - 라이선스 상태 확인

사용법:
    python 00_check_bigip_ready.py

종료 코드:
    0: 성공 (모든 조건 충족)
    1: 실패 (일부 조건 불충족)
================================================================================
"""

import sys
import json
import time
import logging
from pathlib import Path

# 상위 디렉토리를 모듈 경로에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml
import requests
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning

# SSL 경고 억제 (lab.yml에 validate_certs: false 설정 시)
disable_warnings(InsecureRequestWarning)

# --- 로깅 설정 ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("check_bigip")


def load_config() -> dict:
    """lab.yml 설정 파일을 로드합니다."""
    config_path = Path(__file__).resolve().parent.parent / "lab.yml"
    if not config_path.exists():
        logger.error(f"설정 파일을 찾을 수 없습니다: {config_path}")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def check_rest_api(bigip: dict) -> bool:
    """BIG-IP REST API 응답을 확인합니다."""
    host = bigip["host"]
    port = bigip.get("port", 443)
    username = bigip["username"]
    password = bigip["password"]
    verify = bigip.get("validate_certs", False)

    url = f"https://{host}:{port}/mgmt/tm/sys"
    logger.info(f"REST API 연결 확인: {url}")

    try:
        resp = requests.get(
            url,
            auth=(username, password),
            verify=verify,
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            version = data.get("version", "unknown")
            logger.info(f"✅ BIG-IP 연결 성공 (버전: {version})")
            return True
        else:
            logger.error(f"❌ REST API 응답 오류: HTTP {resp.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        logger.error(f"❌ BIG-IP 연결 실패: {host}:{port} (연결 거부됨)")
        return False
    except requests.exceptions.Timeout:
        logger.error(f"❌ BIG-IP 연결 시간 초과: {host}:{port}")
        return False
    except Exception as e:
        logger.error(f"❌ BIG-IP 연결 오류: {e}")
        return False


def check_do_installed(bigip: dict) -> bool:
    """DO (Declarative Onboarding) iApp 패키지 설치 여부를 확인합니다."""
    host = bigip["host"]
    port = bigip.get("port", 443)
    username = bigip["username"]
    password = bigip["password"]
    verify = bigip.get("validate_certs", False)

    url = f"https://{host}:{port}/mgmt/shared/declarative-onboarding/info"
    logger.info("DO 패키지 확인 중...")

    try:
        resp = requests.get(
            url,
            auth=(username, password),
            verify=verify,
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            version = data.get("version", "unknown")
            logger.info(f"✅ DO 설치됨 (버전: {version})")
            return True
        else:
            logger.warning(f"❌ DO 미설치 또는 응답 없음 (HTTP {resp.status_code})")
            return False
    except Exception:
        logger.warning("❌ DO 패키지가 설치되지 않았습니다.")
        return False


def check_as3_installed(bigip: dict) -> bool:
    """AS3 iApp 패키지 설치 여부를 확인합니다."""
    host = bigip["host"]
    port = bigip.get("port", 443)
    username = bigip["username"]
    password = bigip["password"]
    verify = bigip.get("validate_certs", False)

    url = f"https://{host}:{port}/mgmt/shared/appsvcs/info"
    logger.info("AS3 패키지 확인 중...")

    try:
        resp = requests.get(
            url,
            auth=(username, password),
            verify=verify,
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            version = data.get("version", "unknown")
            logger.info(f"✅ AS3 설치됨 (버전: {version})")
            return True
        else:
            logger.warning(f"❌ AS3 미설치 또는 응답 없음 (HTTP {resp.status_code})")
            return False
    except Exception:
        logger.warning("❌ AS3 패키지가 설치되지 않았습니다.")
        return False


def check_provisioning(bigip: dict) -> bool:
    """AWAF/LTM 프로비저닝 상태를 확인합니다."""
    host = bigip["host"]
    port = bigip.get("port", 443)
    username = bigip["username"]
    password = bigip["password"]
    verify = bigip.get("validate_certs", False)

    url = f"https://{host}:{port}/mgmt/tm/sys/provision"
    logger.info("프로비저닝 상태 확인 중...")

    try:
        resp = requests.get(
            url,
            auth=(username, password),
            verify=verify,
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("items", [])
            all_ok = True
            for item in items:
                name = item.get("name", "unknown")
                level = item.get("level", "none")
                logger.info(f"  - {name}: {level}")
                if level == "none":
                    logger.warning(f"  ⚠️ {name} 프로비저닝이 'none'입니다")
                    all_ok = False
            return all_ok
        else:
            logger.warning(f"❌ 프로비저닝 정보 조회 실패 (HTTP {resp.status_code})")
            return False
    except Exception as e:
        logger.error(f"❌ 프로비저닝 조회 오류: {e}")
        return False


def check_license(bigip: dict) -> bool:
    """BIG-IP 라이선스 상태를 확인합니다."""
    host = bigip["host"]
    port = bigip.get("port", 443)
    username = bigip["username"]
    password = bigip["password"]
    verify = bigip.get("validate_certs", False)

    url = f"https://{host}:{port}/mgmt/tm/sys/license"
    logger.info("라이선스 상태 확인 중...")

    try:
        resp = requests.get(
            url,
            auth=(username, password),
            verify=verify,
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            registration_key = data.get("registrationKey", "N/A")
            logger.info(f"✅ 라이선스 등록됨 (Key: {registration_key})")
            return True
        else:
            logger.warning(f"❌ 라이선스 정보 조회 실패 (HTTP {resp.status_code})")
            return False
    except Exception:
        logger.warning("❌ 라이선스 확인 중 오류 발생")
        return False


def main():
    """메인 함수: 모든 점검을 수행하고 결과를 반환합니다."""
    logger.info("=" * 60)
    logger.info("BIG-IP Ready Check 시작")
    logger.info("=" * 60)

    config = load_config()
    bigip = config["bigip"]

    logger.info(f"\n대상: {bigip['host']}:{bigip.get('port', 443)}")
    logger.info(f"사용자: {bigip['username']}\n")

    # 각 점검 수행
    checks = [
        ("REST API 연결", check_rest_api(bigip)),
        ("DO 패키지 설치", check_do_installed(bigip)),
        ("AS3 패키지 설치", check_as3_installed(bigip)),
        ("프로비저닝 상태", check_provisioning(bigip)),
        ("라이선스 상태", check_license(bigip)),
    ]

    # 결과 출력
    success_count = 0
    total_count = len(checks)

    print("\n" + "=" * 60)
    print("점검 결과 요약")
    print("=" * 60)

    for name, result in checks:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}  {name}")
        if result:
            success_count += 1

    print(f"\n결과: {success_count}/{total_count} 통과")

    if success_count == total_count:
        print("\n🎉 모든 점검을 통과했습니다. 다음 단계를 진행하세요!")
        sys.exit(0)
    else:
        print("\n⚠️  일부 점검에 실패했습니다. 위 내용을 확인하고 조치하세요.")
        sys.exit(1)


if __name__ == "__main__":
    main()
