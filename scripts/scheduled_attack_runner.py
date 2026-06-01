#!/usr/bin/env python3
"""
================================================================================
[SCHEDULED] Attack Runner - F5 AWAF Test Lab Factory
================================================================================
n8n 연동 또는 독립 실행형 스케줄러.
실제 운영 환경(transparent 모드, 장기간)을 시뮬레이션하기 위해 설계되었습니다.

사용법 (n8n Execute Command):
    python scripts/scheduled_attack_runner.py --mode once
        → 랜덤 카테고리 선택 후 1회 실행, JSON 결과 출력

사용법 (독립 실행 - 무한 루프):
    python scripts/scheduled_attack_runner.py --mode daemon
        → 15~45분 간격으로 랜덤 테스트 지속 실행

사용법 (단일 카테고리 지정):
    python scripts/scheduled_attack_runner.py --mode once --category sqli
================================================================================
"""

import sys
import json
import time
import random
import argparse
import subprocess
import logging
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml
import requests
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning

disable_warnings(InsecureRequestWarning)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("scheduled_runner")

# --- 카테고리별 가중치 (높을수록 자주 선택됨) ---
CATEGORIES = [
    {"id": "sqli",               "weight": 5, "name": "SQL Injection"},
    {"id": "xss",                "weight": 5, "name": "XSS"},
    {"id": "command_injection",  "weight": 3, "name": "Command Injection"},
    {"id": "file_inclusion",     "weight": 3, "name": "File Inclusion"},
    {"id": "path_traversal",     "weight": 3, "name": "Path Traversal"},
    {"id": "brute_force",        "weight": 2, "name": "Brute Force"},
    {"id": "ssrf",               "weight": 2, "name": "SSRF"},
    {"id": "xxe",                "weight": 2, "name": "XXE"},
    {"id": "nosql_injection",    "weight": 2, "name": "NoSQL Injection"},
    {"id": "ssti",               "weight": 2, "name": "SSTI"},
    {"id": "insecure_deserialization", "weight": 1, "name": "Insecure Deserialization"},
    {"id": "jwt_attacks",        "weight": 1, "name": "JWT Attacks"},
    {"id": "http_protocol_abuse","weight": 1, "name": "HTTP Protocol Abuse"},
]


def weighted_random_selection(count: int = None) -> list:
    """가중치 기반 랜덤 카테고리 선택"""
    if count is None:
        count = random.randint(1, 3)  # 1~3개

    weights = [c["weight"] for c in CATEGORIES]
    selected = random.choices(CATEGORIES, weights=weights, k=min(count, len(CATEGORIES)))
    # 중복 제거
    seen = set()
    unique = []
    for s in selected:
        if s["id"] not in seen:
            seen.add(s["id"])
            unique.append(s)
    return unique


def run_single_batch(category_ids: list = None, repeat: int = None) -> dict:
    """
    선택된 카테고리에 대해 공격 테스트 실행.
    n8n에서 호출용 - JSON 결과 반환.
    """
    if category_ids is None:
        selected = weighted_random_selection()
        category_ids = [c["id"] for c in selected]

    if repeat is None:
        repeat = random.choice([1, 1, 2])  # 기본 1~2회 (가끔 2회)

    base_dir = Path(__file__).resolve().parent.parent
    script_path = base_dir / "scripts" / "03_run_attack_tests.py"

    results = {
        "timestamp": datetime.now().isoformat(),
        "categories": [],
        "total_tests": 0,
        "total_requests": 0,
        "duration_seconds": 0,
        "success": True,
        "error": None,
    }

    start_time = time.time()

    for cat_id in category_ids:
        try:
            logger.info(f"🚀 실행: {cat_id} (반복: {repeat}회)")

            cmd = [
                sys.executable, str(script_path),
                "--test", cat_id,
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10분 타임아웃
                cwd=str(base_dir)
            )

            cat_result = {
                "category": cat_id,
                "return_code": result.returncode,
                "stdout": result.stdout[-500:] if result.stdout else "",
                "stderr": result.stderr[-500:] if result.stderr else "",
                "success": result.returncode == 0,
            }
            results["categories"].append(cat_result)

            if result.returncode != 0:
                logger.warning(f"  ⚠️ {cat_id} 실패 (코드: {result.returncode})")

        except subprocess.TimeoutExpired:
            logger.warning(f"  ⏱️ {cat_id} 시간 초과")
            results["categories"].append({
                "category": cat_id,
                "return_code": -1,
                "error": "timeout",
                "success": False,
            })
        except Exception as e:
            logger.error(f"  ❌ {cat_id} 오류: {e}")
            results["categories"].append({
                "category": cat_id,
                "return_code": -1,
                "error": str(e),
                "success": False,
            })

    results["duration_seconds"] = round(time.time() - start_time, 1)
    logger.info(f"✅ 배치 완료: {len(category_ids)}개 카테고리, {results['duration_seconds']}초 소요")
    return results


def daemon_mode():
    """무한 루프 - 랜덤 간격으로 지속 실행"""
    logger.info("=" * 60)
    logger.info("[DAEMON] 장기 테스트 스케줄러 시작")
    logger.info("=" * 60)

    cycle_count = 0
    start_date = datetime.now()

    try:
        while True:
            cycle_count += 1
            logger.info(f"\n{'='*60}")
            logger.info(f"📅 Cycle #{cycle_count} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"{'='*60}")

            # 랜덤 카테고리 선택 (1~3개)
            selected = weighted_random_selection()
            cat_ids = [c["id"] for c in selected]
            cat_names = [c["name"] for c in selected]

            logger.info(f"🎯 이번 실행: {', '.join(cat_names)} ({len(cat_ids)}개)")

            # 실행
            batch_result = run_single_batch(cat_ids)

            # 다음 실행까지 랜덤 대기 (15~45분)
            wait_minutes = random.randint(15, 45)
            wait_seconds = wait_minutes * 60
            next_time = datetime.now() + timedelta(seconds=wait_seconds)

            elapsed = datetime.now() - start_date
            logger.info(f"⏰ 다음 실행: {next_time.strftime('%H:%M:%S')} (≈{wait_minutes}분 후)")
            logger.info(f"📊 경과: {elapsed.days}일 {elapsed.seconds//3600}시간 | 총 사이클: {cycle_count}")

            time.sleep(wait_seconds)

    except KeyboardInterrupt:
        elapsed = datetime.now() - start_date
        logger.info(f"\n🛑 스케줄러 중단됨")
        logger.info(f"📊 총 실행: {cycle_count}사이클 | {elapsed.days}일 {elapsed.seconds//3600}시간")


def main():
    parser = argparse.ArgumentParser(description="F5 AWAF Scheduled Attack Runner")
    parser.add_argument("--mode", choices=["once", "daemon"], default="once",
                        help="실행 모드 (once=1회, daemon=무한루프)")
    parser.add_argument("--category", "-c", action="append",
                        help="특정 카테고리 지정 (여러 번 사용 가능). 미지정시 랜덤")
    parser.add_argument("--repeat", "-r", type=int, default=None,
                        help="반복 횟수 (기본: 랜덤 1~2)")
    parser.add_argument("--output", "-o",
                        help="JSON 결과 저장 경로 (선택)")

    args = parser.parse_args()

    if args.mode == "daemon":
        daemon_mode()
        return

    # once mode
    category_ids = args.category
    result = run_single_batch(category_ids, args.repeat)

    # JSON 출력 (n8n이 파싱 가능)
    output = {
        "status": "success" if result["success"] else "partial_failure",
        "timestamp": result["timestamp"],
        "categories_run": [c["category"] for c in result["categories"]],
        "duration_seconds": result["duration_seconds"],
        "details": result,
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ 결과 저장: {output_path}")


if __name__ == "__main__":
    main()
