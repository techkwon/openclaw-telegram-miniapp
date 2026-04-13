# OpenClaw Telegram Mini App 운영 체크리스트

이 문서는 `openclaw-telegram-miniapp` 운영 시 장애를 빠르게 분리하기 위한 실전 체크리스트입니다.

기본 전제:
- 로컬 bridge: `http://127.0.0.1:8765`
- 권장 public origin: `https://miniapp.techkwon.kr`
- Mini App은 Telegram, Cloudflare Tunnel, local bridge, OpenClaw Gateway가 모두 맞물려야 정상 동작합니다.

---

## 1. 가장 먼저 볼 것

Mini App의 **상태 탭**에서 아래를 먼저 봅니다.

1. `Cloudflared 서비스`
2. `Tunnel 프로세스 수`
3. `외부 health probe`
4. `외부 응답`
5. 상단 경고 배너
6. `마지막 오류`

이 6개만 봐도 대부분의 장애는 아래 네 가지로 나뉩니다.

- 로컬 bridge 문제
- OpenClaw Gateway 문제
- Cloudflare Tunnel / Public Hostname 문제
- Telegram 인증 또는 접근 문제

---

## 2. 빠른 판별표

### A. 로컬 bridge 문제
증상:
- `http://127.0.0.1:8765/health` 실패
- 상태 탭 자체가 안 뜨거나 로컬 접속이 거부됨

우선 확인:
- bridge launchd 서비스 재시작
- bridge 프로세스 살아있는지 확인
- bridge 로그 확인

### B. OpenClaw Gateway 문제
증상:
- bridge는 열리지만 채팅/명령이 실패
- 상태 탭에서 `Gateway 연결`이 불안정

우선 확인:
- OpenClaw gateway 상태
- `gateway.http.endpoints.chatCompletions.enabled=true`
- gateway token / base url 설정

### C. Cloudflare Tunnel / Hostname 문제
증상:
- 로컬 `127.0.0.1:8765/health` 는 200
- `https://miniapp.techkwon.kr/health` 는 실패
- 상태 탭 상단에 `Cloudflare Tunnel 연결 문제 감지` 또는 `외부 접속 이상 감지`

우선 확인:
- named tunnel 연결 상태
- Public Hostname이 실제 활성 tunnel에 붙어 있는지
- launchd cloudflared 서비스 상태
- 중복 tunnel 프로세스 존재 여부

### D. Cloudflare 보안/WAF 차단
증상:
- 상태 탭 상단에 `Cloudflare 보안 차단 감지`
- 외부 응답에 `1010` 흔적

우선 확인:
- Cloudflare WAF / Security Events
- 해당 hostname/path에 걸린 규칙
- 봇/국가/IP 기반 차단 여부

### E. Telegram 인증 문제
증상:
- Mini App은 열리지만 API가 401
- 브라우저 테스트는 되는데 Telegram 안에서 실패

우선 확인:
- Telegram bot token 설정
- bridge의 `initData` 검증 상태
- Ed25519 검증 가능 여부
- Telegram menu/webapp URL이 현재 public origin과 일치하는지

---

## 3. 표준 확인 순서

### 1단계, 로컬 bridge 확인

```bash
curl http://127.0.0.1:8765/health
```

기대 결과:
- HTTP 200

실패하면:
- Cloudflare보다 먼저 bridge부터 복구합니다.

### 2단계, public origin 확인

```bash
curl https://miniapp.techkwon.kr/health
```

기대 결과:
- HTTP 200

로컬은 되는데 public만 실패하면:
- bridge가 아니라 Cloudflare 쪽 문제로 봅니다.

### 3단계, Telegram 등록 URL 확인

확인할 것:
- Telegram Menu Button / Web App URL이 `https://miniapp.techkwon.kr/` 인지

로컬도 정상, Cloudflare도 정상인데 Telegram만 이상하면:
- Telegram 등록 URL 또는 Telegram 인증 흐름을 봅니다.

---

## 4. 자주 보는 오류 코드

### 401
- 인증 실패
- Telegram `initData` 검증 실패 또는 Bearer 문제

### 403
- 접근 거부
- owner 제한 또는 인증은 됐지만 권한이 맞지 않음

### 1010
- Cloudflare 보안 규칙 차단
- WAF / Security Events 확인 필요

### 1033
- Cloudflare Tunnel connector/hostname 연결 문제
- Public Hostname이 현재 연결된 tunnel과 어긋난 경우가 많음

### 5xx
- bridge 또는 OpenClaw Gateway 내부 오류
- 로컬 로그와 gateway 상태를 먼저 확인

---

## 5. 운영 명령 메모

### bridge 헬스 확인

```bash
curl http://127.0.0.1:8765/health
```

### public origin 헬스 확인

```bash
curl https://miniapp.techkwon.kr/health
```

### cloudflared LaunchAgent 상태 확인

```bash
launchctl print gui/$(id -u)/com.cloudflare.cloudflared
```

### 중복 tunnel 프로세스 확인

```bash
pgrep -fl 'cloudflared tunnel run --token'
```

### bridge 재기동

```bash
launchctl kickstart -k gui/$(id -u)/ai.openclaw.miniapp-bridge
```

### cloudflared 재적용

launchd 환경값이 꼬였을 때는 `kickstart`만으로 부족할 수 있습니다.
이 경우 아래 순서가 더 안전합니다.

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.cloudflare.cloudflared.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.cloudflare.cloudflared.plist
launchctl kickstart -k gui/$(id -u)/com.cloudflare.cloudflared
```

---

## 6. 중요한 운영 교훈

### 1. Quick Tunnel은 엔트리포인트로 쓰지 않기
- `trycloudflare.com` URL은 바뀔 수 있습니다.
- Telegram Mini App 엔트리포인트는 **named tunnel + 고정 hostname** 기준으로 운영합니다.

### 2. plist만 고쳐서는 live 값이 안 바뀔 수 있음
- launchd는 예전 값으로 계속 떠 있을 수 있습니다.
- 특히 token/env 변경 때는 `bootout -> bootstrap` 이 안전합니다.

### 3. 수동 cloudflared와 LaunchAgent를 같이 띄우지 않기
- 중복 connector는 진단을 어렵게 만듭니다.
- 운영 기준은 **단일 LaunchAgent 인스턴스**입니다.

### 4. 기능 추가보다 장애 가시화가 먼저
- 이 Mini App의 상업용 기준 필수는 화려한 기능보다
  **왜 실패했는지 바로 보이는 것**입니다.

---

## 7. 장애 대응 추천 순서

1. 상태 탭 열기
2. 상단 경고 배너 확인
3. `외부 health probe` 와 `외부 응답` 확인
4. 로컬 `/health` 확인
5. public `/health` 확인
6. cloudflared 단일 프로세스 여부 확인
7. Telegram URL / 인증 확인
8. `마지막 오류` 확인 후 필요하면 `오류 지우기`

---

## 8. 정상 상태 기준

정상일 때 기대값:
- `Gateway 연결`: 정상
- `Cloudflared 서비스`: 실행 중
- `Tunnel 프로세스 수`: 1
- `외부 health probe`: 정상
- `Public origin`: `https://miniapp.techkwon.kr`
- 상단 경고 배너 없음
- `마지막 오류`: 없음 또는 이미 정리됨

이 상태인데도 사용자 이슈가 있다면,
그때는 세션/명령/프런트 UX 쪽 문제를 의심합니다.
