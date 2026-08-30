<!-- 상태:current -->

# 6업무 라우터 체크포인트

> 기준: 2026-08-30 · 구현: `crawler/router_source.py`, `crawler/faq_bf_map.py`,
> `crawler/rag.py`

## 모델

| 항목 | 값 |
|---|---|
| 아키텍처 | `Qwen3ForSequenceClassification` |
| 라벨 수 | 6 |
| dtype | float32 |
| 가중치 | `pytorch_model.bin` · 2,383,231,423 bytes |
| 로컬 폴더 | `router_moai_embedding_model/` |
| 배포 저장소 | `us788/moai_yebo_ft` |
| 매니페스트 | `crawler/data/router_manifest.json` |

`config.json`의 `id2label`은 `crawler/faq_bf_map.py`의 `CANONICAL_BF`와 정확히 일치해야
합니다. 불일치하면 조용히 다른 업무를 boost할 수 있으므로 로드를 중단합니다.

## Git 포함 정책

설정·토크나이저 8개 파일은 Git에 포함하고 2.38GB 가중치만 제외합니다.

- `added_tokens.json`
- `chat_template.jinja`
- `config.json`
- `merges.txt`
- `special_tokens_map.json`
- `tokenizer.json`
- `tokenizer_config.json`
- `vocab.json`

가중치는 GitHub 단일 파일 제한을 넘으므로 HuggingFace에서 로컬 폴더로 내려받습니다.

## 현재 상태 확인

리포지토리 루트에서:

```bash
python crawler/router_source.py
```

정상 예:

```text
로컬 상태  : 사용 가능
resolve() -> /.../router_moai_embedding_model
```

2026-08-30 작업 폴더에서는 매니페스트의 9개 파일이 모두 일치하고 로컬 경로로 정상
해석됐습니다.

SHA-256 전수 검사는 2.38GB를 모두 읽으므로 필요할 때만 실행합니다.

```bash
python crawler/router_source.py --verify
```

## 다운로드

```bash
python scripts/download_router_hf.py --dry-run
python scripts/download_router_hf.py
python scripts/download_router_hf.py --verify-sha
```

프라이빗 저장소 접근이 필요하면 read 권한 `HF_TOKEN`을 환경에 설정합니다.

```bash
export HF_TOKEN=hf_...
python scripts/download_router_hf.py
```

다운로드 스크립트는 크기가 맞는 파일을 건너뛰므로 중단 후 다시 실행할 수 있습니다.

essential 저장소에는 업로드 스크립트가 없습니다. 체크포인트를 재학습·배포하는 절차는 이
저장소의 현재 운영 계약에 포함하지 않습니다.

## 경로 해석 순서

`router_source.resolve()`는 다음 순서로 첫 유효 값을 반환합니다.

| 순서 | 조건 | 결과 |
|---:|---|---|
| 1 | `ROUTER_PATH` 환경변수 존재 | 지정값 그대로 |
| 2 | 로컬 9개 파일의 크기가 매니페스트와 일치 | 로컬 절대경로 |
| 3 | `ROUTER_HF_REPO` 또는 매니페스트 `hf_repo` 존재 | HuggingFace repo id |
| 4 | 전부 없음 | `None` |

`ROUTER_PATH`는 검증 없이 우선하므로 다른 체크포인트 A/B에만 사용합니다.

## 라우터가 없을 때

`rag.get_router()`는 모델 로드 실패를 한 번 기록하고 키워드 분류
`classify_query_bf_keyword()`로 폴백합니다. 검색 자체는 계속 동작합니다.

다만 라우터 사용 여부에 따라 업무 boost 대상과 평가 결과가 달라집니다. 지표를 기록할 때
`bf_source=router`인지 fallback인지 함께 남깁니다.

## 사용 위치

### 새 질의 업무 분류

`rag.classify_query_bf()`가 질의를 6업무 중 하나로 예측하고 검색 soft boost에 사용합니다.

### FAQ 문서 태깅

```bash
cd crawler
python faq_bf_map.py --router ../router_moai_embedding_model
```

FAQ 질문 문장만 모델에 넣고 결과를 `data/bf_map.jsonl`에 저장합니다.

## 매니페스트 변경

체크포인트 파일을 바꾸면 `crawler/data/router_manifest.json`의 크기와 SHA-256을 반드시 함께
갱신해야 합니다. 매니페스트가 옛 파일을 가리키면 새 로컬 파일을 거부하고 원격의 다른 모델로
폴백할 수 있습니다.

## 제약과 보안

### pickle 포맷

`pytorch_model.bin`은 pickle 기반 로드 경로를 사용할 수 있으므로 신뢰한 출처의 파일만
사용합니다. safetensors로 전환하려면 450문항 분류 회귀와 매니페스트 갱신이 필요합니다.

### MSP 과신

held-out 질문셋에서 MSP 최솟값 0.9991, 중앙값 1.0 수준의 과신이 확인됐습니다. MSP를
소관 밖/OOS 판정기로 사용하지 않습니다.

### 메모리

BGE-m3 임베딩 모델과 fp32 라우터를 함께 올리면 약 4.8GB를 사용합니다. 메모리 부족은
`exit 139` 또는 페이징 파일 오류로 나타날 수 있습니다. 회귀 검증 없이 dtype을 임의로 바꾸지
않습니다.
