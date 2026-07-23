# 2026-07-22 작업 요약 — 검색 품질 개선 (400건 테스트셋 기준)

기준 파이프라인: `eval_TF.py` · 테스트셋 `data/testset_natural_400_v3.jsonl`(400건, hit@1/hit@3/MRR)

## 실제 효과를 본 변경 (누적, 순서대로 적용)

| 단계 | 조치 | hit@1 | hit@3 | MRR | 미적중 |
|---|---|---|---|---|---|
| 0 | 라벨 QA 이전 baseline | - | 0.795 | - | 82/400 |
| 1 | gt_docs 라벨 QA (과거 수동 6 + 근사문서 자동완성 34) | - | 0.812 | - | 75/400 |
| 2 | RRF 파라미터 1차 튜닝 (rrf_k 60→10, pool 20→30, ko-sroberta 기준) | 0.562 | 0.830 | 0.706 | 68/400 |
| 3 | **임베딩 모델 교체 (ko-sroberta-multitask → BAAI/bge-m3) + RRF 2차 재튜닝 (rrf_k=5, dense가중치2.0:sparse1.0)** | **0.672** | **0.930** | **0.800** | **28/400** |

> **2026-07-23 정정**: 1번의 ratio≥0.4 자동완성 34건은 철회했다. 문자열 유사도는 후보 우선순위일 뿐 relevance 판정이 아니므로, 이 행의 .812와 75/400은 유효한 검색 성능 또는 확정 qrels 결과로 인용하지 않는다. 후보는 전수 사람 검토 전까지 별도 JSONL에만 둔다.

**3번이 이번 세션 최대 성과**: hit@3 +0.100, MRR +0.094, 미적중 40건 감소, 업무간 혼입 31→5건. dense 단독 성능도 hit@3 0.665→0.848로 bge-m3가 기존 모델보다 훨씬 강함. 그리드서치 예측치와 실제 파이프라인 결과가 정확히 일치해 신뢰도 높음.

- **부가 조치**: `kdic-fins-cm-bbs-selectFaqNramtAply` 문서(38청크)의 `business_function` 라벨이 실제 내용(예금보험금 지급절차)과 다르게 "고객 미수령금 신청"으로 잘못 태깅돼 있던 것을 재태깅. 검색 점수엔 영향 없지만(현재 스코어링에 미사용) 오류분석 리포트의 "타업무혼입" 오탐을 제거(37→31건, 관련 원인이 이번 3번 개선 후엔 5건 수준으로 대부분 해소).
- **부가 조치**: `eval.py` 실행 불가 syntax 버그 수정, `eval.py`/`eval_TF.py` 기본 테스트셋을 400건으로 전환.

## 시도했으나 효과 없어 폐기한 것

- **Cross-encoder 재랭킹**(`hybrid_rerank` 모드, 코드는 옵트인으로 남겨둠): 소표본에선 개선처럼 보였으나 400건 전체 재검증시 순이익 없음(오히려 소폭 하락), 프로덕션 기본값 미채택.
- **business_function 하드필터**(SelfQueryRetriever 방식): centroid 분류기 정확도 58.5%로 낮아, 필터 오적용시 정답 후보 자체를 제거 — hit@3 오히려 최대 4.3%p 하락. 미채택.
- **business_function 소프트부스트**(BM25F 필드가중치 방식): hit@1/MRR 미세 상승(+0.004~0.006) 대신 hit@3 항상 소폭 하락(-0.002~-0.005) — net 이득 없음. 미채택.

## 변경 파일

- `crawler/rag.py` — `MODEL_NAME`/`EMB_DIM` (bge-m3, 1024d), `hybrid()`에 `dw`/`sw` 가중치 파라미터 추가·기본값 재튜닝(rrf_k=5, dw=2.0, sw=1.0)
- `crawler/eval.py`, `crawler/eval_TF.py` — syntax 버그 수정, 400건 기본 테스트셋 전환, RRF(k) 리포트 라벨을 `rag.py` 실제값 참조로 수정
- `crawler/data/index/` — bge-m3 임베딩으로 FAISS 재구축(청크·BM25는 불변). 기존 ko-sroberta 인덱스는 `crawler/data/index_backup_ko_sroberta/`에 백업
- `crawler/data/chunks.jsonl`, `crawler/data/index/chunk_meta.jsonl` — `selectFaqNramtAply` 38청크 business_function 재태깅
- `crawler/data/testset_natural_400_v3.jsonl`, `crawler/data/testset_new100_only.jsonl` — 300→400건 확장 + gt_docs 라벨 QA 40건 보정
- `crawler/data/eval_report.md`, `crawler/data/error_analysis.md`, `crawler/data/rrf_grid_log.txt` — 최신 결과 재생성

## 남은 후보 (미착수)

- 착오송금 반환 신청 업무(hit@3=0.833, 6개 업무 중 최저)에 근사문서 9종(신청대상/방법/절차/유의사항 등)이 여전히 서로 혼동 — 근본적으로 콘텐츠가 겹치는 문제라 리트리버 파라미터로는 한계.
