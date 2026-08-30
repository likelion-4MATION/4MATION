<!-- 상태:current -->

# FAQ 업무 분류와 BF 조인

> 기준: 2026-08-30 · 구현: `crawler/faq_bf_map.py`, `crawler/rag.py`

## 목적

통합 FAQ 게시판은 한 문서 안에 여러 업무의 질문이 섞일 수 있습니다. 문서의
`business_function`을 모든 FAQ 청크에 상속하면 검색 soft boost가 잘못 적용됩니다.

따라서 게시판 FAQ는 질문 문장별로 라우터를 적용하고, 결과를 코퍼스와 분리된
`crawler/data/bf_map.jsonl`에 저장합니다.

## 핵심 원칙

1. 개별 청크의 BF를 손으로 수정하지 않습니다.
2. 질문 추출·정규화·대상 필터·임계값 같은 결정론 규칙을 수정합니다.
3. `chunks.jsonl`은 수정하지 않고 별도 맵을 검색 시 조인합니다.
4. 저신뢰 결과는 부모 태그로 롤백하지 않고 `null`로 둡니다.
5. `source: manual` 행을 만들지 않습니다.

## 현재 결과

| 항목 | 값 |
|---|---:|
| 전체 코퍼스 | 181청크 |
| 게시판 FAQ 대상 | 108청크 |
| `bf_map.jsonl` | 108행 |
| 라우터 BF | 105행 |
| 저신뢰 `null` | 3행 |
| source | 전부 `router` |
| MSP 최솟값 | 0.4947 |
| MSP 중앙값 | 1.0 |

현재 파일은 2026-08-14 생성 결과를 보존하고 있으며 `model` 필드는
`../router_moai_embedding_model`입니다.

## 조인 키

```text
질문 추출
  → 공백·표기 정규화
  → sha256(normalized_question)[:16]
  → qhash
```

질문 텍스트가 같으면 FAQ 순서가 바뀌어도 같은 맵을 찾습니다. 질문이 수정되면 hash가 바뀌어
미매핑으로 드러나므로 청크 순번 기반 수동 오버라이드보다 안전합니다.

## 출력 스키마

```json
{
  "qhash": "6c33309e8f50df4c",
  "chunk_id": "...#00",
  "question": "예금보호한도 1억원은 언제부터 적용되었나요?",
  "bf": "예금자보호제도",
  "msp": 1.0,
  "model": "../router_moai_embedding_model",
  "source": "router",
  "labeled_at": "2026-08-14T04:03:51.987483+00:00"
}
```

`bf`는 6업무 중 하나 또는 `null`입니다.

## 생성 절차

`crawler/`에서:

```bash
python faq_bf_map.py --dry-run
python faq_bf_map.py --router ../router_moai_embedding_model
python faq_bf_map.py --router ../router_moai_embedding_model --msp 0.7
```

처리 순서:

1. `is_board()`로 FAQ 게시판 청크 필터
2. 청크에서 질문 문장 추출
3. 정규화 후 `qhash` 생성
4. 라우터로 6업무와 MSP 예측
5. MSP 미달은 `bf=null`
6. 기존 파일에서 같은 `qhash`와 같은 `model`이면 재사용
7. JSONL 저장

`--dry-run`은 라우터를 로드하지 않고 대상 수·질문 추출·hash 충돌만 검사합니다.

## 검색 시 동작

`rag.Searcher`는 시작할 때 BF 맵을 읽습니다. 검색 후보가 게시판 FAQ이면 질문을 다시 추출해
`qhash`로 맵을 조회합니다.

- 매핑 성공: 맵의 BF 사용
- `bf=null`: 업무 boost 없음
- 맵 없음·질문 추출 실패: 업무 boost 없음
- 일반 비게시판 청크: 기존 문서 BF 사용

BF는 soft boost이므로 `null` 청크도 검색 후보에서 제거되지 않습니다.

## 검증 항목

| 항목 | 실패 시 수정할 곳 |
|---|---|
| 라우터 `id2label`이 6업무 정본과 일치 | 체크포인트 또는 라벨 매핑 |
| 질문 문장이 올바르게 추출 | `extract_question()` |
| 추출 실패가 과도하지 않음 | 질문 추출 폴백 |
| 서로 다른 질문의 `qhash` 충돌 없음 | 정규화·hash 규칙 |
| 대상 수가 게시판 청크 수와 일치 | `is_board()` |
| 한 문서 안에서 청크별 BF가 달라질 수 있음 | 정상 동작, 수정하지 않음 |
| `null` 비율이 급증하지 않음 | 모델·임계값·질문 분포 |

## MSP 해석 주의

질의 라우터는 별도 held-out 측정에서 MSP가 거의 1.0으로 포화되는 과신 특성이 확인됐습니다.
따라서 MSP는 OOS 판정에 사용하지 않습니다. FAQ 맵의 0.7 임계는 저신뢰 일부를 비우는 현행
규칙일 뿐, 확률이 실제 정답 확률로 보정됐다는 뜻이 아닙니다.

## 변경 시 체크리스트

- 질문 추출 또는 정규화를 바꿨다면 `--dry-run` 전후 대상·충돌 수 비교
- 라우터를 바꿨다면 108행 전체 재생성 후 BF·null diff 검토
- 개별 JSONL 행 수동 수정 금지
- `chunks.jsonl` 스키마에 BF 조인 결과를 역기입하지 않음
- 검색 평가와 서비스 테스트를 함께 실행
