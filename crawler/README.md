# KDIC 데이터·검색 파이프라인

`crawler/`는 화이트리스트 수집, 본문 파싱, 첨부 연결, 청킹, 임베딩·검색 인덱스 생성과
검색 평가를 담당합니다.

> 기준: 2026-08-30 · 모든 스크립트는 `crawler/`를 현재 폴더로 두고 실행

## 현재 기준선

| 항목 | 값 |
|---|---:|
| 매니페스트 | 38개 문서 |
| 저장된 수집 결과 | 38개 성공 · robots 차단 0 |
| 추적 코퍼스 | 181청크 · 38문서 · 15필드 (`qform_meta` 포함) |
| 자연어 질문셋 | 450문항 |
| 검색 GT | 450문항 · 직접 앵커 430문항 |
| FAQ BF 맵 | 108행 · `null` 3행 |
| 임베딩 | `dragonkue/BGE-m3-ko` · 1024차원 |
| 검색 | FAISS IndexFlatIP + BM25(kiwipiepy) + RRF + BF/Q-Form metadata soft boost |

## 빠른 시작

리포지토리 루트에서 의존성을 설치한 뒤:

```bash
cd crawler
python tests/test_guards.py
python build_dataset.py --crawl
python pipeline.py --manifest crawl_manifest.csv --use-cache --rebuild
```

첫 명령은 네트워크 없이 수집 가드를 검사합니다. `build_dataset.py --crawl`은 원문 수집부터
청킹까지 수행하고, `pipeline.py`가 임베딩과 검색 인덱스를 만듭니다.

## 처리 흐름

```text
crawl_manifest.csv
  → run_crawl.py
  → data/raw/*.html + data/meta/*.json + data/crawl_report.json
  → parser.py
  → data/parsed/*.json
  → fetch_attachments.py
  → data/files/**
  → link_files.py
  → parsed 문서에 local_path·sha256 연결
  → chunk.py
  → data/chunks.jsonl + data/doc_attachments.json
  → pipeline.py / rag.Store
  → data/index/{faiss.index,emb.npy,bm25.pkl,chunk_meta.jsonl,docs.json}
```

`build_dataset.py`가 수집부터 청킹까지를 묶고, `pipeline.py`가 문서 단위 upsert와 인덱스
저장을 담당합니다.

## 단계별 명령

### 매니페스트 재생성

평상시에는 커밋된 `crawl_manifest.csv`를 사용합니다. 원천 CSV/XLSX가 바뀐 경우에만:

```bash
python build_manifest.py kdic_필수페이지_URL매핑.csv \
  분석필요태깅_포함여부분석.xlsx -o crawl_manifest.csv
```

### 수집

```bash
python run_crawl.py --manifest crawl_manifest.csv
python run_crawl.py --manifest crawl_manifest.csv --limit 3
```

수집 대상은 매니페스트의 KDIC 호스트로 제한합니다. 요청 간격은 기본 1.5초와 최대 0.7초
지터이며, 오류 페이지·대기열·허용 호스트·정책 경로 가드를 적용합니다.

### 파싱·첨부·청킹

```bash
python parser.py
python fetch_attachments.py
python link_files.py
python chunk.py
```

한 번에 실행하려면:

```bash
python build_dataset.py             # 저장된 raw 사용
python build_dataset.py --crawl     # 라이브 수집부터
python build_dataset.py --no-fetch  # 첨부 실다운로드 생략
```

첨부 단계는 이전 `data/files/manifest.json`의 성공 레코드를 파일 크기와 SHA-256으로
검증해 재사용합니다. 파일이 없거나 손상된 항목과 이전 실패 항목만 다시 다운로드합니다.

### 인덱스

```bash
python pipeline.py --manifest crawl_manifest.csv --use-cache --rebuild
```

- `--use-cache`: `data/raw/`만 사용하고 네트워크에 접속하지 않음
- `--rebuild`: 기존 인덱스를 비우고 전량 재생성
- 옵션 없음: 라이브 재수집 후 `content_hash`가 바뀐 문서만 upsert

현재 임베딩 모델은 `dragonkue/BGE-m3-ko`이며 인덱스 차원은 1024입니다.

## 인덱스 정합성

`data/index/`는 Git에 포함되지 않아 다른 시점의 로컬 산출물이 남을 수 있습니다. 다음 두 수는
같아야 합니다.

```bash
wc -l data/chunks.jsonl data/index/chunk_meta.jsonl
python -c "import faiss; x=faiss.read_index('data/index/faiss.index'); print(x.ntotal, x.d)"
```

불일치하면 캐시 원문으로 전량 재빌드합니다.

```bash
python pipeline.py --manifest crawl_manifest.csv --use-cache --rebuild
```

## FAQ BF 태깅

게시판 FAQ는 한 문서에 여러 업무가 섞일 수 있어 문서의 업무 태그를 그대로 상속하지 않습니다.
질문 정규화 hash를 키로 `data/bf_map.jsonl`을 별도 생성하고 검색 시 조인합니다.

```bash
python faq_bf_map.py --dry-run
python faq_bf_map.py --router ../router_moai_embedding_model
python faq_bf_map.py --router ../router_moai_embedding_model --msp 0.7
```

현재 커밋된 맵은 108행이며 저신뢰 3행은 `bf: null`입니다. 개별 행을 손으로 고치지 말고
추출·정규화·임계 규칙을 수정한 뒤 전체를 다시 생성합니다.

## 평가

현재 GT는 `gt_testset_retrieval_450.jsonl`입니다. 450문항 중 `gt_anchor_span`이 있는
430문항을 앵커텍스트 지표의 분모로 사용합니다.

```bash
python eval.py chunk --gt gt_testset_retrieval_450.jsonl
python eval.py chunk --gt gt_testset_retrieval_450.jsonl --mode hybrid_bf
python eval.py span --gt gt_testset_retrieval_450.jsonl --limit 50
```

`chunk`의 기본 판정은 앵커텍스트 전용이며 `gt_chunk_ids`는 감사용 참고값입니다. 검색 없이 이미
저장된 결과를 채점하려면 `--retrieved <파일.jsonl>`을 사용합니다.

평가는 BGE-m3와 라우터를 함께 로드할 수 있으므로 메모리가 충분한 환경에서 실행합니다.

## 추적 파일과 로컬 산출물

### Git에 포함

- `crawl_manifest.csv`
- `kdic_필수페이지_URL매핑.csv`
- `분석필요태깅_포함여부분석.xlsx`
- `data/chunks.jsonl`
- `data/crawl_report.json`
- `data/doc_attachments.json`
- `data/bf_map.jsonl`
- `data/testset_natural_450.jsonl`
- `gt_testset_retrieval_450.jsonl`
- `data/router_manifest.json`
- Q-Form CSV 4종

### Git에서 제외

- `data/raw/`, `data/meta/`, `data/parsed/`
- `data/files/`
- `data/index/`
- 라우터 `pytorch_model.bin`

## 주의사항

- `crawler/` 스크립트는 `data/...` 상대경로를 사용하므로 반드시 이 폴더에서 실행합니다.
- 첨부 파일은 `pipeline.py`만으로 다시 받지 않습니다. `build_dataset.py` 또는
  `fetch_attachments.py` + `link_files.py`를 사용합니다.
- 보호한도 페이지에 `5천만` 구값이 있으면 캐시 없이 재수집합니다.
- `OVERLAP=0`은 현 구현에서 겹침 없음으로 안전하게 해석되지 않으므로 관리자 러너가 1로
  보정합니다.
- 원문·청크의 개별 값을 손으로 수정하지 않습니다. 결정론 규칙과 파이프라인을 고칩니다.
