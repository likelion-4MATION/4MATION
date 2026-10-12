# KDIC 챗봇 관리자 콘솔

비전공자 관리자가 검색·생성·Q-Form 설정을 조정하고, 데이터 재빌드와 첨부 관리, OOS 안내처,
오류 신고를 운영하는 FastAPI 웹 콘솔입니다.

> 기준: 2026-10-12 · 상세 계약은 [관리자콘솔 사양서](../docs/current/관리자콘솔_사양서.md)

## 실행

리포지토리 루트에서 가상환경을 활성화한 뒤:

```bash
source .venv/bin/activate
cd admin
python -m uvicorn main:app --host 127.0.0.1 --port 8600
```

관리자 서버: <http://127.0.0.1:8600>

`KDIC_REPO`를 설정하지 않으면 `admin/`의 상위 폴더를 저장소 루트로 사용합니다. 다른 위치를
사용하는 경우에만 명시합니다.

```bash
export KDIC_REPO=/path/to/repository
```

## 구성

| 파일 | 역할 |
|---|---|
| `main.py` | FastAPI API와 정적 UI 서빙 |
| `registry.py` | 파라미터 정의(현재 37개), 프리셋, 기준 설정 |
| `settings.py` | 설정 저장·검증·이력·런타임 주입 |
| `guards.py` | 최신성 정정 규칙 CRUD와 프롬프트 블록 생성 |
| `attachments.py` | 첨부 표시명·숨김·교체·추가 파일 오버레이, 업무 외 링크 |
| `runner.py` | 평가·재빌드·재검증·첨부 재수집 실행 |
| `jobs.py` | 작업 상태·진행률·중복 실행·판정 대기 관리 |
| `metrics.py` | 대시보드와 측정/추정 등급 계산 |
| `oos_store.py` | OOS 안내처·유선상담·오류 신고 SQLite 저장소 |
| `static/` | 관리자 HTML/CSS/JavaScript UI |

런타임 상태는 `admin/data/`에 저장됩니다. 이 중 `admin_config.json`·`attachments.json`·
`oos.sqlite3`는 팀 공유 초기값으로 Git에 추적되고, 업로드·백업·잡 기록은 추적하지 않습니다.
실행 중 생기는 변경을 다루는 방법은 [RUNBOOK §9](../docs/current/RUNBOOK.md#9-알려진-제약)를 봅니다.

## 화면과 설정

탭은 ① 답변 품질 · ② 응답 속도·비용 · ③ 되묻기 · ④ 최신성 가드 · ⑤ 첨부문서 · ⑥ 고급 ·
⑦ 문서 처리 · ⑧ OOS 안내처 · ⑨ 오류 신고함의 9개입니다. 탭별 기능과 `registry.PARAMS`
37개 항목의 기본값·범위·적용 대상은 [콘솔 사양서 §2·§3](../docs/current/관리자콘솔_사양서.md#2-화면-구조)이 정본입니다.

설정은 반영 방식에 따라 넷으로 나뉩니다.

- 일반 설정: 저장 후 사용자 챗봇의 다음 생성 요청부터 반영
- 고급 설정: 잠금 해제 후 변경
- 재빌드 설정: `pending`에 격리하고 성공한 재빌드 뒤 `override`로 승격
- 표시 전용: 임베딩 모델처럼 콘솔에서 수정하지 않는 항목

API 키·주소와 공급자별 실제 모델명은 `.env`에서만 관리하며 관리자 설정 파일에는 비밀값을
저장하지 않습니다.

## 작업 종류

| 종류 | 동작 | 홈페이지 접근 | 서비스 인덱스 영향 |
|---|---|---:|---:|
| `verify` | 현재 인덱스 읽기·평가 | 없음 | 없음 |
| `eval` | 샌드박스 재청킹·인덱싱·평가 후 복원 | 없음 | 없음 |
| `rebuild` | 저장 원문으로 서비스 인덱스 재생성 | 없음 | 교체 |
| `recrawl` | 라이브 원문 수집 후 서비스 인덱스 재생성 | 있음 | 교체 |
| `files` | 첨부 실파일 다운로드·연결 | 있음 | 재빌드 전까지 없음 |
| `chain` | 변경 종류에 따라 검증→재빌드→재검증 | 조건부 | 조건부 |

`runner.py`는 `crawler/`를 현재 폴더로 바꾸고 모듈 상수를 주입한 뒤 파이프라인을 호출합니다.
평가 모드는 `data/index_eval`을 사용하고 완료 뒤 삭제합니다.

### 읽기 전용 재검증

```bash
cd admin
python runner.py --mode verify --config '{}'
```

### 재빌드

```bash
cd admin
python runner.py --mode rebuild --config '{"CHUNK_SIZE":800,"OVERLAP":100}'
```

라우터와 임베딩을 함께 로드할 때 메모리가 부족하면 `exit 139`가 날 수 있습니다. 데이터 손상
오류와 구분해야 하며, 먼저 메모리를 확보한 뒤 재실행합니다.

### Q-Form 검색 반영 측정

`verify`·`eval`·`rebuild`는 평가 직전에 `Q-Form 메타데이터 확인` 단계를 거치고, 저장된
`QFORM_RETRIEVAL_MODE`·`QFORM_META_BOOST`·`QFORM_SCOPE`를 그대로 걸어 검색합니다. 문항 슬롯은
평가셋의 `business_function`을 넘겨 `chatbot/qform_extract.extract()`로 뽑습니다(LLM 호출 0).

결과의 `qform` 블록에는 슬롯이 잡힌 문항 수, 가산이 실제로 걸린 검색 결과 수, 그리고
**같은 문항을 Q-Form 없이 돌린 대조군과의 차이**(`hit@1`/`hit@5`/`mrr@10`)가 들어갑니다.
슬롯이 없는 문항은 두 경로의 검색 입력이 같으므로 대조군을 따로 돌리지 않습니다.

`qform_meta` 블록은 인덱스 청크의 태깅 현황입니다. 설정이 켜져 있어도 여기가 비어 있으면
검색은 순수 hybrid와 같습니다 — 원인은 두 가지로 갈립니다.

| 상태 | 뜻 | 조치 |
|---|---|---|
| `keyed=0` | Q-Form 태깅 이전에 만들어진 산출물 | 재청킹 |
| `keyed>0`, `tagged=0` | 조합표가 비었거나 추출기 미탑재 | `crawler/data/qform_combos_*.csv` 확인 |
| `boost=0` | 가산치가 0이라 순위가 안 바뀜 | ⑥ 고급의 `QFORM_META_BOOST` |

세 경우 모두 실행 전 경고(`/api/job`의 `preflight`)와 `/api/dashboard`의
`qform.effective=false`로 드러납니다.

## 인덱스 기준선 주의

대시보드 코퍼스 수는 `crawler/data/chunks.jsonl`, 실제 검색은
`crawler/data/index/chunk_meta.jsonl`을 읽습니다. 두 파일의 행 수가 다르면 대시보드와 서비스가
다른 코퍼스를 보고 있는 상태입니다.

```bash
wc -l ../crawler/data/chunks.jsonl ../crawler/data/index/chunk_meta.jsonl
```

이 경우 성능 숫자를 비교하지 말고 먼저 같은 원문·청킹 설정으로 인덱스를 재빌드합니다.

## 첨부 관리

크롤러 원본 파일은 `crawler/data/files/`에 있고 관리자 교체 파일은 `admin/data/uploads/`에
쌓입니다. 교체는 원본 삭제가 아니라 오버레이입니다.

- 원본 다운로드: 읽기 전용
- 표시명 수정·숨김: `admin/data/attachments.json`
- 교체·추가 파일: `admin/data/uploads/`
- 재수집: `fetch_attachments.py` → `link_files.py`
- 첨부 재수집 뒤 청크 메타 반영을 위해 재빌드 필요

## 운영 기능 상세

아래 주제는 이 README에 반복하지 않고 정본 문서를 따릅니다.

| 주제 | 정본 |
|---|---|
| OOS 안내처 게시 조건, 오류 신고 마스킹·30일 보관 | [OOS 구현·운영 가이드](../docs/current/OOS_구현_운영가이드.md) |
| 최신성 가드 매칭·프롬프트 주입·수치 허용 | [콘솔 사양서 §10](../docs/current/관리자콘솔_사양서.md#10-최신성-가드-배선-상태) |
| API 목록 | [콘솔 사양서 §11](../docs/current/관리자콘솔_사양서.md#11-api), 서버 실행 후 <http://127.0.0.1:8600/docs> |
| 성능 수치 해석, 코드 상수 기준선 | [콘솔 사양서 §1·§4](../docs/current/관리자콘솔_사양서.md#4-프리셋과-기준선) |

## 알려진 제약

- 관리자 인증이 없습니다. 외부 공개 없이 신뢰된 내부 환경에서만 사용합니다.
- 사용자 서버는 설정 변경을 푸시로 받지 않고 다음 생성 요청 직전에 설정 파일 교체를 확인합니다.
  생성 요청이 없는 동안에는 이전 값이 메모리에 남아 있습니다.
- 작업 판정 대기는 프로세스 메모리 이벤트를 사용하므로 서버 재시작 후 이어갈 수 없습니다.
- 업로드 파일의 백업·용량 관리는 별도 운영 정책이 필요합니다.
- 최신성 가드는 승인·유효기간·업무·발동 키워드가 모두 맞을 때 사용자 답변 경로에 적용됩니다.
