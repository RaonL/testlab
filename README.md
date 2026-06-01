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

## 📖 사용 방법 - 상세 단계별 가이드

> ⚠️ **시작 전 필수 확인사항**
> 1. Python 3.8+ 설치 확인: `python --version`
> 2. Python 패키지 설치: `pip install -r requirements.txt`
> 3. `lab.yml` 파일에 본인의 IP가 정확히 입력되었는지 확인
> 4. BIG-IP에 DO 패키지와 AS3 패키지가 설치되어 있어야 함
> 5. DVWA 서버(192.168.137.113:80)가 정상 동작 중이어야 함

---

### Step 00: BIG-IP 연결 및 상태 확인 ⏱ 10초

**목적**: BIG-IP 장비가 정상적으로 통신 가능한지, DO/AS3 패키지가 설치되어 있는지, AWAF 라이선스가 활성화되어 있는지 확인합니다.

```bash
python scripts/00_check_bigip_ready.py
```

**정상 출력 예시**:
```
10:00:00 [INFO] ============================================================
10:00:00 [INFO] BIG-IP Ready Check 시작
10:00:00 [INFO] ============================================================
10:00:00 [INFO] 대상: 192.168.137.125:443
10:00:00 [INFO] 사용자: admin

10:00:02 [INFO] ✅ BIG-IP 연결 성공 (버전: 17.1.0)
10:00:03 [INFO] ✅ DO 설치됨 (버전: 1.48.0)
10:00:04 [INFO] ✅ AS3 설치됨 (버전: 3.54.0)
10:00:05 [INFO]   - awaf: nominal
10:00:05 [INFO]   - ltm: nominal
10:00:06 [INFO] ✅ 라이선스 등록됨

============================================================
점검 결과 요약
============================================================
  ✅ PASS  REST API 연결
  ✅ PASS  DO 패키지 설치
  ✅ PASS  AS3 패키지 설치
  ✅ PASS  프로비저닝 상태
  ✅ PASS  라이선스 상태

결과: 5/5 통과
🎉 모든 점검을 통과했습니다. 다음 단계를 진행하세요!
```

**❌ 실패 시 대처법**:
| 증상 | 원인 | 해결 |
|------|------|------|
| `연결 실패` | BIG-IP IP가 다름 | `lab.yml`의 `bigip.host` 확인 |
| `DO 미설치` | DO 패키지 없음 | BIG-IP에 DO iApp 설치 |
| `AS3 미설치` | AS3 패키지 없음 | BIG-IP에 AS3 iApp 설치 |
| `프로비저닝 none` | AWAF/LTM 미프로비저닝 | BIG-IP > System > Resource Provisioning |

---

### Step 01: Declarative Onboarding (DO) 실행 ⏱ 1~3분

**목적**: BIG-IP의 초기 네트워크 설정(DNS, NTP, VLAN, Self IP, Route)과 AWAF/LTM 프로비저닝을 자동으로 구성합니다.

```bash
python scripts/01_onboard_do.py
```

**정상 출력 예시**:
```
10:01:00 [INFO] ============================================================
10:01:00 [INFO] [01] Declarative Onboarding 시작
10:01:00 [INFO] ============================================================
10:01:00 [INFO] DO 템플릿 렌더링 중: do_awaf_lab.json.j2
10:01:00 [INFO] ✅ DO 선언 렌더링 완료: output/do_rendered.json
10:01:01 [INFO] DO 선언 제출 중...
10:01:01 [INFO] ✅ DO 선언 제출 성공 (작업 ID: 9d8c7b6a-5e4f-3d2c-1b0a)
10:01:01 [INFO] DO 작업 완료 대기 중 (최대 600초)...
10:01:12 [INFO]   진행 중... 상태: RUNNING (시도 1/60)
10:01:27 [INFO] ✅ DO 작업 완료! (시도 2회)

============================================================
🎉 DO 온보딩이 성공적으로 완료되었습니다!
다음 단계: python 02_deploy_as3.py
============================================================
```

**⚠️ 주의**: DO는 BIG-IP를 초기화하는 작업입니다. 이미 설정이 완료된 장비라면 SKIP해도 됩니다.
필요시 `lab.yml`에서 `provision_awaf: false`, `provision_ltm: false`로 설정하면 네트워크 설정 없이 프로비저닝만 적용됩니다.

---

### Step 02: AS3 DVWA + WAF 정책 배포 ⏱ 1~3분

**목적**: DVWA 애플리케이션을 위해 BIG-IP에 Virtual Server(VIP)와 Pool, WAF 정책을 생성합니다.

> **이 단계에서 생성되는 리소스**:
> - Virtual Server: `192.168.137.211:80` (DVWA VIP)
> - Pool: `dvwaPool` → 백엔드 `192.168.137.113:80`
> - WAF 정책: `awaf-lab-policy` (Transparent 모드, SQLi/XSS 등 탐지)
> - Log Profile: Security 로그를 JSON 형식으로 저장

**ℹ️ WAF 정책 파일 자동 업로드**:  
스크립트가 `declarations/waf_policy_template.json` 파일을 BIG-IP의 `https://192.168.137.125/mgmt/shared/file-transfer/uploads/` API를 통해 자동 업로드합니다.  
(자동 업로드가 실패해도 AS3 배포는 계속 진행되며, 아래 수동 방법으로 파일을 업로드하고 재시도할 수 있습니다.)

```bash
python scripts/02_deploy_as3.py
```

**정상 출력 예시**:
```
10:05:00 [INFO] ============================================================
10:05:00 [INFO] [02] AS3 Deploy 시작
10:05:00 [INFO] ============================================================
10:05:00 [INFO] AS3 템플릿 렌더링 중: as3_dvwa_awaf.json.j2
10:05:00 [INFO] ✅ AS3 선언 렌더링 완료: output/as3_rendered.json
10:05:01 [INFO] AS3 선언 제출 중...
10:05:01 [INFO] ✅ AS3 선언 제출 성공 (작업 ID: a1b2c3d4)
10:05:01 [INFO] AS3 작업 완료 대기 중 (최대 300초)...
10:05:15 [INFO] ✅ AS3 배포 완료! 테넌트: AWAF_Lab

--- 배포 검증 ---
10:05:15 [INFO] Virtual Server 확인 중: 192.168.137.211:80
10:05:16 [INFO]   ✅ Virtual Server 상태: available
10:05:16 [INFO]   ✅ Destination: 192.168.137.211:80

============================================================
🎉 AS3 배포가 성공적으로 완료되었습니다!
DVWA 접속: http://192.168.137.211:80
다음 단계: python 03_run_attack_tests.py
============================================================
```

**✅ 배포 확인**: 브라우저에서 `http://192.168.137.211` 접속 → DVWA 로그인 페이지가 보이면 성공!

---

### Step 03: 공격 테스트 실행 ⏱ 10~30분 (325개 케이스)

**목적**: DVWA를 대상으로 325개의 실제 보안 공격을 전송하여 WAF 탐지 성능을 측정합니다.

```bash
# 모든 테스트 실행 (325개 전체)
python scripts/03_run_attack_tests.py
```

**정상 실행 중 출력 예시**:
```
10:10:00 [INFO] ============================================================
10:10:00 [INFO] [03] Run Attack Tests 시작
10:10:00 [INFO] ============================================================

--- 테스트 정의 로드 ---
10:10:00 [INFO]   📄 sqli.yml: SQL Injection (45개 케이스)
10:10:00 [INFO]   📄 xss.yml: XSS (45개 케이스)
10:10:00 [INFO]   📄 file_inclusion.yml: File Inclusion (40개 케이스)
10:10:00 [INFO]   📄 brute_force.yml: Brute Force (40개 케이스)
10:10:00 [INFO]   📄 path_traversal.yml: Path Traversal (40개 케이스)
10:10:00 [INFO]   📄 command_injection.yml: Command Injection (30개 케이스)
... (13개 파일 로드)

--- DVWA 로그인 ---
10:10:02 [INFO] DVWA 로그인 성공
10:10:02 [INFO] 보안 레벨 'low' 설정 완료

--- [sqli] 45개 테스트 케이스 실행 ---
10:10:03 [sqli] 기본 SQL Injection - ' OR 1=1    [1/3] 🛡️  HTTP 403 (0.05s)
10:10:04 [sqli] 기본 SQL Injection - ' OR 1=1    [2/3] 🛡️  HTTP 403 (0.04s)
...

============================================================
📊 테스트 실행 결과 요약
============================================================
  총 테스트 케이스: 325
  전송 성공:        975 (325 x 3회 반복)
  전송 실패:        0
  🛡️  WAF 탐지:     280 (86.2%)
  소요 시간:        12분 35초
============================================================
📈 WAF가 높은 탐지율을 보이고 있습니다!
============================================================

다음 단계: python 04_collect_logs.py
```

#### 🎯 특정 테스트만 실행하기
```bash
# SQL Injection만 실행 (45개)
python scripts/03_run_attack_tests.py --test sqli

# XSS만 실행 (45개)
python scripts/03_run_attack_tests.py --test xss

# Command Injection만 실행 (30개)
python scripts/03_run_attack_tests.py --test command_injection

# SSRF만 실행 (25개)
python scripts/03_run_attack_tests.py --test ssrf

# 신규 카테고리 테스트
python scripts/03_run_attack_tests.py --test xxe
python scripts/03_run_attack_tests.py --test nosql_injection
python scripts/03_run_attack_tests.py --test ssti
python scripts/03_run_attack_tests.py --test jwt_attacks
```

#### 🔍 실제 전송 없이 미리보기 (Dry Run)
```bash
python scripts/03_run_attack_tests.py --dry-run
```

---

### Step 04: 로그 수집 ⏱ 30초

**목적**: BIG-IP에서 WAF가 탐지한 보안 로그(Security violations)를 자동으로 수집합니다.

```bash
python scripts/04_collect_logs.py
```

**정상 출력 예시**:
```
10:30:00 [INFO] ============================================================
10:30:00 [INFO] [04] Collect Logs 시작
10:30:00 [INFO] ============================================================
10:30:00 [INFO] Security 로그 수집 중 (최근 30분)...
10:30:02 [INFO] ✅ Security 로그 수집 완료: 280개 발견

  [탐지된 공격 유형]
    - SQL Injection: 120회
    - Cross Site Scripting (XSS): 85회
    - Path Traversal: 50회
    - Command Execution: 25회

10:30:03 [INFO] ✅ security 로그 저장 완료: output/logs/security_latest.json

============================================================
📋 로그 수집 완료: 총 280개 로그
============================================================
  - security: 280개

다음 단계: python 05_generate_report.py
============================================================
```

---

### Step 05: HTML 리포트 생성 ⏱ 5초

**목적**: 테스트 결과와 로그를 기반으로 차트와 표가 포함된 HTML 리포트를 자동 생성합니다.

```bash
python scripts/05_generate_report.py
```

**정상 출력 예시**:
```
10:35:00 [INFO] ============================================================
10:35:00 [INFO] [05] Generate Report 시작
10:35:00 [INFO] ============================================================
10:35:00 [INFO] 테스트 결과 로드 중...
10:35:00 [INFO]   ✅ 325개 테스트 결과 로드 완료
10:35:00 [INFO] 보안 로그 로드 중...
10:35:00 [INFO]   ✅ 280개 보안 로그 로드 완료
10:35:00 [INFO] HTML 리포트 생성 중...
10:35:01 [INFO] ✅ HTML 리포트 저장 완료: C:\...\f5-awaf-testlab-factory\reports\result.html

============================================================
🎉 리포트 생성 완료!
📄 파일: C:\...\f5-awaf-testlab-factory\reports\result.html
============================================================
```

**✅ 리포트 확인**: `reports/result.html` 파일을 브라우저로 열면 됩니다.

---

### 🚀 빠른 실행 (All-in-One)

모든 단계를 연속으로 실행하려면:

```bash
for script in scripts/[0-9]*.py; do
    echo "=== Running $script ==="
    python "$script" || { echo "❌ $script failed"; exit 1; }
done
```

> 💡 **주의**: DO(Step 01)는 이미 설정된 장비에서 실행하면 네트워크가 재설정될 수 있습니다.
> 이미 설정이 완료된 장비라면 Step 01은 건너뛰고 Step 02부터 실행하는 것을 추천합니다.

---

## ⚠️ 문제 해결 - WAF 정책 파일 업로드

Step 02 실행 시 "WAF 정책 파일 업로드" 단계에서 실패하면 아래 방법으로 수동 업로드 후 다시 실행하세요.

### 방법 1: SCP를 통한 수동 업로드 (권장)
```bash
# 로컬 PC에서 실행 (BIG-IP 관리 IP: 192.168.137.125)
scp declarations/waf_policy_template.json admin@192.168.137.125:/var/config/rest/iapps/as3/declarations/
```

### 방법 2: WinSCP 사용 (Windows)
1. WinSCP 실행
2. 파일 프로토콜: **SCP** 선택
3. 호스트: `192.168.137.125`
4. 사용자: `admin`, 비밀번호: `admin`
5. 로컬 파일: `declarations/waf_policy_template.json`
6. 원격 경로: `/var/config/rest/iapps/as3/declarations/`
7. 업로드 후 다시 `python scripts/02_deploy_as3.py` 실행

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
  host: "192.168.137.125"       # 귀하의 BIG-IP IP
  username: "admin"
  password: "admin"

# DVWA 접속 정보
target:
  vip_address: "192.168.137.211" # Virtual Server IP
  dvwa:
    url: "http://192.168.137.211"
    security_level: "low"
```

### 환경별 커스터마이징

1. **BIG-IP IP 변경** - `lab.yml`의 `bigip.host` 수정 (현재: 192.168.137.125)
2. **Virtual Server IP 변경** - `lab.yml`의 `target.vip_address` 수정 (현재: 192.168.137.211)
3. **DVWA 백엔드 IP 변경** - `declarations/as3_dvwa_awaf.json.j2`에서 `serverAddresses` 수정 (현재: 192.168.137.113)
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
