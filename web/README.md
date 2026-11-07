# 사용자 웹 앱

`web/`은 `chatbot/`의 라우팅·Q-Form·RAG·OOS 로직을 호출하는 FastAPI 서버와 정적
HTML/CSS/JavaScript UI입니다. 관리자 서버와 별도 프로세스로 실행합니다.

## 실행

리포지토리 루트에서:

```bash
source .venv/bin/activate
python -m uvicorn web.main:app --host 127.0.0.1 --port 8501
```

- 사용자 화면: <http://127.0.0.1:8501>
- API 문서: <http://127.0.0.1:8501/api/docs>
- 상태 확인: <http://127.0.0.1:8501/api/health>

필요한 의존성은 [SETUP](../SETUP.md)에 따라 검색과 FastAPI 패키지를 같은 가상환경에
설치합니다.

## 세션

- 세션 ID 형식: `sess_<16자리 hex>`
- 저장 위치: 현재 프로세스 메모리
- 만료: 마지막 접근 후 8시간
- 보관 내용: Q-Form 흐름 상태, 대화 이력, 화면 설정, 재생성 필요 여부
- 같은 세션의 동시 요청은 세션별 잠금으로 직렬화

서버를 재시작하면 세션과 프로세스 단위 LLM 호출 카운터가 초기화됩니다.

## API

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/api/health` | 서버 상태와 LLM 호출 예산 |
| POST | `/api/sessions` | 새 세션 생성 |
| GET | `/api/sessions/{id}` | 세션 상태 조회 |
| DELETE | `/api/sessions/{id}` | 세션 삭제 |
| POST | `/api/sessions/{id}/messages` | 사용자 메시지 처리 |
| POST | `/api/sessions/{id}/actions` | 되묻기·메모리 패널 액션 |
| PATCH | `/api/sessions/{id}/settings` | 세션 화면·동작 설정 |
| POST | `/api/sessions/{id}/reports` | 특정 답변 오류 신고 |
| GET | `/api/sessions/{id}/attachments/{attachment_id}` | 허용된 첨부 다운로드 |

오류 신고는 `admin/oos_store.py` 저장소에 개인정보 마스킹 후 보관됩니다. 첨부 다운로드는
`crawler/data/files/` 또는 관리자가 등록한 안전한 파일만 제공합니다.

## 관리자 설정 반영

`web/service.py`는 시작할 때 `admin/settings.py`의 저장값을 런타임 모듈에 적용하고, 이후 생성
요청마다 `refresh_runtime()`으로 `admin/data/admin_config.json`의 교체(mtime·크기·inode)를
확인합니다. 바뀌었으면 `settings.apply_runtime()`을 다시 호출하므로 관리자에서 저장한 값은 사용자
서버 재시작 없이 다음 생성 요청부터 반영됩니다. 청킹 설정은 재빌드가 끝나야 반영됩니다.

## 보안 경계

- 모델 응답은 HTML로 삽입하지 않고 일반 텍스트로 렌더링
- CSP, `nosniff`, `no-referrer`, 프레임 차단 헤더 적용
- 첨부 경로는 허용 저장소 밖으로 나가지 못하게 검증
- 오류 신고 저장 전 민감정보 마스킹

## 테스트

```bash
python -m pytest tests/test_web_api.py -q
node --check web/static/app.js
```
