# F5 AWAF 모니터링 - Grafana + Loki + Promtail

> **WSL2 + Docker Desktop** 환경에서 F5 BIG-IP WAF 로그를 실시간으로 모니터링합니다.

## 전체 구성도

```
┌─ Proxmox (Mini PC) ─────────────────────┐
│  F5 BIG-IP (192.168.137.125)            │
│    └─ ASM 로그 → syslog (UDP 1514) ─────┼─────┐
└──────────────────────────────────────────┘     │
                                                 ▼
┌─ 노트북 (WSL2 + Docker Desktop) ─────────────────┐
│                                                    │
│  Promtail (port 1514)                              │
│    └─ syslog 수신 → 로그 파싱                      │
│         │                                          │
│         ▼                                          │
│  Loki (port 3100)                                  │
│    └─ 로그 저장/검색                                │
│         │                                          │
│         ▼                                          │
│  Grafana (port 3000)                               │
│    └─ http://localhost:3000                         │
│       ├─ ID: admin / PW: admin                     │
│       └─ Loki Data Source 자동 연결                 │
│       └─ F5 AWAF 대시보드 자동 임포트              │
└────────────────────────────────────────────────────┘
```

---

## 1️⃣ WSL2 + Docker Desktop 설치 (처음 1회)

### Windows PowerShell (관리자 권한)에서 실행

```powershell
# 1. WSL2 활성화
wsl --install -d Ubuntu

# 2. 재부팅 후 Ubuntu 초기 설정 (계정/비밀번호 생성)

# 3. Docker Desktop 설치
#    https://docs.docker.com/desktop/setup/install/windows-install/
#    → 다운로드 후 설치
#    → Settings > Resources > WSL Integration > "Ubuntu" ON

# 4. PowerShell에서 WSL2 기본 버전 확인
wsl -l -v
#    → Ubuntu가 2로 표시되어야 함
```

### Ubuntu(WSL2) 터미널에서 실행

```bash
# Ubuntu 업데이트
sudo apt update && sudo apt upgrade -y

# Docker Compose 확인
docker compose version
# → Docker Desktop이 설치되면 WSL2 내에서 docker 명령어 사용 가능
```

---

## 2️⃣ 프로젝트 준비

```bash
# WSL2 Ubuntu에서 프로젝트 클론
cd ~
git clone https://github.com/RaonL/testlab.git
cd testlab/monitoring

# 디렉토리 구조 확인
ls -la
# ├── docker-compose.yml
# ├── loki/loki-config.yml
# ├── promtail/promtail-config.yml
# └── grafana/
#     ├── datasources/datasource.yml
#     └── dashboards/
#         ├── dashboard.yml
#         └── f5_awaf_dashboard.json
```

---

## 3️⃣ 모니터링 스택 실행

```bash
# 모니터링 폴더로 이동
cd ~/testlab/monitoring

# 컨테이너 실행
docker compose up -d

# 상태 확인
docker compose ps
# NAME            IMAGE                    PORTS
# f5-grafana      grafana/grafana:11.6.1  0.0.0.0:3000->3000/tcp
# f5-loki         grafana/loki:3.7.2      0.0.0.0:3100->3100/tcp
# f5-promtail     grafana/promtail:3.7.2  0.0.0.0:1514->1514/tcp,udp

# 로그 확인 (오류 없는지 체크)
docker compose logs -f
```

---

## 4️⃣ Grafana 접속 확인

```bash
# WSL2 IP 확인 (같은 PC에서 접속 시 localhost 사용 가능, 외부 접속용)
ip addr show eth0 | grep "inet "

# 브라우저에서 접속
# → http://localhost:3000
# → ID: admin / PW: admin
```

**자동 설정 확인:**
1. ✅ Loki Data Source가 이미 등록되어 있어야 함
2. ✅ "F5 AWAF - 실시간 WAF 모니터링" 대시보드가 자동 임포트되어야 함

---

## 5️⃣ BIG-IP → Promtail syslog 연결

> ⚠️ **중요**: BIG-IP가 WSL2의 Promtail(포트 1514)로 syslog를 보낼 수 있어야 합니다.
> WSL2는 기본적으로 NAT 네트워크이므로 **Windows 방화벽 포트포워딩**이 필요합니다.

### Windows PowerShell (관리자 권한) - 포트포워딩 설정

```powershell
# WSL2 IP 확인 (WSL2 Ubuntu에서 실행)
wsl -- ip addr show eth0 | findstr "inet "
# → 예: 172.27.64.1

# Windows → WSL2 포트포워딩 (관리자 PowerShell)
netsh interface portproxy add v4tov4 listenport=1514 listenaddress=0.0.0.0 connectport=1514 connectaddress=172.27.64.1

# Windows 방화벽 인바운드 규칙 추가 (1514번 포트 열기)
netsh advfirewall firewall add rule name="Promtail 1514" dir=in action=allow protocol=TCP localport=1514
netsh advfirewall firewall add rule name="Promtail 1514 UDP" dir=in action=allow protocol=UDP localport=1514

# 포트포워딩 확인
netsh interface portproxy show all
```

### 노트북 Windows IP 확인

```powershell
ipconfig
# → 무선 LAN 어댑터 Wi-Fi: 192.168.137.x (동일 네트워크여야 함)
```

### BIG-IP에서 syslog 설정 (BIG-IP CLI)

```bash
# BIG-IP SSH 접속
ssh admin@192.168.137.125

# 원격 syslog 설정 (노트북 IP가 192.168.137.50 이라고 가정)
tmsh create sys syslog remote-servers { notebook-mon { host 192.168.137.50 port 1514 } }

# ASM 로그를 syslog로 전송하도록 설정
tmsh modify sys syslog remote-servers/notebook-mon { format RFC-5424 }

# 설정 저장
tmsh save sys config
```

### BIG-IP에서 syslog 설정 (웹 UI)
1. **BIG-IP 웹 UI 접속**: `https://192.168.137.125`
2. **System → Logs → Configuration → Remote Logging**
3. **Remote Servers** → **Add**
   - Name: `notebook-mon`
   - Host: `192.168.137.50` (노트북 IP)
   - Port: `1514`
   - Protocol: `UDP`
4. **Update** → **Save**

---

## 6️⃣ 테스트 및 확인

```bash
# Promtail 로그 확인 (syslog 수신 여부)
docker compose logs promtail | tail -20
# → "received message" 로그가 보이면 정상 수신 중

# Grafana 대시보드 확인
# 브라우저 → http://localhost:3000
# → "F5 AWAF - 실시간 WAF 모니터링" 대시보드 열기
# → 공격 추세, Top 10 공격 유형, Top 10 IP 등 확인
```

### 직접 테스트 로그 보내보기

```bash
# WSL2에서 테스트 로그 전송 (BIG-IP 없이 테스트)
echo '<14>1 2024-01-01T12:00:00Z bigip asm - - [src_ip=192.168.1.100 violation=SQL_INJECTION request_status=blocked uri="/test?id=1"]' | nc -u localhost 1514
```

---

## 7️⃣ 유용한 명령어

```bash
# 서비스 중지
docker compose down

# 서비스 재시작
docker compose restart

# 로그 실시간 보기
docker compose logs -f promtail

# Loki에 저장된 로그 개수 확인
curl -s "http://localhost:3100/loki/api/v1/query?query=count_over_time({job=~\"f5_asm_syslog.*\"}[1h])" | jq

# 불필요한 데이터 삭제 (디스크 공간 확보)
docker compose down -v  # 볼륨까지 삭제 (모든 로그 초기화)
```

---

## 8️⃣ 문제 해결

| 증상 | 원인 | 해결 |
|------|------|------|
| Grafana 3000 접속 안 됨 | Docker 미실행 | `docker compose up -d` 실행 |
| Promtail 로그 없음 | BIG-IP에서 syslog 도달 안 함 | 1) Windows 방화벽 확인 2) `netsh portproxy` 확인 3) BIG-IP syslog 설정 확인 |
| Loki 연결 오류 | Loki 컨테이너 미실행 | `docker compose logs loki` 확인 |
| 대시보드 안 보임 | 프로비저닝 실패 | Grafana 재시작: `docker compose restart grafana` |
| WSL2 IP 변경됨 | WSL2 재시작 | `netsh interface portproxy` 재설정 필요 |
| 포트 충돌 (3000/3100 이미 사용 중) | 다른 프로그램이 포트 사용 중 | `docker-compose.yml`에서 포트 변경 (예: 3001:3000) |
