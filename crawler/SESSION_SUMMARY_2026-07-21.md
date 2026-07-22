# 2026-07-21 작업 요약 — fins 청크 누락 진단·수정 및 검색 품질 개선

## 1. fins.kdic.or.kr 청크 0건 문제

- **증상**: fins.kdic.or.kr 14개 URL(FAQ 5건 + 안내 9건)이 크롤 리포트엔 `status: ok`로 정상 기록됐지만, 실제 파싱 결과는 전부 `text_len=6`(페이지 타이틀뿐) · `_no_container: true` — 청크 0개. `chunks.jsonl`에 fins 문서 청크가 하나도 없었음.
- **원인**: fins.kdic.or.kr 응답이 본인인증 위젯 스니펫을 `<html>/<body>`째로 중복 포함한 기형 HTML을 반환. HTML5 스펙(WHATWG §13.2.6.4.7)은 이런 중복 body를 기존 body에 병합해 복구하도록 정의하는데, **Windows용 `lxml` 휠은 libxml2 2.11(HTML5 이전 세대)에 고정**돼 있어(PyPI 5.3.0~6.1.1 전 구간 동일 확인) 이 복구를 못 하고 진짜 본문을 통째로 버림. macOS/manylinux 휠은 libxml2 2.14+(HTML5 준수)라 정상 동작 — 동일 코드가 Mac에서는 문제없던 이유.
- **부가 발견**: 같은 버그가 크롤링 시점 FAQ 페이지네이션 감지(`.paging`)도 막아서, FAQ 게시판 5건 중 3건이 2페이지 이상 있는데도 1페이지만 수집돼 있었음(캐시 재파싱만으론 불완전, 재크롤링 필요).
- **수정**: `parser.py`에 `parse_html()` 헬퍼 추가 — lxml 우선 파싱 후 `.contents` 미탐지 시 `html.parser`(표준 라이브러리, OS/휠 버전 무관)로 재시도. `crawler.py`의 관련 3개 지점에 동일 적용. www 24건 전체 재검증 결과 lxml 결과와 100% 바이트 동일(회귀 없음 확인).
- **재크롤링**: fins 14건 라이브 재수집 → 파싱/청킹 정상화, 누락됐던 FAQ 페이지네이션도 전부 병합(+32건 문답). `chunks.jsonl` 93 → 215건(fins 122건 신규).
- **부수 이슈 처리**: 이 PC의 Avast 백신 HTTPS 스캔이 Python `requests`의 TLS 인증서 검증을 막고 있어 `pip-system-certs`로 해결(Windows 시스템 인증서 저장소 사용).

## 2. 검색 품질 평가 및 개선

fins 수정 후 300문항 평가(`eval_TF.py`) 기준.

| | hit@1 | hit@3 | MRR | 미적중 | 비고 |
|---|---|---|---|---|---|
| fins 수정 직후 baseline | 0.560 | 0.743 | 0.673 | 77/300 | |
| **+ 문서당 청크 상한(max_per_doc=1)** | 0.560 | **0.807** | **0.696** | **58/300** | **채택** |

- **문제**: 대형 FAQ 문서(예: 미수령금 FAQ 38청크) 하나가 자기 청크끼리 top-3를 독점 — `혼입 문서 랭킹` 1위가 56회.
- **조치**: `rag.py::Searcher.hybrid()`에 RRF 융합 후 같은 `parent_doc_id`는 결과에 1개까지만 남기는 캡 추가(`max_per_doc=1` 기본값). MMR(Carbonell & Goldstein, 1998) 임베딩 기반 재랭킹도 검증했으나 효과가 미미해(hit@3 +0.01, MRR −0.002) 더 단순한 문서당 캡으로 대체 채택.
- **결과**: 전 지표 동시 개선, 대표 6문항 5/6→6/6, 오염체크 0건 유지. 인덱스 재구축 불필요(검색 시점 로직).

## 3. 시도했으나 되돌린 것

- **임베딩에 business_function 추가**(`chunk_embed_text`): 업무간 혼입은 줄었지만(37→31) hit@1(-0.037)·MRR(-0.023)이 악화돼 **되돌림**. 원인: 긴 접두어가 같은 문서 내 청크들을 더 뭉치게 해 자기잠식이 오히려 심해짐.
- **Weighted RRF(dense 가중치 상향)**: 착오송금 반환 신청 업무의 특정 사례(BM25가 정답을 1위→6위로 끌어내림)에서 착안했으나, 전역 가중치 조정은 다른 질문(FAQ 등)에서 BM25 순기여를 깎아 전 지표 악화 → **미적용**.
- **공백 정규화**: 청크 텍스트·메타 필드·평가셋 질문 전수 확인 — 이상 없음(원인 아님, 확인 후 종료).

## 4. 남은 문제 (다음 후보)

- **착오송금 반환 신청**(72문항, 최대 그룹) hit@3=0.708로 6개 업무 중 최저. 신청대상/신청방법/절차/유의사항(송금인·수취인)/구비서류(송금인·수취인) 등 9개 근사문서가 서로 혼동됨 — 전역 가중치 조정으로는 해결 안 됨. 다음 후보: 업무 국한 규칙, 또는 cross-encoder 재랭킹.

## 변경 파일

- `crawler/crawler.py`, `crawler/parser.py` — HTML 파서 폴백
- `crawler/rag.py` — hybrid() 문서당 청크 캡
- `crawler/data/chunks.jsonl`, `crawler/data/crawl_report.json`, `crawler/data/eval_report.md`, `crawler/data/error_analysis.md` — 재생성 산출물
