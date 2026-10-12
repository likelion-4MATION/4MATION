# 개발 환경 세팅

새 클론에서 의존성 설치, 모델 준비, 데이터·인덱스 생성, 사용자 챗봇과 관리자 콘솔 실행까지의
현행 절차입니다. 모든 명령은 별도 표시가 없으면 리포지토리 루트에서 실행합니다.

> 기준: `dev` · Python 3.11+ · 2026-10-12

## 1. 준비물

| 항목 | 요구사항 |
|---|---|
| Python | 3.11 이상 |
| 디스크 | 최소 8GB 여유 |
| LLM | HCX, DeepSeek 또는 Upstage Solar API 설정 |
| 라우터 | 선택. 로컬 체크포인트는 약 2.38GB |

임베딩 모델 `dragonkue/BGE-m3-ko`는 약 2.2GB이며 최초 인덱스 생성 때 HuggingFace 캐시에
다운로드됩니다. 라우터와 임베딩을 한 프로세스에 fp32로 올리면 메모리를 약 4.8GB 사용합니다.

## 2. 클론과 가상환경

```bash
git clone git@github.com:likelion-4MATION/4MATION.git
cd 4MATION
git switch dev     # 최신 통합본. main은 2026-08-31 병합 시점

python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
git clone git@github.com:likelion-4MATION/4MATION.git
cd 4MATION
git switch dev

python -m venv .venv
.venv\Scripts\Activate.ps1
```

## 3. 의존성 설치

```bash
python -m pip install --upgrade pip
python -m pip install -r crawler/requirements.txt
python -m pip install -r admin/requirements.txt
python -m pip install python-dotenv pytest
```

확인:

```bash
python -c "import fastapi, faiss, torch, transformers; print('의존성 OK')"
```

사용자 웹은 검색 스택과 FastAPI를 함께 사용하므로 `crawler/requirements.txt`와
`admin/requirements.txt`를 같은 가상환경에 설치해야 합니다.

## 4. 환경변수

```bash
test -f .env || cp .env.example .env
```

`.env`에서 사용할 공급자의 값을 채웁니다.

```ini
LLM_PROVIDER=hcx

DEEPSEEK_API_KEY=
DEEPSEEK_API_URL=https://api.deepseek.com/chat/completions
DEEPSEEK_MODEL=deepseek-v4-flash

UPSTAGE_API_KEY=
UPSTAGE_API_URL=https://api.upstage.ai/v1/chat/completions
UPSTAGE_MODEL=solar-pro3

CLOVA_API_KEY=
CLOVA_API_URL=
CLOVA_MODEL=HCX-003
```

- `LLM_PROVIDER`: CLI 단독 실행의 초기값(`hcx`, `deepseek`, `upstage`). 웹 서비스는 관리자 콘솔의
  `챗봇 모델` 설정을 우선 적용합니다.
- Upstage 기본값은 [공식 Chat Completions 예시](https://console.upstage.ai/api-keys?api=chat)의
  `https://api.upstage.ai/v1`·`solar-pro3` 형식에 맞췄습니다.
- `.env`는 Git에 올리지 않습니다.
- 라우터를 다른 경로에서 시험할 때만 `ROUTER_PATH`를 설정합니다.

## 5. 라우터 체크포인트

라우터가 없어도 키워드 분류로 폴백하므로 서비스는 실행됩니다. 다만 업무 분류 성능이 달라질 수
있으므로 데모·평가 전에는 로컬 상태를 확인합니다.

```bash
python crawler/router_source.py
```

`로컬 상태: 사용 가능`이면 추가 작업이 없습니다. 가중치가 없다면 접근 권한이 있는 환경에서:

```bash
python scripts/download_router_hf.py --dry-run
python scripts/download_router_hf.py
python scripts/download_router_hf.py --verify-sha
```

프라이빗 저장소 접근이 필요하면 `HF_TOKEN`을 `.env` 또는 셸 환경에 설정합니다. 상세 규약은
[라우터 체크포인트 문서](./docs/current/router_checkpoint.md)를 봅니다.

`chatbot/chain.py`는 HuggingFace 오프라인 모드를 기본으로 켭니다. 따라서 서비스를 띄우기 전에
라우터와 임베딩 모델을 받아 두어야 합니다. 임베딩 모델은 다음 명령으로 미리 받을 수 있습니다.

```bash
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('dragonkue/BGE-m3-ko')"
```

## 6. 데이터와 인덱스

Git에는 매니페스트, 181청크 코퍼스, 450문항 질문셋과 GT, FAQ BF 맵이 포함됩니다.
`raw/`, `meta/`, `parsed/`, `files/`, `index/`는 로컬 재생성 대상입니다.

### 새 클론에서 전체 생성

```bash
(cd crawler && python tests/test_guards.py)
(cd crawler && python build_dataset.py --crawl)
(cd crawler && python pipeline.py --manifest crawl_manifest.csv --use-cache --rebuild)
```

수집은 요청당 1.5초와 지터를 적용하므로 수 분 걸립니다. `build_dataset.py --crawl`은
수집 → 파싱 → 첨부 다운로드 → 첨부 연결 → 청킹을 수행하고, 다음 명령이 검색 인덱스를 만듭니다.

저장된 원문으로 다시 만들기, 단계별 실행, 증분 재수집은
[RUNBOOK §3](./docs/current/RUNBOOK.md#3-데이터와-인덱스)을 봅니다.

### 정합성 확인

```bash
wc -l crawler/data/chunks.jsonl crawler/data/index/chunk_meta.jsonl
python -c "import faiss; x=faiss.read_index('crawler/data/index/faiss.index'); print(x.ntotal, x.d)"
```

두 청크 수가 같고 FAISS 차원이 1024여야 합니다. 수가 다르면 다른 시점의 산출물이 섞인 것이므로
`pipeline.py ... --use-cache --rebuild`를 다시 실행합니다.

### 보호한도 스테일 확인

```bash
grep -c "5천만" crawler/data/raw/kdic-www-sp-dpstrprot-ProtSystProtLmts-selectScrn.html || true
```

보호한도 페이지에서 1건 이상 나오면 캐시 없이 다시 수집합니다.

```bash
(cd crawler && python pipeline.py --manifest crawl_manifest.csv --rebuild)
```

## 7. 서비스 실행

관리자(포트 8600)와 사용자 챗봇(포트 8501)을 터미널 두 개에서 각각 실행합니다. 명령과 접속
주소는 [RUNBOOK §2](./docs/current/RUNBOOK.md#2-서비스-실행)를 따릅니다.

관리자와 사용자 챗봇은 별도 프로세스지만 재시작은 필요 없습니다. 사용자 서버(`web/service.py`)가
생성 요청 직전에 `admin/data/admin_config.json` 교체를 감지해 설정을 다시 적용합니다. 청킹처럼
재빌드가 필요한 설정만 예외입니다.

## 8. 검증

설치가 끝났는지는 네트워크 없이 도는 회귀 테스트로 확인합니다.

```bash
python -m pytest tests -q
```

2026-10-12 기준 65개가 통과합니다. 전체 검증 명령과 기대값은
[RUNBOOK §7](./docs/current/RUNBOOK.md#7-테스트)을 봅니다.

검색 평가는 인덱스와 모델을 로드하므로 메모리가 충분한 환경에서 실행합니다.

```bash
(cd crawler && python eval.py chunk --gt gt_testset_retrieval_450.jsonl)
```

평가셋 450문항 중 앵커가 있는 430문항이 앵커 지표의 분모입니다.

## 문제 해결

### `FileNotFoundError: data/index/faiss.index`

인덱스를 다시 만듭니다.

```bash
(cd crawler && python pipeline.py --manifest crawl_manifest.csv --use-cache --rebuild)
```

### 라우터 로드 실패

키워드 폴백이 동작하므로 오류 자체는 치명적이지 않습니다. 라우터가 필요한 실행이면
`python crawler/router_source.py`로 누락 파일과 크기를 확인합니다.

### `exit 139` 또는 메모리 부족

BGE-m3와 fp32 라우터를 함께 올리는 경로는 메모리를 약 4.8GB 사용합니다. 현재 코드는 긴 청크와
Q-form 단독 라우터 추론을 안정적으로 처리하도록 PyTorch CPU 스레드를 기본 1개로 제한합니다.
메모리 여유가 충분한 서버에서 속도를 높이려면 아래처럼 스레드 수를 명시해 실행할 수 있습니다.

```bash
(cd crawler && RAG_TORCH_THREADS=2 python pipeline.py --manifest crawl_manifest.csv --use-cache --rebuild)
```

현재 체크포인트는 분류 회귀 검증 없이 임의로 bf16으로 바꾸지 않습니다.

### SSL 인증서 오류

회사 보안 프로그램의 TLS 검사나 로컬 인증서 저장소 문제일 수 있습니다. 인증 검증을 끄지 말고,
운영체제 또는 조직이 제공한 CA를 Python이 사용하는 인증서 번들에 안전하게 추가합니다.

## 다음 문서

- [RUNBOOK](./docs/current/RUNBOOK.md): 일상 실행·재빌드·평가
- [crawler/README.md](./crawler/README.md): 파이프라인 단계별 입출력
- [web/README.md](./web/README.md): 사용자 API
- [admin/README.md](./admin/README.md): 관리자 기능
