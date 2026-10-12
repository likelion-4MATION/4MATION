# 4MATION

예금보험공사(KDIC) 공개 웹사이트의 정보를 수집·정리하고, 6개 업무 범위에서 답하는
RAG 챗봇과 운영용 관리자 콘솔을 제공하는 PoC입니다.

> 기준: `main` · essential 저장소 재구성본 · 2026-08-30 현행화

## 제공 기능

| 영역 | 현재 구현 |
|---|---|
| 데이터 파이프라인 | 화이트리스트 38개 문서 수집, 본문 파싱, 첨부 연결, 청킹, FAISS·BM25 인덱스 생성 |
| 검색 | `dragonkue/BGE-m3-ko` 1024차원 임베딩 + BM25 + RRF + 6업무/Q-Form 메타 soft boost |
| 챗봇 | HCX/DeepSeek/Upstage 답변 생성, 출처 표시, 동적 답변 검증 게이트, 절 단위 처리, Q-Form 되묻기·슬롯 기억·검색 조건 반영 |
| OOS | 오류 신고, 검증된 타기관 안내, 일상 대화, 원거리 소관 밖, 유선 상담 안내 |
| 사용자 웹 | FastAPI API + 빌드 과정 없는 HTML/CSS/JavaScript UI |
| 관리자 | 검색·생성·Q-Form 설정, 재빌드 작업, 첨부 관리, OOS 안내처와 오류 신고함 |

## 현재 저장소 구조

```text
4MATIONESS/
├── README.md                 프로젝트 개요와 문서 지도
├── SETUP.md                  새 환경 설치와 첫 실행
├── .env.example              LLM·라우터 환경변수 예시
├── crawler/                  수집·파싱·청킹·검색·평가
│   ├── README.md
│   ├── data/                 추적 데이터 + 로컬 재생성 산출물
│   └── tests/test_guards.py
├── chatbot/                  답변 생성·Q-Form·OOS 오케스트레이션
├── web/                      사용자 FastAPI 서버와 정적 UI
├── admin/                    관리자 FastAPI 서버와 정적 UI
├── tests/                    OOS·웹 API 회귀 테스트
├── scripts/                  라우터 체크포인트 다운로드
├── router_moai_embedding_model/
│   └── ...                   설정·토크나이저는 Git, 2.38GB 가중치는 로컬 전용
└── docs/current/             현행 설계·운영 문서
```

과거 저장소에 있던 `records/`, `plans/`, `superseded/`, `archive/`, `exp/`, `logs/`는
essential 재구성본에 포함하지 않습니다. 현재 문서는 이 저장소에 실제로 남은 코드와 데이터만
정본으로 취급합니다.

## 빠른 실행

처음 설치한다면 [SETUP.md](./SETUP.md)를 먼저 봅니다. 의존성·`.env`·인덱스가 준비돼 있다면
리포지토리 루트에서 다음 두 프로세스를 실행합니다.

```bash
# 터미널 1 — 관리자
source .venv/bin/activate
cd admin
python -m uvicorn main:app --host 127.0.0.1 --port 8600
```

```bash
# 터미널 2 — 사용자 챗봇(리포지토리 루트)
source .venv/bin/activate
python -m uvicorn web.main:app --host 127.0.0.1 --port 8501
```

- 사용자 화면: <http://127.0.0.1:8501>
- 사용자 API 문서: <http://127.0.0.1:8501/api/docs>
- 관리자 화면: <http://127.0.0.1:8600>

실행·재빌드·평가 명령은 [RUNBOOK](./docs/current/RUNBOOK.md)을 정본으로 사용합니다.

## 데이터와 모델 기준선

Git에 포함된 현재 데이터는 다음과 같습니다.

| 자산 | 현재 값 |
|---|---:|
| 수집 매니페스트 | 38개 문서 |
| `crawler/data/chunks.jsonl` | 181청크 · 38문서 · 15필드 |
| 자연어 질문셋 | 450문항 |
| 검색 GT | 450문항 · 앵커 보유 430문항 |
| FAQ BF 맵 | 108행 · 저신뢰 `null` 3행 |
| 임베딩 | `dragonkue/BGE-m3-ko` · 1024차원 |
| 라우터 | Qwen3 계열 6분류 · fp32 2.38GB |

`crawler/data/index/`, `raw/`, `meta/`, `parsed/`, `files/`는 로컬 재생성 산출물이라 Git에
포함되지 않습니다. 로컬 인덱스의 청크 수는 반드시 `chunks.jsonl`과 맞아야 합니다.

```bash
wc -l crawler/data/chunks.jsonl crawler/data/index/chunk_meta.jsonl
```

수가 다르면 서로 다른 빌드 산출물이 섞인 상태입니다. [RUNBOOK의 인덱스 재빌드 절차](./docs/current/RUNBOOK.md#3-데이터와-인덱스)를 따릅니다.

## 검증

```bash
python -m pytest tests -q
```

2026-10-12 기준 65개가 통과합니다. 수집 가드·UI 문법·Q-Form 검증 스크립트를 포함한 전체 명령과
파일별 기대값은 [RUNBOOK §7](./docs/current/RUNBOOK.md#7-테스트)을 정본으로 사용합니다.

## 문서 지도

| 알고 싶은 내용 | 문서 |
|---|---|
| 새 환경 설치 | [SETUP.md](./SETUP.md) |
| 실행·재빌드·평가·테스트 | [docs/current/RUNBOOK.md](./docs/current/RUNBOOK.md) |
| 최근 개선 작업 1~5 구현·검증 현황 | [개선작업_구현검증_요약.md](./docs/current/개선작업_구현검증_요약.md) |
| 크롤러 입력·출력 | [crawler/README.md](./crawler/README.md) |
| 사용자 웹 API | [web/README.md](./web/README.md) |
| 관리자 콘솔 | [admin/README.md](./admin/README.md) |
| Q-Form 설계 | [QFORM_ARCH_설계스펙.md](./docs/current/QFORM_ARCH_설계스펙.md) |
| FAQ 업무 태깅 | [faq_routing_bf.md](./docs/current/faq_routing_bf.md) |
| 라우터 체크포인트 | [router_checkpoint.md](./docs/current/router_checkpoint.md) |
| OOS 운영 | [OOS_구현_운영가이드.md](./docs/current/OOS_구현_운영가이드.md) |
| 관리자 상세 사양 | [관리자콘솔_사양서.md](./docs/current/관리자콘솔_사양서.md) |

## 기술 스택

- Python 3.11+
- FastAPI, Uvicorn, SQLite
- requests, BeautifulSoup, lxml
- sentence-transformers, PyTorch, Transformers
- FAISS, BM25(kiwipiepy), RRF
- 정적 HTML/CSS/JavaScript

## 프로젝트 정보

- LikeLion AI/NLP 5기 · 클라비 기업 연계 프로젝트
- 기간: 2026-07-10 ~ 2026-09-02
- 성격: 기술 타당성 검증 PoC
