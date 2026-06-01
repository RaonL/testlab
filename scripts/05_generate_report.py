#!/usr/bin/env python3
"""
================================================================================
[05] Generate Report - F5 AWAF Test Lab Factory
================================================================================
테스트 결과와 로그를 기반으로 HTML 리포트를 생성합니다.
  - output/test_result.json 로드
  - output/logs/security_latest.json 로드
  - 차트와 표가 포함된 HTML 리포트 생성
  - reports/ 디렉토리에 결과 저장

사용법:
    python 05_generate_report.py

사전 조건:
    - 03_run_attack_tests.py 완료 (output/test_result.json)
    - 04_collect_logs.py 완료 (선택, output/logs/ 디렉토리)
================================================================================
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml

# --- 로깅 설정 ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("generate_report")


def load_config() -> dict:
    """lab.yml 설정 파일을 로드합니다."""
    config_path = Path(__file__).resolve().parent.parent / "lab.yml"
    if not config_path.exists():
        logger.error(f"설정 파일을 찾을 수 없습니다: {config_path}")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_test_results() -> Optional[dict]:
    """output/test_result.json 파일을 로드합니다."""
    result_path = Path(__file__).resolve().parent.parent / "output" / "test_result.json"
    if not result_path.exists():
        logger.warning("⚠️ 테스트 결과 파일을 찾을 수 없습니다.")
        return None
    with open(result_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_latest_logs(log_type: str = "security") -> Optional[dict]:
    """output/logs/ 디렉토리에서 최신 로그를 로드합니다."""
    logs_dir = Path(__file__).resolve().parent.parent / "output" / "logs"
    if not logs_dir.exists():
        return None

    # latest 파일 또는 가장 최근 파일 찾기
    latest_path = logs_dir / f"{log_type}_latest.json"
    if latest_path.exists():
        with open(latest_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # 최신 파일 찾기
    log_files = sorted(logs_dir.glob(f"{log_type}_*.json"), reverse=True)
    if log_files:
        with open(log_files[0], "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def generate_report_html(
    test_results: Optional[dict],
    security_logs: Optional[dict],
    config: dict
) -> str:
    """HTML 리포트를 생성합니다."""
    report_config = config.get("report", {})
    title = report_config.get("title", "F5 AWAF Security Test Report")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 통계 계산
    stats = {}
    if test_results:
        stats = test_results.get("stats", {})
        results_list = test_results.get("results", [])
    else:
        results_list = []

    # 카테고리별 통계
    categories = {}
    for result in results_list:
        cat = result.get("category", "unknown")
        if cat not in categories:
            categories[cat] = {"total": 0, "waf_detected": 0, "passed": 0}
        categories[cat]["total"] += 1
        if result.get("waf_detected"):
            categories[cat]["waf_detected"] += 1
        if any(r.get("status_code", 0) > 0 for r in result.get("responses", [])):
            categories[cat]["passed"] += 1

    # 탐지된 공격 유형
    attack_types = {}
    if security_logs:
        for entry in security_logs.get("entries", []):
            sig_name = entry.get("signatureName", "Unknown")
            attack_types[sig_name] = attack_types.get(sig_name, 0) + 1

    global_waf_rate = 0
    if stats.get("total", 0) > 0:
        global_waf_rate = (stats.get("waf_triggered", 0) / stats["total"]) * 100

    # HTML 템플릿
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f0f2f5; color: #333; line-height: 1.6; }}
  .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}

  /* Header */
  .header {{ background: linear-gradient(135deg, #1a237e, #0d47a1); color: white; padding: 30px; border-radius: 12px; margin-bottom: 24px; }}
  .header h1 {{ font-size: 28px; margin-bottom: 8px; }}
  .header .meta {{ opacity: 0.85; font-size: 14px; }}

  /* Cards */
  .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }}
  .card {{ background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); transition: transform 0.2s; }}
  .card:hover {{ transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,0.12); }}
  .card .label {{ font-size: 13px; color: #666; margin-bottom: 8px; }}
  .card .value {{ font-size: 32px; font-weight: 700; }}

  /* Charts */
  .chart-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }}
  .chart-box {{ background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
  .chart-box h3 {{ margin-bottom: 16px; font-size: 16px; color: #444; }}

  /* Table */
  .table-wrap {{ background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); overflow-x: auto; margin-bottom: 24px; }}
  .table-wrap h3 {{ margin-bottom: 16px; font-size: 16px; color: #444; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #eee; font-size: 14px; }}
  th {{ background: #f8f9fa; font-weight: 600; color: #555; }}
  tr:hover {{ background: #f8f9fa; }}
  .badge {{ display: inline-block; padding: 3px 8px; border-radius: 12px; font-size: 12px; font-weight: 600; }}
  .badge-success {{ background: #e8f5e9; color: #2e7d32; }}
  .badge-danger {{ background: #ffebee; color: #c62828; }}
  .badge-warning {{ background: #fff3e0; color: #e65100; }}

  /* Logs */
  .log-section {{ background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 24px; }}
  .log-section h3 {{ margin-bottom: 16px; font-size: 16px; color: #444; }}
  .log-entry {{ padding: 8px 12px; margin-bottom: 6px; border-radius: 6px; font-size: 13px; background: #f8f9fa; }}
  .log-entry .sig-name {{ font-weight: 600; color: #c62828; }}

  /* Footer */
  .footer {{ text-align: center; padding: 20px; color: #888; font-size: 13px; }}

  @media (max-width: 768px) {{
    .chart-row {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>
<div class="container">
  <!-- Header -->
  <div class="header">
    <h1>{title}</h1>
    <div class="meta">
      생성일: {now} &nbsp;|&nbsp;
      대상: {config['target']['vip_address']}:{config['target']['vip_port']} &nbsp;|&nbsp;
      BIG-IP: {config['bigip']['host']}
    </div>
  </div>

  <!-- Summary Cards -->
  <div class="cards">
    <div class="card">
      <div class="label">총 테스트</div>
      <div class="value">{stats.get('total', 0)}</div>
    </div>
    <div class="card">
      <div class="label">🛡️ WAF 탐지</div>
      <div class="value" style="color: #2e7d32;">{stats.get('waf_triggered', 0)}</div>
    </div>
    <div class="card">
      <div class="label">탐지율</div>
      <div class="value" style="color: {'#2e7d32' if global_waf_rate >= 70 else '#e65100'};">{global_waf_rate:.1f}%</div>
    </div>
    <div class="card">
      <div class="label">전송 실패</div>
      <div class="value" style="color: {'#c62828' if stats.get('failed', 0) > 0 else '#666'};">{stats.get('failed', 0)}</div>
    </div>
  </div>

  <!-- Charts -->
  <div class="chart-row">
    <div class="chart-box">
      <h3>카테고리별 WAF 탐지</h3>
      <canvas id="categoryChart"></canvas>
    </div>
    <div class="chart-box">
      <h3>탐지된 공격 유형</h3>
      <canvas id="attackChart"></canvas>
    </div>
  </div>

"""

    # Chart JavaScript
    cat_labels = json.dumps(list(categories.keys()))
    cat_total = json.dumps([c["total"] for c in categories.values()])
    cat_detected = json.dumps([c["waf_detected"] for c in categories.values()])

    atk_labels = json.dumps(list(attack_types.keys()))
    atk_values = json.dumps(list(attack_types.values()))

    html += f"""
  <script>
  const catCtx = document.getElementById('categoryChart').getContext('2d');
  new Chart(catCtx, {{
    type: 'bar',
    data: {{
      labels: {cat_labels},
      datasets: [
        {{ label: '전체', data: {cat_total}, backgroundColor: '#bbdefb' }},
        {{ label: 'WAF 탐지', data: {cat_detected}, backgroundColor: '#4caf50' }}
      ]
    }},
    options: {{
      responsive: true,
      plugins: {{ legend: {{ position: 'top' }} }},
      scales: {{ y: {{ beginAtZero: true, ticks: {{ stepSize: 1 }} }} }}
    }}
  }});
"""

    if attack_types:
        html += f"""
  const atkCtx = document.getElementById('attackChart').getContext('2d');
  new Chart(atkCtx, {{
    type: 'doughnut',
    data: {{
      labels: {atk_labels},
      datasets: [{{ data: {atk_values}, backgroundColor: ['#e53935','#fb8c00','#43a047','#1e88e5','#8e24aa','#00acc1','#ffb300','#6d4c41'] }}]
    }},
    options: {{
      responsive: true,
      plugins: {{ legend: {{ position: 'right' }} }}
    }}
  }});
"""
    else:
        html += """
  document.getElementById('attackChart').parentElement.innerHTML = '<h3>탐지된 공격 유형</h3><p style="color:#888;text-align:center;padding:40px;">로그 데이터가 없습니다.</p>';
"""

    html += "</script>"

    # Detailed Results Table
    html += """
  <div class="table-wrap">
    <h3>📋 상세 테스트 결과</h3>
    <table>
      <thead>
        <tr>
          <th>카테고리</th>
          <th>테스트</th>
          <th>Method</th>
          <th>경로</th>
          <th>심각도</th>
          <th>상태</th>
          <th>WAF</th>
        </tr>
      </thead>
      <tbody>
"""

    for result in results_list:
        cat = result.get("category", "")
        desc = result.get("description", "")
        method = result.get("method", "GET")
        url_path = result.get("url", "")
        severity = result.get("severity", "medium")
        waf = result.get("waf_detected", False)

        # Extract path from URL
        path = "/" + "/".join(url_path.split("/")[3:]) if "://" in url_path else url_path

        # Response status (가장 최근 응답 기준)
        responses = result.get("responses", [])
        if responses:
            last_resp = responses[-1]
            status_code = last_resp.get("status_code", 0)
            status_badge = "success" if status_code < 400 else "danger" if status_code >= 500 else "warning"
            status_text = str(status_code) if status_code > 0 else "ERROR"
        else:
            status_badge = "warning"
            status_text = "N/A"

        waf_badge = "success" if waf else "danger"
        waf_text = "✅ 탐지" if waf else "❌ 미탐지"

        severity_color = "danger" if severity == "high" else "warning" if severity == "medium" else "success"

        html += f"""
        <tr>
          <td><span class="badge badge-{severity_color}">{cat}</span></td>
          <td>{desc}</td>
          <td><code>{method}</code></td>
          <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{path}</td>
          <td>{severity}</td>
          <td><span class="badge badge-{status_badge}">{status_text}</span></td>
          <td><span class="badge badge-{waf_badge}">{waf_text}</span></td>
        </tr>"""

    html += """
      </tbody>
    </table>
  </div>
"""

    # Security Logs
    if security_logs and security_logs.get("entries"):
        html += """
  <div class="log-section">
    <h3>🛡️ WAF 탐지 로그 (상위 50개)</h3>
"""
        for entry in security_logs.get("entries", [])[:50]:
            sig_name = entry.get("signatureName", "Unknown")
            src_ip = entry.get("sourceIp", "N/A")
            time_str = entry.get("generationTime", "")
            method = entry.get("method", "N/A")
            uri = entry.get("uri", "N/A")

            html += f"""
    <div class="log-entry">
      <span class="sig-name">🔴 {sig_name}</span> &nbsp;
      <span style="color:#666;">{method} {uri}</span> &nbsp;
      <span style="color:#999;font-size:12px;">from {src_ip}</span>
    </div>"""

        html += "\n  </div>\n"

    # Footer
    html += f"""
  <div class="footer">
    Generated by F5 AWAF Test Lab Factory &bull; {now}
  </div>
</div>
</body>
</html>
"""

    return html


def save_report(html_content: str, config: dict):
    """HTML 리포트를 파일로 저장합니다."""
    report_path = config.get("report", {}).get("output_file", "reports/result.html")
    output_path = Path(__file__).resolve().parent.parent / report_path

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    logger.info(f"✅ HTML 리포트 저장 완료: {output_path.resolve()}")
    return output_path.resolve()


def main():
    """메인 함수: 리포트를 생성합니다."""
    logger.info("=" * 60)
    logger.info("[05] Generate Report 시작")
    logger.info("=" * 60)

    config = load_config()

    # 1. 테스트 결과 로드
    logger.info("테스트 결과 로드 중...")
    test_results = load_test_results()
    if test_results:
        total = test_results.get("stats", {}).get("total", 0)
        logger.info(f"  ✅ {total}개 테스트 결과 로드 완료")
    else:
        logger.warning("  ⚠️ 테스트 결과 없음 (빈 리포트 생성)")

    # 2. 보안 로그 로드
    logger.info("보안 로그 로드 중...")
    security_logs = load_latest_logs("security")
    if security_logs:
        count = len(security_logs.get("entries", []))
        logger.info(f"  ✅ {count}개 보안 로그 로드 완료")
    else:
        logger.warning("  ⚠️ 보안 로그 없음 (로그 미수집)")

    # 3. HTML 리포트 생성
    logger.info("HTML 리포트 생성 중...")
    html = generate_report_html(test_results, security_logs, config)

    # 4. 저장
    output_path = save_report(html, config)

    print("\n" + "=" * 60)
    print(f"🎉 리포트 생성 완료!")
    print(f"📄 파일: {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
