# 오류 분석 리포트 — hybrid 기준

- 대상: 전체 400건 중 **미적중 28건** · 미적중률 7.0%
- 미적중 = gt_docs 문서가 hybrid top-3 밖. `rank=0` 은 top-10 내에도 정답 문서 없음.
- 태그: **✅정답** / **⚠️타업무혼입**(다른 업무 문서가 올라옴) / **❌동일업무오답**(같은 업무의 다른 문서).

## 1. 업무별 미적중

| 업무 | 문항 | 미적중 | 미적중률 |
|---|---|---|---|
| 착오송금 반환 신청 | 72 | 12 | 16.7% |
| 예금보험금 안내 | 65 | 6 | 9.2% |
| 고객 미수령금 신청 | 67 | 3 | 4.5% |
| 채무조정 안내 | 68 | 3 | 4.4% |
| 은닉재산 신고 | 62 | 2 | 3.2% |
| 예금자보호제도 | 66 | 2 | 3.0% |

## 2. 혼입 문서 랭킹 (미적중 문항 top-3를 잠식한 오답 문서)

| 혼입 문서 | 출현 | 소속 업무 |
|---|---|---|
| `kdic-fins-cm-bbs-selectFaqNramtAply` | 10 | 예금보험금 안내 |
| `kdic-fins-ir-aplygudn-MtrsGvbkSprtProc-selectScrn` | 9 | 착오송금 반환 신청 |
| `kdic-www-sp-kmrs-kmrsItrdAplyTrgt-selectScrn` | 6 | 착오송금 반환 신청 |
| `kdic-fins-lb-lbltinfo-LbltInfoInqItrdMthdGudn-selectScrn` | 5 | 채무조정 안내 |
| `kdic-fins-cm-bbs-selectFaqMsdrGvbkAply` | 4 | 착오송금 반환 신청 |
| `kdic-www-rb-lbltajmt-LbltAjmtSprtLbltAjmtSyst-selectScrn` | 4 | 채무조정 안내 |
| `kdic-www-sp-dpstrprot-ProtSystFaq-selectScrn` | 4 | 예금자보호제도 |
| `kdic-www-sp-kmrs-kmrsItrd-selectScrn` | 3 | 착오송금 반환 신청 |
| `kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn` | 3 | 착오송금 반환 신청 |
| `kdic-fins-ir-msdrpr-MsdrprAttnMttr-selectScrn` | 3 | 착오송금 반환 신청 |
| `kdic-fins-cm-bbs-selectFaqTop10` | 3 | 공통 |
| `kdic-www-sp-sprtfund-SprtFndCncmDclrGudn-selectScrn` | 2 | 은닉재산 신고 |
| `kdic-www-sp-dpstrprot-DpsmIbamtExpln-selectScrn` | 2 | 예금보험금 안내 |
| `kdic-fins-ir-aplygudn-MsdrAddrsePossDcmntGudn-selectScrn` | 2 | 착오송금 반환 신청 |
| `kdic-www-sp-kmrs-kmrsItrdProc-selectScrn` | 2 | 착오송금 반환 신청 |

## 3. 업무 간 혼입 흐름 (미적중 문항의 top-1이 엉뚱한 업무를 가리킨 경우)

| 정답 업무 | → top-1 업무 | 건수 |
|---|---|---|
| 예금보험금 안내 | 채무조정 안내 | 1 |
| 예금보험금 안내 | 예금자보호제도 | 1 |
| 착오송금 반환 신청 | 채무조정 안내 | 1 |
| 고객 미수령금 신청 | 채무조정 안내 | 1 |
| 고객 미수령금 신청 | 공통 | 1 |

## 4. 미적중 문항 상세

### [고객 미수령금 신청 · new] 미수령금이 몇 천 원밖에 안 되는 것 같은데 그것도 신청할 수 있나요?
- 정답 gt_docs: ['kdic-www-sp-dpstrprot-ProtSystNramtInqAplyNramtGudn-selectScrn']
- dense rank: 6 · hybrid rank: 4
- hybrid top-3:
  1. [❌동일업무오답] 고객 미수령금 신청 / 안내  `kdic-fins-ua-aplygudn-NramtItgrAplyItrdMthdGudn-selectScrn`
  2. [⚠️타업무혼입] 예금보험금 안내 / 신청시 구비서류  `kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn`
  3. [⚠️타업무혼입] 예금보험금 안내 / 미수령금통합신청  `kdic-fins-cm-bbs-selectFaqNramtAply`

### [고객 미수령금 신청 · new] 미수령금이 있는지조차 몰랐는데 예보에서 먼저 연락을 주기도 하나요?
- 정답 gt_docs: ['kdic-www-sp-dpstrprot-ProtSystNramtInqAplyNramtGudn-selectScrn', 'kdic-fins-ua-aplygudn-NramtItgrAplyItrdMthdGudn-selectScrn']
- dense rank: 4 · hybrid rank: 5
- hybrid top-3:
  1. [⚠️타업무혼입] 공통 / TOP 10  `kdic-fins-cm-bbs-selectFaqTop10`
  2. [⚠️타업무혼입] 예금보험금 안내 / 미수령금통합신청  `kdic-fins-cm-bbs-selectFaqNramtAply`
  3. [❌동일업무오답] 고객 미수령금 신청 / 상속인 금융거래조회  `kdic-www-sp-dpstrprot-ProtSystHrpeHistInq-selectScrn`

### [고객 미수령금 신청 · new] 옛날에 망한 회사가 여러 곳인데 한 번에 다 조회하고 신청할 수 있나요?
- 정답 gt_docs: ['kdic-fins-ua-aplygudn-NramtItgrAplyItrdMthdGudn-selectScrn', 'kdic-www-sp-dpstrprot-ProtSystNramtInqAplyNramtGudn-selectScrn']
- dense rank: 5 · hybrid rank: 6
- hybrid top-3:
  1. [⚠️타업무혼입] 채무조정 안내 / 채무정보 조회 ＆ 상담신청  `kdic-www-rb-lbltajmt-LbltAjmtSprtLbltInfoInqDscsnAply-selectScrn`
  2. [⚠️타업무혼입] 채무조정 안내 / 파산면책  `kdic-www-rb-lbltajmt-LbltAjmtSprtPsnBr-selectScrn`
  3. [⚠️타업무혼입] 은닉재산 신고 / 신고센터  `kdic-www-sp-sprtfund-SprtFndCncmDclrGudn-selectScrn`

### [예금보험금 안내 · new] 제가 예금한 은행이 다른 은행으로 넘어갔다는데 제 통장은 그대로 쓸 수 있는 건가요?
- 정답 gt_docs: ['kdic-www-sp-dpstrprot-DpsmIbamtExpln-selectScrn']
- dense rank: 7 · hybrid rank: 5
- hybrid top-3:
  1. [❌동일업무오답] 예금보험금 안내 / 미수령금통합신청  `kdic-fins-cm-bbs-selectFaqNramtAply`
  2. [⚠️타업무혼입] 착오송금 반환 신청 / 반환지원절차  `kdic-fins-ir-aplygudn-MtrsGvbkSprtProc-selectScrn`
  3. [⚠️타업무혼입] 예금자보호제도 / 예금자보호제도 FAQ  `kdic-www-sp-dpstrprot-ProtSystFaq-selectScrn`

### [예금보험금 안내 · new] 지금 정상적으로 영업 중인 은행에 오래 안 쓴 통장이 있는데 이것도 예보에서 찾아주나요?
- 정답 gt_docs: ['kdic-www-sp-dpstrprot-DpsmIbamtExpln-selectScrn']
- dense rank: 미적중 · hybrid rank: 7
- hybrid top-3:
  1. [❌동일업무오답] 예금보험금 안내 / 미수령금통합신청  `kdic-fins-cm-bbs-selectFaqNramtAply`
  2. [⚠️타업무혼입] 고객 미수령금 신청 / 상속인 금융거래조회  `kdic-www-sp-dpstrprot-ProtSystHrpeHistInq-selectScrn`
  3. [⚠️타업무혼입] 채무조정 안내 / 채무정보조회  `kdic-fins-cm-bbs-selectFaqLbltInfoInq`

### [예금보험금 안내 · paraphrase] 1종 보험사고랑 2종 차이가 뭐예요?
- 정답 gt_docs: ['kdic-www-sp-dpstrprot-DpsmIbamtExpln-selectScrn', 'kdic-www-sp-dpstrprot-DpsmIbamtAplyProc-selectScrn']
- dense rank: 미적중 · hybrid rank: 4
- hybrid top-3:
  1. [⚠️타업무혼입] 예금자보호제도 / 개요  `kdic-www-sp-dpstrprot-selectProtSystProtSumr`
  2. [⚠️타업무혼입] 예금자보호제도 / 보호한도  `kdic-www-sp-dpstrprot-ProtSystProtLmts-selectScrn`
  3. [⚠️타업무혼입] 예금자보호제도 / 예금자보호제도 FAQ  `kdic-www-sp-dpstrprot-ProtSystFaq-selectScrn`

### [예금보험금 안내 · simple] 인터넷 신청도 미성년자는 안 되나요?
- 정답 gt_docs: ['kdic-www-sp-dpstrprot-DpsmIbamtExpln-selectScrn']
- dense rank: 미적중 · hybrid rank: 9
- hybrid top-3:
  1. [❌동일업무오답] 예금보험금 안내 / 미수령금통합신청  `kdic-fins-cm-bbs-selectFaqNramtAply`
  2. [⚠️타업무혼입] 착오송금 반환 신청 / 착오송금인  `kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn`
  3. [⚠️타업무혼입] 채무조정 안내 / 채무정보조회  `kdic-fins-cm-bbs-selectFaqLbltInfoInq`

### [예금보험금 안내 · yesom] 예금보험금을 창구에서 직접 받으려면 어느 지점으로 가야 하나요?
- 정답 gt_docs: ['kdic-www-sp-dpstrprot-DpsmIbamtAplyProc-selectScrn']
- dense rank: 4 · hybrid rank: 4
- hybrid top-3:
  1. [❌동일업무오답] 예금보험금 안내 / 미수령금통합신청  `kdic-fins-cm-bbs-selectFaqNramtAply`
  2. [❌동일업무오답] 예금보험금 안내 / 예금보험금이란?  `kdic-www-sp-dpstrprot-DpsmIbamtExpln-selectScrn`
  3. [⚠️타업무혼입] 착오송금 반환 신청 / 방문접수안내  `kdic-fins-ir-aplygudn-MtrsVstRcptGudn-selectScrn`

### [예금보험금 안내 · yesom] 은행 망했을 때 보험금은 어떤 방법으로 신청할 수 있어?
- 정답 gt_docs: ['kdic-www-sp-dpstrprot-DpsmIbamtAplyProc-selectScrn']
- dense rank: 3 · hybrid rank: 4
- hybrid top-3:
  1. [⚠️타업무혼입] 채무조정 안내 / 채무조정제도  `kdic-www-rb-lbltajmt-LbltAjmtSprtLbltAjmtSyst-selectScrn`
  2. [❌동일업무오답] 예금보험금 안내 / 미수령금통합신청  `kdic-fins-cm-bbs-selectFaqNramtAply`
  3. [⚠️타업무혼입] 채무조정 안내 / 소개와 방법 안내  `kdic-fins-lb-lbltinfo-LbltInfoInqItrdMthdGudn-selectScrn`

### [예금자보호제도 · new] 예금자보호를 해주는 은행이나 저축은행이 전국에 몇 곳이나 되는지 알 수 있나요?
- 정답 gt_docs: ['kdic-www-sp-dpstrprot-selectProtSystProtSumr']
- dense rank: 미적중 · hybrid rank: 6
- hybrid top-3:
  1. [❌동일업무오답] 예금자보호제도 / 예금자보호제도 FAQ  `kdic-www-sp-dpstrprot-ProtSystFaq-selectScrn`
  2. [❌동일업무오답] 예금자보호제도 / 미수령금통합신청  `kdic-fins-cm-bbs-selectFaqNramtAply`
  3. [❌동일업무오답] 예금자보호제도 / 개요  `kdic-www-sp-dpstrprot-selectProtSystProtTrgtPrdctSumr`

### [예금자보호제도 · short] 예금보험 가입 따로 해야 하나요?
- 정답 gt_docs: ['kdic-www-sp-dpstrprot-ProtSystFaq-selectScrn']
- dense rank: 6 · hybrid rank: 5
- hybrid top-3:
  1. [❌동일업무오답] 예금자보호제도 / 예금자보호제도  `kdic-www-sp-dpstrprot-ProtSyst-selectScrn`
  2. [❌동일업무오답] 예금자보호제도 / 개요  `kdic-www-sp-dpstrprot-selectProtSystProtTrgtPrdctSumr`
  3. [⚠️타업무혼입] 예금보험금 안내 / 예금보험금이란?  `kdic-www-sp-dpstrprot-DpsmIbamtExpln-selectScrn`

### [은닉재산 신고 · new] 제가 신고했는데 예보가 이미 알고 있던 정보였으면 포상금을 못 받나요?
- 정답 gt_docs: ['kdic-www-sp-sprtfund-SprtFndCncmDclrGudn-selectScrn']
- dense rank: 미적중 · hybrid rank: 4
- hybrid top-3:
  1. [❌동일업무오답] 은닉재산 신고 / FAQ  `kdic-www-sp-sprtfund-SprtFndCncmDclrFaq-selectScrn`
  2. [❌동일업무오답] 은닉재산 신고 / 은닉재산신고  `kdic-fins-cm-bbs-selectFaqCncmPrptDclr`
  3. [⚠️타업무혼입] 예금보험금 안내 / 미수령금통합신청  `kdic-fins-cm-bbs-selectFaqNramtAply`

### [은닉재산 신고 · simple] 일반인도 은닉재산 신고할 수 있어요?
- 정답 gt_docs: ['kdic-www-sp-sprtfund-SprtFndCncmDclrGudn-selectScrn']
- dense rank: 9 · hybrid rank: 4
- hybrid top-3:
  1. [❌동일업무오답] 은닉재산 신고 / 은닉재산신고  `kdic-fins-cm-bbs-selectFaqCncmPrptDclr`
  2. [❌동일업무오답] 은닉재산 신고 / FAQ  `kdic-www-sp-sprtfund-SprtFndCncmDclrFaq-selectScrn`
  3. [❌동일업무오답] 은닉재산 신고 / 신고 및 조회  `kdic-www-sp-sprtfund-SprtCncmDclrInqGudn-selectScrn`

### [착오송금 반환 신청 · paraphrase] 착오송금 반환지원 대상이 어떻게 돼요?
- 정답 gt_docs: ['kdic-www-sp-kmrs-kmrsItrdAplyTrgt-selectScrn', 'kdic-www-sp-kmrs-kmrsItrd-selectScrn']
- dense rank: 미적중 · hybrid rank: 7
- hybrid top-3:
  1. [❌동일업무오답] 착오송금 반환 신청 / 유의사항  `kdic-fins-ir-msdrpr-MsdrprAttnMttr-selectScrn`
  2. [⚠️타업무혼입] 공통 / TOP 10  `kdic-fins-cm-bbs-selectFaqTop10`
  3. [❌동일업무오답] 착오송금 반환 신청 / 착오송금반환지원신청  `kdic-fins-cm-bbs-selectFaqMsdrGvbkAply`

### [착오송금 반환 신청 · short] 이의제기 서류 뭐 필요해요?
- 정답 gt_docs: ['kdic-fins-ir-aplygudn-MsdrAddrsePossDcmntGudn-selectScrn']
- dense rank: 미적중 · hybrid rank: 6
- hybrid top-3:
  1. [⚠️타업무혼입] 채무조정 안내 / 소개와 방법 안내  `kdic-fins-lb-lbltinfo-LbltInfoInqItrdMthdGudn-selectScrn`
  2. [⚠️타업무혼입] 예금보험금 안내 / 미수령금통합신청  `kdic-fins-cm-bbs-selectFaqNramtAply`
  3. [⚠️타업무혼입] 예금보험금 안내 / 신청시 구비서류  `kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn`

### [착오송금 반환 신청 · short] 잘못 송금한 거 온라인 접수돼요?
- 정답 gt_docs: ['kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn']
- dense rank: 미적중 · hybrid rank: 8
- hybrid top-3:
  1. [❌동일업무오답] 착오송금 반환 신청 / 착오송금반환지원신청  `kdic-fins-cm-bbs-selectFaqMsdrGvbkAply`
  2. [⚠️타업무혼입] 공통 / TOP 10  `kdic-fins-cm-bbs-selectFaqTop10`
  3. [❌동일업무오답] 착오송금 반환 신청 / 착오송금반환지원 신청대상  `kdic-www-sp-kmrs-kmrsItrdAplyTrgt-selectScrn`

### [착오송금 반환 신청 · short] 착오송금 어떻게 신청해요?
- 정답 gt_docs: ['kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn']
- dense rank: 6 · hybrid rank: 9
- hybrid top-3:
  1. [❌동일업무오답] 착오송금 반환 신청 / 착오송금수취인  `kdic-fins-ir-aplygudn-MsdrAddrsePossDcmntGudn-selectScrn`
  2. [❌동일업무오답] 착오송금 반환 신청 / 착오송금인  `kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn`
  3. [❌동일업무오답] 착오송금 반환 신청 / 착오송금반환지원 절차  `kdic-www-sp-kmrs-kmrsItrdProc-selectScrn`

### [착오송금 반환 신청 · yesom] 계좌 잘못 눌러서 딴 사람한테 돈을 보냈는데, 나라에서 받아주는 제도가 있다던데?
- 정답 gt_docs: ['kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn']
- dense rank: 미적중 · hybrid rank: 미적중(top10밖)
- hybrid top-3:
  1. [❌동일업무오답] 착오송금 반환 신청 / 착오송금반환지원신청  `kdic-fins-cm-bbs-selectFaqMsdrGvbkAply`
  2. [❌동일업무오답] 착오송금 반환 신청 / 반환지원절차  `kdic-fins-ir-aplygudn-MtrsGvbkSprtProc-selectScrn`
  3. [❌동일업무오답] 착오송금 반환 신청 / 착오송금반환지원 제도란  `kdic-www-sp-kmrs-kmrsItrd-selectScrn`

### [착오송금 반환 신청 · yesom] 군인이 착오송금한 경우 반환 신청 서류는 뭘 준비해야 해?
- 정답 gt_docs: ['kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn']
- dense rank: 1 · hybrid rank: 4
- hybrid top-3:
  1. [❌동일업무오답] 착오송금 반환 신청 / 착오송금수취인  `kdic-fins-ir-aplygudn-MsdrAddrsePossDcmntGudn-selectScrn`
  2. [❌동일업무오답] 착오송금 반환 신청 / 반환지원절차  `kdic-fins-ir-aplygudn-MtrsGvbkSprtProc-selectScrn`
  3. [❌동일업무오답] 착오송금 반환 신청 / 착오송금반환지원 절차  `kdic-www-sp-kmrs-kmrsItrdProc-selectScrn`

### [착오송금 반환 신청 · yesom] 돈을 잘못 보낸 사람은 반환 신청을 무슨 방법으로 하면 돼요?
- 정답 gt_docs: ['kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn']
- dense rank: 미적중 · hybrid rank: 10
- hybrid top-3:
  1. [❌동일업무오답] 착오송금 반환 신청 / 반환지원절차  `kdic-fins-ir-aplygudn-MtrsGvbkSprtProc-selectScrn`
  2. [❌동일업무오답] 착오송금 반환 신청 / 착오송금반환지원 신청대상  `kdic-www-sp-kmrs-kmrsItrdAplyTrgt-selectScrn`
  3. [❌동일업무오답] 착오송금 반환 신청 / 착오송금반환지원 제도란  `kdic-www-sp-kmrs-kmrsItrd-selectScrn`

### [착오송금 반환 신청 · yesom] 외국 거주자가 잘못 보낸 돈 반환 신청할 땐 서류가 어떻게 되나요?
- 정답 gt_docs: ['kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn']
- dense rank: 4 · hybrid rank: 5
- hybrid top-3:
  1. [❌동일업무오답] 착오송금 반환 신청 / 착오송금반환지원신청  `kdic-fins-cm-bbs-selectFaqMsdrGvbkAply`
  2. [❌동일업무오답] 착오송금 반환 신청 / 반환지원절차  `kdic-fins-ir-aplygudn-MtrsGvbkSprtProc-selectScrn`
  3. [❌동일업무오답] 착오송금 반환 신청 / 유의사항  `kdic-fins-ir-msdrpr-MsdrprAttnMttr-selectScrn`

### [착오송금 반환 신청 · yesom] 잘못 들어온 돈을 돌려달라는데 억울한 사정이 있으면 어디에 이의를 낼 수 있어요?
- 정답 gt_docs: ['kdic-fins-ir-aplygudn-MsdrAddrsePossDcmntGudn-selectScrn', 'kdic-fins-ir-addrse-AddrseAttnMttr-selectScrn']
- dense rank: 미적중 · hybrid rank: 4
- hybrid top-3:
  1. [❌동일업무오답] 착오송금 반환 신청 / 반환지원절차  `kdic-fins-ir-aplygudn-MtrsGvbkSprtProc-selectScrn`
  2. [⚠️타업무혼입] 은닉재산 신고 / 신고센터  `kdic-www-sp-sprtfund-SprtFndCncmDclrGudn-selectScrn`
  3. [❌동일업무오답] 착오송금 반환 신청 / 착오송금반환지원 신청대상  `kdic-www-sp-kmrs-kmrsItrdAplyTrgt-selectScrn`

### [착오송금 반환 신청 · yesom] 잘못 송금한 거 온라인으로 접수하는 절차가 어떻게 되나요?
- 정답 gt_docs: ['kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn']
- dense rank: 9 · hybrid rank: 9
- hybrid top-3:
  1. [❌동일업무오답] 착오송금 반환 신청 / 반환지원절차  `kdic-fins-ir-aplygudn-MtrsGvbkSprtProc-selectScrn`
  2. [❌동일업무오답] 착오송금 반환 신청 / 착오송금인  `kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn`
  3. [❌동일업무오답] 착오송금 반환 신청 / 착오송금반환지원 신청대상  `kdic-www-sp-kmrs-kmrsItrdAplyTrgt-selectScrn`

### [착오송금 반환 신청 · yesom] 제가 직접 가서 잘못 보낸 돈 반환 신청하면 뭘 들고 가야 하나요?
- 정답 gt_docs: ['kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn']
- dense rank: 미적중 · hybrid rank: 10
- hybrid top-3:
  1. [❌동일업무오답] 착오송금 반환 신청 / 반환지원절차  `kdic-fins-ir-aplygudn-MtrsGvbkSprtProc-selectScrn`
  2. [❌동일업무오답] 착오송금 반환 신청 / 착오송금반환지원 신청대상  `kdic-www-sp-kmrs-kmrsItrdAplyTrgt-selectScrn`
  3. [❌동일업무오답] 착오송금 반환 신청 / 착오송금반환지원 제도란  `kdic-www-sp-kmrs-kmrsItrd-selectScrn`

### [착오송금 반환 신청 · yesom] 회사 돈을 잘못 이체했는데 법인 반환 신청 서류가 따로 있나요?
- 정답 gt_docs: ['kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn']
- dense rank: 8 · hybrid rank: 6
- hybrid top-3:
  1. [❌동일업무오답] 착오송금 반환 신청 / 착오송금반환지원 신청대상  `kdic-www-sp-kmrs-kmrsItrdAplyTrgt-selectScrn`
  2. [❌동일업무오답] 착오송금 반환 신청 / 반환지원절차  `kdic-fins-ir-aplygudn-MtrsGvbkSprtProc-selectScrn`
  3. [❌동일업무오답] 착오송금 반환 신청 / 유의사항  `kdic-fins-ir-msdrpr-MsdrprAttnMttr-selectScrn`

### [채무조정 안내 · new] 형편이 정말 어려운 사람은 빚을 더 많이 깎아주기도 하나요?
- 정답 gt_docs: ['kdic-www-rb-lbltajmt-LbltAjmtSprtCredRcvrySprt-selectScrn']
- dense rank: 미적중 · hybrid rank: 4
- hybrid top-3:
  1. [❌동일업무오답] 채무조정 안내 / 개인회생  `kdic-www-rb-lbltajmt-LbltAjmtSprtPsnRg-selectScrn`
  2. [❌동일업무오답] 채무조정 안내 / 소개와 방법 안내  `kdic-fins-lb-lbltinfo-LbltInfoInqItrdMthdGudn-selectScrn`
  3. [❌동일업무오답] 채무조정 안내 / 채무조정제도  `kdic-www-rb-lbltajmt-LbltAjmtSprtLbltAjmtSyst-selectScrn`

### [채무조정 안내 · short] 빚 조정 신청은 어디서 해요?
- 정답 gt_docs: ['kdic-www-rb-lbltajmt-LbltAjmtSprtLbltInfoInqDscsnAply-selectScrn', 'kdic-fins-cm-bbs-selectFaqLbltInfoInq']
- dense rank: 7 · hybrid rank: 4
- hybrid top-3:
  1. [❌동일업무오답] 채무조정 안내 / 신용회복 지원  `kdic-www-rb-lbltajmt-LbltAjmtSprtCredRcvrySprt-selectScrn`
  2. [❌동일업무오답] 채무조정 안내 / 채무조정제도  `kdic-www-rb-lbltajmt-LbltAjmtSprtLbltAjmtSyst-selectScrn`
  3. [❌동일업무오답] 채무조정 안내 / 소개와 방법 안내  `kdic-fins-lb-lbltinfo-LbltInfoInqItrdMthdGudn-selectScrn`

### [채무조정 안내 · simple] 빚 때문에 힘든데 예보가 도와주나요?
- 정답 gt_docs: ['kdic-www-rb-lbltajmt-LbltAjmtSprtCredRcvrySprt-selectScrn']
- dense rank: 미적중 · hybrid rank: 미적중(top10밖)
- hybrid top-3:
  1. [❌동일업무오답] 채무조정 안내 / 채무조정제도  `kdic-www-rb-lbltajmt-LbltAjmtSprtLbltAjmtSyst-selectScrn`
  2. [⚠️타업무혼입] 예금자보호제도 / 예금자보호제도 FAQ  `kdic-www-sp-dpstrprot-ProtSystFaq-selectScrn`
  3. [❌동일업무오답] 채무조정 안내 / 소개와 방법 안내  `kdic-fins-lb-lbltinfo-LbltInfoInqItrdMthdGudn-selectScrn`

