<!-- 상태:current -->

# RUNBOOK — 현재 저장소 실행 절차

이 문서는 essential 재구성본에 실제로 존재하는 명령만 다룹니다.

> 기준: `main` · 2026-08-30
> 설치가 처음이면 [SETUP](../../SETUP.md)을 먼저 봅니다.

## 0. 공통 준비

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r crawler/requirements.txt
python -m pip install -r admin/requirements.txt
python -m pip install python-dotenv pytest
test -f .env || cp .env.example .env
```

Windows에서는 가상환경 생성에 `python`, 활성화에 `.venv\Scripts\Activate.ps1`을 사용합니다.

## 1. 모델 확인

### 임베딩 모델

인덱스를 만들 때 `dragonkue/BGE-m3-ko`를 HuggingFace 캐시에 자동 다운로드합니다. 미리 받으려면:

```bash
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('dragonkue/BGE-m3-ko')"
```

### 업무 라우터

```bash
python crawler/router_source.py
```

로컬 가중치가 없다면:

```bash
python scripts/download_router_hf.py --dry-run
python scripts/download_router_hf.py
python scripts/download_router_hf.py --verify-sha
```

라우터가 없어도 검색은 키워드 분류로 폴백합니다. 체크포인트 계약은
[router_checkpoint.md](./router_checkpoint.md)를 봅니다.

## 2. 서비스 실행

터미널 1 — 관리자:

```bash
source .venv/bin/activate
cd admin
python -m uvicorn main:app --host 127.0.0.1 --port 8600
```

터미널 2 — 사용자 챗봇:

```bash
source .venv/bin/activate
python -m uvicorn web.main:app --host 127.0.0.1 --port 8501
```

| 서비스 | 주소 |
|---|---|
| 사용자 화면 | <http://127.0.0.1:8501> |
| 사용자 API | <http://127.0.0.1:8501/api/docs> |
| 사용자 상태 | <http://127.0.0.1:8501/api/health> |
| 관리자 | <http://127.0.0.1:8600> |

관리자 런타임 설정은 저장 후 사용자 챗봇의 다음 생성 요청부터 자동 반영됩니다. 사용자 서버는
관리자 설정 파일의 원자적 교체를 감지하며, 청킹처럼 재빌드가 필요한 설정은 예외입니다.

## 3. 데이터와 인덱스

`crawler/` 스크립트는 상대경로를 사용합니다. 아래 명령은 표시대로 `crawler/`에서 실행합니다.

### 전체 수집·빌드

```bash
cd crawler
python tests/test_guards.py
python build_dataset.py --crawl
python pipeline.py --manifest crawl_manifest.csv --use-cache --rebuild
```

첨부 단계는 이전 `data/files/manifest.json`의 성공 파일을 크기와 SHA-256으로 검증해
재사용합니다. 누락·손상·이전 실패 항목만 다시 다운로드하므로 같은 빌드를 반복해도
첨부 파일이 새 이름으로 계속 늘어나지 않아야 합니다.

### 저장 원문으로 재생성

```bash
cd crawler
python build_dataset.py --no-fetch
python pipeline.py --manifest crawl_manifest.csv --use-cache --rebuild
```

### 단계별 실행

```bash
cd crawler
python run_crawl.py --manifest crawl_manifest.csv
python parser.py
python fetch_attachments.py
python link_files.py
python chunk.py
python pipeline.py --manifest crawl_manifest.csv --use-cache --rebuild
```

### 증분 재수집

```bash
cd crawler
python pipeline.py --manifest crawl_manifest.csv
```

문서 `content_hash`가 같은 경우 기존 문서를 유지하고, 바뀐 문서만 다시 임베딩합니다.

### 정합성 확인

리포지토리 루트에서:

```bash
wc -l crawler/data/chunks.jsonl crawler/data/index/chunk_meta.jsonl
python -c "import faiss; x=faiss.read_index('crawler/data/index/faiss.index'); print('ntotal=',x.ntotal,'dim=',x.d)"
```

두 행 수와 FAISS `ntotal`이 같고 차원이 1024여야 합니다. 2026-08-30 전체 재빌드 기준값은
`chunks.jsonl` 181행, `chunk_meta.jsonl` 181행, FAISS `ntotal=181`, `dim=1024`입니다.
로컬 인덱스는 Git 비추적 산출물이므로 코퍼스가 바뀌면 서비스·평가 전에 반드시 다시 빌드합니다.

## 4. 검색과 평가

### 검색 단발 확인

```bash
cd crawler
python -c "import rag; s=rag.Searcher(); print([(x['chunk_id'],x['page_title']) for x in s.search('착오송금 반환 신청 구비서류',k=5,mode='hybrid_bf')])"
```

검색 모드는 `dense`, `sparse`, `hybrid`, `hybrid_bf`입니다. 서비스 기본 경로는
`hybrid_bf`입니다.

### 평가

```bash
cd crawler
python eval.py chunk --gt gt_testset_retrieval_450.jsonl
python eval.py chunk --gt gt_testset_retrieval_450.jsonl --mode hybrid_bf
python eval.py chunk --gt gt_testset_retrieval_450.jsonl --report data/eval_chunk_report.md
python eval.py span --gt gt_testset_retrieval_450.jsonl --limit 50
```

- GT: 450문항
- 직접 앵커 보유: 430문항
- `chunk` 기본 판정: 앵커텍스트 전용
- 앵커가 없는 문항: 실패가 아니라 지표 분모에서 제외
- `gt_chunk_ids`: `--score chunk_id` 또는 `--id-fallback`을 명시한 감사 경로에서만 사용
- 2026-08-30 전체 재빌드 평가: relation-aware Hit@5 `0.714`, Hit@10 `0.788`, MRR@10 `0.493`
- 최신 상세 결과: `data/eval_chunk_report.md`

검색을 생략하고 저장 결과를 평가하려면:

```bash
python eval.py chunk --gt gt_testset_retrieval_450.jsonl --retrieved data/retrieved.jsonl
```

`gold` 서브커맨드는 저장된 검색 결과가 필요합니다.

```bash
python eval.py gold --gt gt_testset_retrieval_450.jsonl --retrieved data/retrieved.jsonl
```

## 5. FAQ BF 맵

```bash
cd crawler
python faq_bf_map.py --dry-run
python faq_bf_map.py --router ../router_moai_embedding_model
```

현재 `data/bf_map.jsonl`은 108행이고 저신뢰 3행이 `null`입니다. 자세한 원칙은
[faq_routing_bf.md](./faq_routing_bf.md)를 봅니다.

## 6. 관리자 작업 직접 실행

### 현재 인덱스 재검증

```bash
cd admin
python runner.py --mode verify --config '{}'
```

### 샌드박스 A/B

```bash
cd admin
python runner.py --mode eval --config '{"CHUNK_SIZE":800,"OVERLAP":100,"MIN_CHUNK":60,"TABLE_KEEP":true,"TABLE_GAP_MAX":12}'
```

### 서비스 인덱스 재빌드

```bash
cd admin
python runner.py --mode rebuild --config '{"CHUNK_SIZE":800,"OVERLAP":100}'
```

### 첨부 재수집

```bash
cd admin
python runner.py --mode files --config '{}'
```

관리자 작업은 가능한 한 UI에서 실행하는 것을 권합니다. 작업 상태, 백업, 판정 게이트와 복원
결과를 함께 볼 수 있기 때문입니다.

## 7. 테스트

테스트 명령과 기대값은 이 절이 정본입니다. README·SETUP·각 가이드는 이 절을 링크합니다.

리포지토리 루트에서:

```bash
python -m pytest tests -q
(cd crawler && python tests/test_guards.py)
node --check web/static/app.js
node --check admin/static/app.js
python chatbot/verify_qform_e2e.py
python chatbot/verify_qform_integration.py
python chatbot/verify_qform_search_attachments.py
python chatbot/verify_qform_multiturn.py
```

`crawler/tests/test_guards.py`는 pytest 테스트 함수가 없는 스크립트형 수집 가드 검사입니다.
pytest 묶음에 넣어도 수집되지 않으므로 위처럼 `crawler/`에서 따로 실행합니다(네트워크 없음).

### pytest 묶음

2026-10-12 실측 **65 passed**:

| 파일 | 테스트 | 범위 |
|---|---:|---|
| `tests/test_oos.py` | 13 | OOS 정책·안내처 게시 검증·오류 신고 마스킹 |
| `tests/test_qform_boost.py` | 12 | Q-Form 검색 확장·메타데이터 가산·원문/검색문 분리 |
| `tests/test_answer_gate.py` | 10 | 답변 검증 게이트 경고·재생성·차단과 관리자 런타임 주입 |
| `tests/test_admin_qform.py` | 9 | 관리자 재검증·재청킹의 Q-Form 경로 연결 |
| `tests/test_web_api.py` | 8 | 사용자 웹 API·보안 헤더·첨부 경로 |
| `tests/test_model_selection.py` | 6 | HCX/DeepSeek/Upstage 전환·모델명 동기화 |
| `tests/test_freshness_guards.py` | 4 | 최신성 가드 답변 배선 |
| `tests/test_context_k.py` | 3 | 검색 문맥 수 기본 5청크·재정의 |

`test_oos.py`·`test_qform_boost.py`를 실행하면 Git이 추적하는 `admin/data/oos.sqlite3*`가
변경으로 보일 수 있습니다. 데이터 변경이 아니라 SQLite WAL 체크포인트입니다.
[§9 알려진 제약](#9-알려진-제약)을 봅니다.

### 검증 스크립트

2026-08-30 통합 검증 기준(외부 LLM 0콜):

- 사용자·관리자 UI JavaScript 문법: 통과
- Q-Form E2E: 104조합 통과
- Q-Form 통합: 전 시나리오 통과
- Q-Form 실검색 첨부 반환: 실제 Searcher → chain → 첨부 실파일 통과
- Q-Form 검색 조건: `field: value` 확장·원문 생성 분리·기본 ON 통과
- Q-Form 멀티턴: 24/24 통과

## 8. OOS 운영 확인

관리자와 사용자 서버를 실행한 뒤:

```bash
curl -fsS http://127.0.0.1:8600/api/oos/schema
curl -fsS http://127.0.0.1:8600/api/oos/referrals
curl -fsS http://127.0.0.1:8600/api/oos/reports
```

OOS 안내처는 게시·활성·링크 정상 상태인 행만 사용자에게 노출됩니다. 초기 상태에 공식 연락처가
없으면 “게시된 정보 없음”으로 안내하는 것이 정상입니다.

운영 절차는 [OOS_구현_운영가이드.md](./OOS_구현_운영가이드.md)를 봅니다.

## 9. 알려진 제약

- BGE-m3와 fp32 라우터를 함께 로드하면 메모리를 약 4.8GB 사용합니다. 긴 청크와 Q-Form
  단독 라우터 추론의 `exit 139`를 막기 위해 PyTorch CPU 스레드는 기본 1개입니다. 메모리
  여유가 충분한 서버에서만 `RAG_TORCH_THREADS=2`처럼 명시적으로 올립니다.
- 라우터 MSP는 체계적으로 과신되어 OOS 판정 신호로 쓰지 않습니다.
- 보호한도 원문 본문은 `1억원`이지만 같은 페이지의 보험사고 각주 한 문장에는 공식 사이트가
  아직 `5천만원`을 노출합니다. 크롤러에서 임의 교정하지 않고 원문 그대로 보존합니다.
- 관리자 최신성 가드는 승인·기간·업무·키워드가 일치하면 답변 생성 프롬프트와 수치 검증에 함께 적용됩니다.
- `crawler/data/index/`는 Git 비추적이므로 새 환경에서 다시 생성해야 합니다.
- `admin/data/`의 `admin_config.json`·`attachments.json`·`oos.sqlite3`(`-wal`·`-shm` 포함)는
  2026-09-01부터 팀 공유 초기값으로 Git에 추적됩니다. `.gitignore`의 `admin/data/*` 규칙보다
  추적이 우선합니다. 업로드·백업·잡 기록은 계속 Git 밖에 둡니다.
- OOS DB는 WAL 모드라 관리자·사용자 서버나 테스트가 DB를 열기만 해도 `-wal` 내용이 본 파일로
  합쳐져 `git status`에 변경으로 보입니다. 공유할 운영 데이터 변경이 아니라면
  `git restore admin/data/`로 되돌리고 커밋하지 않습니다.
- essential 재구성 전에 존재하던 실험·튜닝·평가 보조 스크립트는 현재 RUNBOOK의 실행 계약이
  아닙니다.
