# OpenClaw Telegram Mini App

Telegram 안에서 OpenClaw를 조금 더 가볍고 빠르게 다루기 위한 Mini App 포크입니다.
원본 프로젝트인 [clawvader-tech/hermes-telegram-miniapp](https://github.com/clawvader-tech/hermes-telegram-miniapp)을 바탕으로 OpenClaw 환경에 맞게 포팅하고 있으며, 원본의 MIT 라이선스를 그대로 유지합니다.

먼저, 훌륭한 기반 프로젝트를 공개해 준 원작자에게 감사드립니다.
이 포크는 원작의 방향성과 장점을 존중하면서, OpenClaw에서 바로 쓸 수 있는 실용적인 형태로 다듬는 것을 목표로 합니다.

## 이 프로젝트는 무엇인가요?

이 저장소는 다음을 목표로 합니다.

- Telegram Mini App 형태의 UI 유지
- OpenClaw Gateway와 자연스럽게 연결
- 모바일에서 빠르게 상태 확인, 대화, 크론 작업 확인 가능
- OpenClaw 사용자에게 맞는 한국어 UI 제공

즉, "Hermes용 Mini App"을 억지로 흉내 내는 포크가 아니라,
**OpenClaw에 맞게 다시 연결한 Telegram Mini App 포크**에 가깝습니다.

## 현재 상태

이 포크는 이미 **기본 동작 가능한 수준**까지 올라와 있습니다.

현재 확인된 범위:

- OpenClaw 브랜딩 반영
- 한국어 UI 1차 적용
- OpenClaw chat 연결
- OpenClaw 세션 헤더 연결
- Mini App bridge 추가
- 크론 목록 조회 및 기본 액션 연결
- macOS용 bridge launchd 실행 구성 추가

## 지금 동작하는 것

현재 이 포크에서 동작하는 핵심 기능은 아래와 같습니다.

- Telegram Mini App 기본 UI
- OpenClaw Gateway를 통한 채팅
- `/api/model-info`
- `/api/session-usage`
- `/api/jobs` 기반 크론 조회/수정/실행 연동
- `/api/command` 기반 간단 명령 실행
- `/v1/chat/completions` 프록시 연결
- 브라우저 fallback용 Bearer token 인증
- Telegram Mini App 헤더 기반 인증 경로

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

## 왜 이 포크를 만들었나요?

원본 프로젝트는 이미 훌륭한 사용자 경험과 UI 감각을 갖고 있었습니다.
다만 OpenClaw는 Hermes와 백엔드 구조가 완전히 같지 않기 때문에, 그대로 가져오면 동작하지 않는 지점들이 있었습니다.

그래서 이 포크에서는 아래 원칙을 지키고 있습니다.

- 안 되는 기능을 되는 척하지 않기
- OpenClaw에 맞는 연결 방식을 명확히 만들기
- 원본 크레딧과 라이선스 의무를 유지하기
- 사용자 입장에서는 더 단순하고 실용적으로 보이게 만들기

## 앞으로 다듬을 부분

아직 더 좋아질 수 있는 부분도 분명히 있습니다.

- 남아 있는 일부 영문 문구 정리
- 상태/크론 패널의 OpenClaw 네이티브 데이터 확장
- Telegram Mini App 인증 검증 고도화
- 배포 문서 정리
- 도메인/터널/실배포 가이드 추가

## 개발 방향

이 포크는 다음 원칙으로 유지합니다.

- 원본 MIT 라이선스 유지
- 원작자 명시적 크레딧 유지
- 포크 상태를 README에서 정직하게 설명
- OpenClaw에 없는 Hermes 전용 기능을 과장하지 않음
- OpenClaw 사용자 경험은 한국어 중심으로 정리

## 저장소 링크

- 원본 프로젝트: <https://github.com/clawvader-tech/hermes-telegram-miniapp>
- 이 포크: <https://github.com/techkwon/openclaw-telegram-miniapp>

## 라이선스

원본 프로젝트와 이 포크는 모두 MIT License를 따릅니다.
자세한 내용은 [LICENSE](LICENSE)를 참고해 주세요.
