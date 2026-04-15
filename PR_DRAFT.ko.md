# PR 초안

## 제목
OpenClaw Telegram Mini App의 배포 준비도와 브라우저 세션 보안을 강화합니다

## 요약
이 PR은 OpenClaw Telegram Mini App을 실제 self-hosted 운영에 더 적합하게 다듬는 데 초점을 맞췄습니다.

핵심 축은 두 가지입니다.

1. 브라우저 fallback 인증 보안 강화
2. 배포 및 운영 준비도 향상

## 변경 사항

### 브라우저 세션 보안
- bridge가 발급하는 short-lived browser session token 추가
- `/api/auth/session`, `/api/auth/refresh`, `/api/auth/revoke` 추가
- 만료 전 자동 refresh 추가
- 브라우저 설정 화면에서 현재 세션을 revoke하는 logout 흐름 추가
- fallback 브라우저 모드에서 장기 shared token 노출을 줄임

### 신뢰성 하드닝
- refresh race 완화를 위한 server-side refresh cache/lock 추가
- client-side in-flight refresh dedupe 추가
- 일시적 refresh 실패에 대한 retry 처리 추가
- 브라우저 token persistence 경로를 통합해 부분 저장 실패 케이스를 줄임

### 배포 준비도 향상
- 주요 배포 설정에 대한 startup config validation 추가
- request ID, status, duration, auth kind를 포함하는 구조화 JSON 요청 로그 추가
- 민감한 인증 값은 로그에 남기지 않도록 유지
- `.env.example` 확장
- README에 production checklist 및 보안 메모 추가

## 왜 중요한가
- 브라우저 fallback 경로를 self-hosted 배포에 더 안전하게 만듭니다
- 세션 refresh 실패 시 동작을 더 안정적으로 만듭니다
- 잘못된 배포 설정을 시작 시점에 빨리 발견할 수 있습니다
- 구조화 로그로 운영 중 문제 파악이 쉬워집니다
- 단순히 동작하는 포크를 넘어서, 실제 배포 가능한 포크에 가깝게 끌어올립니다

## 검증
- `python3 -m py_compile bridge/openclaw_miniapp_bridge.py`
- `index.html` 스크립트 파싱 확인
- auth/session 흐름 및 배포 문서 diff 수동 검토

## 참고
- 이 변경은 대규모 multi-tenant 서비스보다는 개인 또는 소규모 self-hosted 운영을 우선한 설계입니다
- 남은 작업은 핵심 인증 정확성보다는 문서 분리와 운영 가이드 확장 쪽에 더 가깝습니다

## 리뷰 포인트 제안
- 브라우저 fallback 인증 생명주기
- refresh/revoke edge case
- startup validation 범위
- 로그 안전성과 운영 활용성
