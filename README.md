# OpenClaw Telegram Mini App

Telegram 안에서 OpenClaw를 더 빠르고 가볍게 다루기 위한 **한국어 Telegram Mini App 포크**입니다.
원본 프로젝트인 [clawvader-tech/hermes-telegram-miniapp](https://github.com/clawvader-tech/hermes-telegram-miniapp)을 바탕으로 OpenClaw 환경에 맞게 포팅했고, 원본의 MIT 라이선스를 그대로 유지합니다.

먼저, 훌륭한 기반 프로젝트를 공개해 준 원작자에게 감사드립니다.
이 포크는 원작의 방향성과 장점을 존중하면서, OpenClaw에서 바로 쓸 수 있는 실용적인 형태로 다듬는 것을 목표로 합니다.

## 한 줄 소개

**OpenClaw용 Telegram Mini App companion**입니다.
채팅만 붙인 데모가 아니라, 모바일에서 OpenClaw의 **chat, status, sessions, agents, cron**을 바로 확인하고 다룰 수 있게 만드는 쪽에 초점을 두고 있습니다.

## 왜 이 리포를 봐야 하나요?

이 포크는 아래 같은 OpenClaw 사용자에게 특히 잘 맞습니다.

- Telegram 안에서 바로 OpenClaw를 열고 싶은 사람
- 모바일에서 상태 확인과 간단한 운영 작업까지 하고 싶은 사람
- 한국어 UI가 필요한 사람
- Cloudflare Tunnel 기반으로 self-hosted Mini App을 붙이고 싶은 사람
- Hermes용 Mini App 아이디어를 OpenClaw에 맞게 재구성한 사례가 필요한 사람

즉, "Hermes용 Mini App을 억지로 흉내 내는 포크"가 아니라,
**OpenClaw에 맞게 다시 연결한 Telegram Mini App 포크**에 가깝습니다.

## 현재 상태

이 포크는 이미 **기본 동작 가능한 수준**을 넘어서,
OpenClaw 운영 companion으로 실제 써볼 수 있는 단계까지 올라와 있습니다.

최근 반영 범위:

- OpenClaw 브랜딩 반영
- 한국어 UI 1차 적용
- OpenClaw chat 연결
- OpenClaw 세션 헤더 연결
- Mini App bridge 추가
- 크론 목록 조회 및 기본 액션 연결
- macOS용 bridge launchd 실행 구성 추가
- 런타임 상태, 에이전트, 세션 패널 추가
- 외부 health / cloudflared 상태 / diagnostics 표시 강화
- owner 제한 및 인증 하드닝 반영

## 지금 동작하는 것

현재 이 포크에서 동작하는 핵심 기능은 아래와 같습니다.

### Mobile companion UI
- Telegram Mini App 기본 UI
- OpenClaw Gateway를 통한 채팅
- 상태 패널
- 세션 목록 / 세션 상태 확인
- 에이전트 / subagent 상태 확인
- 크론 목록 조회 및 기본 실행 액션

### Bridge / API
- `/v1/chat/completions` 프록시 연결
- `/api/model-info`
- `/api/session-usage`
- `/api/jobs`
- `/api/command`
- `/api/runtime-status`
- `/api/subagents`
- `/api/diagnostics`

### 운영 기능
- 브라우저 fallback용 Bearer token 인증
- Telegram Mini App 기반 인증 경로
- Cloudflare / public origin 이상 탐지용 diagnostics
- bridge launchd 실행 구성
- Cloudflare Tunnel 운영 체크리스트 포함

## 포함된 브리지

이 저장소에는 작은 OpenClaw 브리지 서버가 포함되어 있습니다.

- `bridge/openclaw_miniapp_bridge.py`
- `bridge/run_bridge.sh`
- `systemd/openclaw-miniapp-bridge.service`
- `launchd/ai.openclaw.miniapp-bridge.plist`

이 브리지는 Mini App 프런트와 OpenClaw 사이에서 다음 역할을 맡습니다.

- 정적 Mini App 파일 서빙
- OpenClaw chat endpoint 프록시
- 모델/세션 정보 조회
- `openclaw cron` 기반 작업 조회 및 액션 연결
- 간단한 명령 호환 레이어 제공
- subagents / diagnostics 같은 운영용 데이터 노출

## OpenClaw 설정에서 필요한 것

채팅 프록시를 사용하려면 OpenClaw Gateway에서 HTTP chat completions endpoint를 켜야 합니다.

```json5
{
  gateway: {
    http: {
      endpoints: {
        chatCompletions: { enabled: true }
      }
    }
  }
}
```

설정 후에는 gateway 재시작이 필요합니다.

## 빠른 배포 개요

현재 로컬 브리지는 `127.0.0.1:8765` 에서 동작하도록 맞춰져 있고,
실배포 기본 도메인은 아래 기준으로 정리했습니다.

- 권장 Mini App origin: `https://miniapp.techkwon.kr`
- launchd 기본값: `MINIAPP_PUBLIC_ORIGIN=https://miniapp.techkwon.kr`
- Cloudflare Tunnel 예시 파일: `tunnel/cloudflared-config.yml`

권장 배포 순서:

1. `cloudflared tunnel login`
2. `cloudflared tunnel create openclaw-miniapp`
3. `cloudflared tunnel route dns openclaw-miniapp miniapp.techkwon.kr`
4. `~/.cloudflared/config.yml` 에 `tunnel/cloudflared-config.yml` 내용을 실제 tunnel UUID로 반영
5. `cloudflared tunnel --config ~/.cloudflared/config.yml tunnel run openclaw-miniapp`
6. Telegram Bot 설정에서 Mini App URL 또는 Menu Button URL을 `https://miniapp.techkwon.kr` 로 교체

주의:

- Telegram Mini App 엔트리포인트는 `trycloudflare.com` 같은 임시 URL보다 고정 hostname이 훨씬 안전합니다.
- 실제 Telegram 쪽 URL 교체는 Cloudflare named tunnel이 정상 응답하는 것을 먼저 확인한 뒤 진행하는 것이 좋습니다.
- launchd plist를 수정한 뒤 환경 변수를 확실히 반영하려면 단순 kickstart보다 `bootout -> bootstrap` 재적용이 더 안전할 수 있습니다.
- 운영 중 장애 분리 순서는 [`OPERATIONS_CHECKLIST.md`](OPERATIONS_CHECKLIST.md)를 바로 참고하면 됩니다.

## 이 포크가 원본과 다른 점

원본 프로젝트는 이미 훌륭한 사용자 경험과 UI 감각을 갖고 있었습니다.
다만 OpenClaw는 Hermes와 백엔드 구조가 완전히 같지 않기 때문에, 그대로 가져오면 동작하지 않는 지점들이 있었습니다.

그래서 이 포크에서는 아래 원칙을 지키고 있습니다.

- 안 되는 기능을 되는 척하지 않기
- OpenClaw에 맞는 연결 방식을 명확히 만들기
- 원본 크레딧과 라이선스 의무를 유지하기
- 사용자 입장에서는 더 단순하고 실용적으로 보이게 만들기
- 관리자용 대시보드를 그대로 노출하기보다 모바일 companion 경험에 집중하기

## 저장소에서 바로 볼 만한 파일

- `bridge/openclaw_miniapp_bridge.py` - OpenClaw 연결 핵심 bridge
- `index.html` - Mini App 프런트엔드
- `OPERATIONS_CHECKLIST.md` - 장애 대응 체크리스트
- `tunnel/cloudflared-config.yml` - Cloudflare Tunnel 예시 설정
- `launchd/ai.openclaw.miniapp-bridge.plist` - macOS launchd 예시

## 앞으로 더 다듬을 부분

아직 더 좋아질 수 있는 부분도 분명히 있습니다.

- README에 실제 스크린샷 / GIF 추가
- 상태/크론 패널의 OpenClaw 네이티브 데이터 확장
- Telegram Mini App 인증 검증 고도화
- 설치/배포 문서 세분화
- 세션/에이전트 조작 UX 개선

## 개발 방향

이 포크는 다음 원칙으로 유지합니다.

- 원본 MIT 라이선스 유지
- 원작자 명시적 크레딧 유지
- 포크 상태를 README에서 정직하게 설명
- OpenClaw에 없는 Hermes 전용 기능을 과장하지 않음
- OpenClaw 사용자 경험은 한국어 중심으로 정리
- 모바일 운영 companion으로서 실제 유용성을 우선함

## 저장소 링크

- 원본 프로젝트: <https://github.com/clawvader-tech/hermes-telegram-miniapp>
- 이 포크: <https://github.com/techkwon/openclaw-telegram-miniapp>

## 라이선스

원본 프로젝트와 이 포크는 모두 MIT License를 따릅니다.
자세한 내용은 [LICENSE](LICENSE)를 참고해 주세요.
