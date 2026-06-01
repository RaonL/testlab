# F5 AWAF Test Lab Factory 🏭

> **F5 AWAF(Advanced WAF) 테스트 환경을 자동으로 구축하고, 보안 공격을 시뮬레이션하며, 결과를 리포트로 제공하는 종합 테스트 자동화 도구**

---

## 📋 개요

F5 AWAF Test Lab Factory는 F5 BIG-IP AWAF(Advanced Web Application Firewall)의 WAF 정책을 실제 환경에서 신속하게 테스트하고 검증하기 위한 자동화 프로젝트입니다.

실제 회사에서 사내 테스트를 자주 진행해야 하는 F5 엔지니어를 위해 설계되었으며, 다음과 같은 복잡한 작업을 **단일 파이프라인**으로 자동화합니다:

1. ✅ **BIG-IP Ready Check** - 장비 상태 및 패키지 설치 확인
2. ✅ **Declarative Onboarding (DO)** - AWAF 프로비저닝 및 네트워크 설정 자동화
3. ✅ **AS3 Deploy** - DVWA 애플리케이션 + WAF 보안 정책 배포
4. ✅ **Attack Tests** - SQLi, XSS, LFI/RFI, Command Injection, SSRF 등 325개 실제 공격 시뮬레이션
5. ✅ **Log Collection** - BIG-IP 보안 로그 자동 수집
6. ✅ **Report Generation** - 차트와 표가 포함된 HTML 리포트 생성

---

## 🚀 시작하기

### 사전 요구사항

| 요구사항 | 버전 | 설명 |
|---------|------|------|
| Python | 3.8+ | 스크립트 실행 환경 |
| BIG-IP | 15.0+ | AWAF 라이선스 필요 |
| DO 패키지 | 1.40.0+ | Declarative Onboarding 설치 |
| AS3 패키지 | 3.50.0+ | Application Services 3 설치 |
| Docker | 20.0+ | (선택) 로컬 DVWA 실행용 |

### 설치

```bash
# 1. 프로젝트 클론
git clone <repository-url>
cd f5-awaf-testlab-factory

# 2. Python 패키지 설치
pip install -r requirements.txt

# 3. lab.yml 설정 (환경에 맞게 수정)
#    - bigip.host: BIG-IP 관리 IP
#    - bigip.password: BIG-IP 관리 비밀번호
#    - target.vip_address: Virtual Server IP
vim lab.yml

# 4. (선택) 로컬 DVWA 실행
docker-compose up -d
```

---

## 📖 사용 방법

### 전체 파이프라인 실행

```bash
# Step 00: BIG-IP 연결 및 상태 확인
python scripts/00_check_bigip_ready.py

# Step 01: Declarative Onboarding 실행
python scripts/01_onboard_do.py

# Step 02: AS3 DVWA + WAF 정책 배포
python scripts/02_deploy_as3.py

# Step 03: 공격 테스트 실행
python scripts/03_run_attack_tests.py

# 특정 테스트만 실행
python scripts/03_run_attack_tests.py --test sqli
python scripts/03_run_attack_tests.py --test xss

# 실제 전송 없이 시뮬레이션 (Dry Run)
python scripts/03_run_attack_tests.py --dry-run

# Step 04: 로그 수집
python scripts/04_collect_logs.py

# Step 05: HTML 리포트 생성
python scripts/05_generate_report.py
```

### 빠른 실행 (All-in-One)

```bash
# 모든 단계를 순차적으로 실행
for script in scripts/[0-9]*.py; do
    echo "=== Running $script ==="
    python "$script" || { echo "❌ $script failed"; exit 1; }
done
```

---

## 📂 프로젝트 구조

```
f5-awaf-testlab-factory/
├── README.md                    # 프로젝트 설명서
├── lab.yml                      # 랩 환경 설정 (BIG-IP, DVWA, 테스트 설정)
├── requirements.txt             # Python 의존성 패키지
├── docker-compose.yml           # DVWA 컨테이너 실행
│
├── scripts/                     # 실행 스크립트
│   ├── 00_check_bigip_ready.py  # BIG-IP 연결 및 상태 확인
│   ├── 01_onboard_do.py         # Declarative Onboarding (AWAF 프로비저닝)
│   ├── 02_deploy_as3.py         # AS3 DVWA + WAF 정책 배포
│   ├── 03_run_attack_tests.py   # 보안 공격 시뮬레이션 실행
│   ├── 04_collect_logs.py       # BIG-IP 보안 로그 수집
│   └── 05_generate_report.py    # HTML 리포트 생성
│
├── declarations/                # F5 선언 템플릿
│   ├── do_awaf_lab.json.j2      # DO 템플릿 (Jinja2)
│   ├── as3_dvwa_awaf.json.j2    # AS3 템플릿 (Jinja2)
│   └── waf_policy_template.json # WAF 보안 정책
│
├── tests/                       # 공격 테스트 정의 (YAML, 총 325 케이스)
│   ├── sqli.yml                 # SQL Injection 테스트 (45 케이스)
│   ├── xss.yml                  # XSS 테스트 (45 케이스)
│   ├── file_inclusion.yml       # 파일 포함 취약점 테스트 (40 케이스)
│   ├── brute_force.yml          # 무차별 대입 테스트 (40 케이스)
│   ├── path_traversal.yml       # 경로 탐색 테스트 (40 케이스)
│   ├── command_injection.yml    # OS 명령어 삽입 테스트 (30 케이스)
│   ├── ssrf.yml                 # Server-Side Request Forgery (25 케이스)
│   ├── xxe.yml                  # XML External Entity (20 케이스)
│   ├── insecure_deserialization.yml # 안전하지 않은 역직렬화 (15 케이스)
│   ├── nosql_injection.yml      # NoSQL Injection (15 케이스)
│   ├── ssti.yml                 # SSTI (15 케이스)
│   ├── jwt_attacks.yml          # JWT 변조 공격 (10 케이스)
│   └── http_protocol_abuse.yml  # HTTP 프로토콜 변조 (10 케이스)
│
├── reports/                     # 생성된 리포트
│   └── result.html              # HTML 테스트 리포트
│
└── output/                      # 스크립트 출력물
    ├── do_rendered.json         # 렌더링된 DO 선언
    ├── as3_rendered.json        # 렌더링된 AS3 선언
    ├── test_result.json         # 테스트 실행 결과
    └── logs/                    # 수집된 로그 파일
        ├── security_latest.json
        └── ...
```

---

## 🛡️ 테스트 구성

### 공격 테스트 유형

| 테스트 | 파일 | 케이스 | 심각도 | 설명 |
|--------|------|:------:|--------|------|
| 🗃️ SQL Injection | `tests/sqli.yml` | **45** | 🔴 Critical | UNION, Blind, Error-based, PostgreSQL/MSSQL, Second-Order, OOB, WAF 우회 |
| 💉 XSS | `tests/xss.yml` | **45** | 🔴 Critical | Reflected, Stored, DOM, mXSS, Polyglot, CSP Bypass, DOM Clobbering |
| 📂 File Inclusion | `tests/file_inclusion.yml` | **40** | 🟠 High | LFI, RFI, PHP Wrapper, Log Poisoning, Session Inclusion |
| 🔑 Brute Force | `tests/brute_force.yml` | **40** | 🟠 High | Credential Stuffing, Password Spraying, MFA Bypass, API BF, Rate Limit 우회 |
| 📁 Path Traversal | `tests/path_traversal.yml` | **40** | 🟠 High | 디렉토리 경로 탐색, K8s/Docker 경로, Cloud 환경, 인코딩 우회 |
| 💻 Command Injection | `tests/command_injection.yml` | **30** | 🔴 Critical | OS 명령어 삽입, Blind Cmd, OOB Cmd, 우회 기법 |
| 🌐 SSRF | `tests/ssrf.yml` | **25** | 🔴 Critical | 내부망 스캔, AWS/GCP/Azure 메타데이터, 프로토콜 우회 |
| 📄 XXE | `tests/xxe.yml` | **20** | 🔴 Critical | In-band/OOB/Blind XXE, XInclude, SVG, SOAP |
| 🧊 Insecure Deserialization | `tests/insecure_deserialization.yml` | **15** | 🔴 Critical | PHP/Java/Python 역직렬화, Log4Shell, Proto Pollution |
| 🍃 NoSQL Injection | `tests/nosql_injection.yml` | **15** | 🔴 Critical | MongoDB $ne/$gt/$regex, Blind, Content-Type 우회 |
| 📝 SSTI | `tests/ssti.yml` | **15** | 🔴 Critical | Jinja2, Twig, Freemarker, Velocity, ERB RCE |
| 🔐 JWT Attacks | `tests/jwt_attacks.yml` | **10** | 🟠 High | None Alg, Algorithm Confusion, JKU/JWK/Kid Injection |
| 🔧 HTTP Protocol Abuse | `tests/http_protocol_abuse.yml` | **10** | 🟠 High | Method Tampering, Content-Type 변조, HPP, Smuggling |

**총 325개의 테스트 케이스**가 13개 파일에 포함되어 있습니다.

> 💡 신규 테스트 파일은 DVWA에 실제 취약점이 없는 경우에도(WAF 우회 기법 등) **WAF 시그니처 탐지 여부를 검증**하는 용도로 동작합니다.

### WAF 정책 구성

선언된 WAF 정책(`declarations/waf_policy_template.json`)은 **Transparent(감사) 모드**로 설정되어 있어, 실제 차단 없이 탐지 여부를 확인할 수 있습니다. 주요 탐지 항목:

- **VIOLATION_SQL_INJECTION** - SQL 인젝션 공격
- **VIOLATION_XSS** - 크로스 사이트 스크립팅
- **VIOLATION_HTTP_METHOD** - 허용되지 않은 HTTP 메소드
- **VIOLATION_FILE_TYPE** - 비허용 파일 유형
- **VIOLATION_PARAMETER_VALUE** - 비정상 파라미터 값
- **VIOLATION_URL** - 비정상 URL 패턴
- **Signature Sets** - SQLi, XSS, Command Execution, Path Traversal 시그니처

> **운영 환경에 배포할 때는 `blocking-settings`의 `"block": true`로 변경하여 실제 차단이 가능합니다.**

---

## 📊 리포트 샘플

`reports/result.html` 파일은 다음과 같은 정보를 포함한 HTML 리포트를 제공합니다:

- 📈 **요약 카드** - 총 테스트 수, WAF 탐지 수, 탐지율
- 📊 **차트** - 카테고리별 WAF 탐지 현황, 탐지된 공격 유형 분포
- 📋 **상세 테스트 결과 테이블** - 각 테스트 케이스별 결과
- 🛡️ **WAF 탐지 로그** - BIG-IP에서 수집된 보안 로그

---

## ⚙️ 설정 가이드

### lab.yml 주요 설정 항목

```yaml
# BIG-IP 연결 정보
bigip:
  host: "192.168.1.245"          # 귀하의 BIG-IP IP로 변경
  username: "admin"               # 관리자 계정
  password: "admin"               # 관리자 비밀번호

# DVWA 접속 정보
target:
  vip_address: "192.168.1.100"    # Virtual Server IP
  dvwa:
    url: "http://192.168.1.100"   # DVWA 접속 URL (VIP 경유)
    security_level: "low"          # low=가장 취약 (테스트 용이)
```

### 환경별 커스터마이징

1. **BIG-IP IP/Port 변경** - `lab.yml`의 `bigip.host` 수정
2. **Virtual Server IP 변경** - `lab.yml`의 `target.vip_address` 수정
3. **WAF 모드 변경** - `declarations/waf_policy_template.json`의 `enforcementMode` 수정
   - `transparent` (감사 모드, 기본)
   - `blocking` (차단 모드)
4. **테스트 반복 횟수 변경** - `lab.yml`의 `attack_tests.repeat_count` 수정

---

## 🔍 문제 해결

### 일반적인 문제

| 문제 | 원인 | 해결 방법 |
|------|------|----------|
| `Connection refused` | BIG-IP REST API 미활성화 | `tmsh modify sys httpd allow-remote-ui enable` |
| `DO 패키지 없음` | DO 미설치 | [DO 다운로드](https://github.com/F5Networks/f5-declarative-onboarding) |
| `AS3 패키지 없음` | AS3 미설치 | [AS3 다운로드](https://github.com/F5Networks/f5-appsvcs-extension) |
| `DVWA 로그인 실패` | DVWA 설정 문제 | `docker-compose logs dvwa`로 로그 확인 |
| `SSL 경고` | 인증서 문제 | `lab.yml`의 `validate_certs: false` 설정 |

### 로그 확인

```bash
# BIG-IP REST API 로그
tail -f /var/log/restnoded/restnoded.log

# ASM 로그
tail -f /var/log/asm.log

# 테스트 실행 로그
python scripts/03_run_attack_tests.py 2>&1 | tee test_run.log
```

---

## 📌 주의사항

⚠️ **이 도구는 공인된 테스트 환경에서만 사용하세요.**
- 실제 운영 중인 서비스에 사용하지 마십시오.
- 테스트 대상에 대한 사전 승인을 받은 후 사용하십시오.
- WAF 정책은 `transparent` 모드(감사 모드)로 설정되어 있습니다.
- DVWA는 의도적으로 취약하게 설계된 애플리케이션으로, 외부 네트워크에 노출하지 마십시오.

---

## 📚 참고 자료

- [F5 Declarative Onboarding 문서](https://clouddocs.f5.com/products/extensions/f5-declarative-onboarding/latest/)
- [F5 Application Services 3 문서](https://clouddocs.f5.com/products/extensions/f5-appsvcs-extension/latest/)
- [F5 ASM/ASLG REST API 문서](https://clouddocs.f5.com/api/asm-rest-apis/)
- [DVWA (Damn Vulnerable Web Application)](https://github.com/digininja/DVWA)

---

## 📝 라이선스

이 프로젝트는 내부 F5 테스트 자동화를 목적으로 제작되었습니다.

---

*Made with ❤️ by an F5 Engineer*
