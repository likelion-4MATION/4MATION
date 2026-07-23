# 오류 분석 리포트 — hybrid 기준

- 대상: 전체 400건 중 **미적중 25건** · 미적중률 6.2%
- 미적중 = gt_docs 문서가 hybrid top-3 밖. `rank=0` 은 top-10 내에도 정답 문서 없음.
- 태그: **✅정답** / **⚠️타업무혼입**(다른 업무 문서가 올라옴) / **❌동일업무오답**(같은 업무의 다른 문서).

## 1. 업무별 미적중

| 업무 | 문항 | 미적중 | 미적중률 |
|---|---|---|---|
| 착오송금 반환 신청 | 72 | 11 | 15.3% |
| 고객 미수령금 신청 | 67 | 4 | 6.0% |
| 은닉재산 신고 | 62 | 3 | 4.8% |
| 예금보험금 안내 | 65 | 3 | 4.6% |
| 채무조정 안내 | 68 | 3 | 4.4% |
| 예금자보호제도 | 66 | 1 | 1.5% |

## 2. 혼입 문서 랭킹 (미적중 문항 top-3를 잠식한 오답 문서)

| 혼입 문서 | 출현 | 소속 업무 |
|---|---|---|
| `kdic-fins-cm-bbs-selectFaqMsdrGvbkAply` | 6 | 착오송금 반환 신청 |
| `kdic-fins-ir-aplygudn-MtrsGvbkSprtProc-selectScrn` | 5 | 착오송금 반환 신청 |
| `kdic-fins-lb-lbltinfo-LbltInfoInqItrdMthdGudn-selectScrn` | 5 | 채무조정 안내 |
| `kdic-www-rb-lbltajmt-LbltAjmtSprtLbltAjmtSyst-selectScrn` | 5 | 채무조정 안내 |
| `kdic-fins-cm-bbs-selectFaqNramtAply` | 5 | 고객 미수령금 신청 |
| `kdic-www-sp-kmrs-kmrsItrdAplyTrgt-selectScrn` | 5 | 착오송금 반환 신청 |
| `kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn` | 5 | 착오송금 반환 신청 |
| `kdic-fins-cm-bbs-selectFaqTop10` | 5 | 공통 |
| `kdic-fins-ir-msdrpr-MsdrprAttnMttr-selectScrn` | 3 | 착오송금 반환 신청 |
| `kdic-fins-cm-bbs-selectFaqCncmPrptDclr` | 3 | 은닉재산 신고 |
| `kdic-www-sp-sprtfund-SprtFndCncmDclrFaq-selectScrn` | 3 | 은닉재산 신고 |
| `kdic-www-sp-dpstrprot-ProtSystHrpeHistInq-selectScrn` | 3 | 고객 미수령금 신청 |
| `kdic-www-sp-kmrs-kmrsItrd-selectScrn` | 2 | 착오송금 반환 신청 |
| `kdic-fins-cm-bbs-selectFaqLbltInfoInq` | 2 | 채무조정 안내 |
| `kdic-www-sp-dpstrprot-DpsmIbamtExpln-selectScrn` | 2 | 예금보험금 안내 |

## 3. 업무 간 혼입 흐름 (미적중 문항의 top-1이 엉뚱한 업무를 가리킨 경우)

| 정답 업무 | → top-1 업무 | 건수 |
|---|---|---|
| 예금보험금 안내 | 고객 미수령금 신청 | 2 |
| 예금보험금 안내 | 채무조정 안내 | 1 |
| 고객 미수령금 신청 | 착오송금 반환 신청 | 1 |
| 착오송금 반환 신청 | 공통 | 1 |
| 착오송금 반환 신청 | 고객 미수령금 신청 | 1 |
| 고객 미수령금 신청 | 채무조정 안내 | 1 |
| 고객 미수령금 신청 | 공통 | 1 |

## 4. 미적중 문항 상세

### [고객 미수령금 신청 · new] 미수령금이 있는지조차 몰랐는데 예보에서 먼저 연락을 주기도 하나요?
- 정답 gt_docs: ['kdic-www-sp-dpstrprot-ProtSystNramtInqAplyNramtGudn-selectScrn', 'kdic-fins-ua-aplygudn-NramtItgrAplyItrdMthdGudn-selectScrn']
- dense rank: 5 · hybrid rank: 4
- hybrid top-3:
  1. [⚠️타업무혼입] 공통 / TOP 10  `kdic-fins-cm-bbs-selectFaqTop10`
  2. [❌동일업무오답] 고객 미수령금 신청 / 미수령금통합신청  `kdic-fins-cm-bbs-selectFaqNramtAply`
  3. [⚠️타업무혼입] 착오송금 반환 신청 / 착오송금반환지원신청  `kdic-fins-cm-bbs-selectFaqMsdrGvbkAply`

### [고객 미수령금 신청 · new] 옛날에 망한 회사가 여러 곳인데 한 번에 다 조회하고 신청할 수 있나요?
- 정답 gt_docs: ['kdic-fins-ua-aplygudn-NramtItgrAplyItrdMthdGudn-selectScrn', 'kdic-www-sp-dpstrprot-ProtSystNramtInqAplyNramtGudn-selectScrn']
- dense rank: 4 · hybrid rank: 4
- hybrid top-3:
  1. [⚠️타업무혼입] 채무조정 안내 / 채무정보 조회 ＆ 상담신청  `kdic-www-rb-lbltajmt-LbltAjmtSprtLbltInfoInqDscsnAply-selectScrn`
  2. [⚠️타업무혼입] 채무조정 안내 / 파산면책  `kdic-www-rb-lbltajmt-LbltAjmtSprtPsnBr-selectScrn`
  3. [❌동일업무오답] 고객 미수령금 신청 / 상속인 금융거래조회  `kdic-www-sp-dpstrprot-ProtSystHrpeHistInq-selectScrn`

### [고객 미수령금 신청 · new] 제가 예전에 거래하던 회사가 진짜 파산한 게 맞는지 어디서 확인할 수 있나요?
- 정답 gt_docs: ['kdic-www-sp-dpstrprot-ProtSystNramtInqAplyNramtGudn-selectScrn']
- dense rank: 미적중 · hybrid rank: 5
- hybrid top-3:
  1. [❌동일업무오답] 고객 미수령금 신청 / 상속인 금융거래조회  `kdic-www-sp-dpstrprot-ProtSystHrpeHistInq-selectScrn`
  2. [⚠️타업무혼입] 채무조정 안내 / 부채증명원/금융거래정보신청  `kdic-www-sp-sprtfund-SprtFndDebtDlngAplyGudn-selectScrn`
  3. [⚠️타업무혼입] 채무조정 안내 / 채무정보 조회 ＆ 상담신청  `kdic-www-rb-lbltajmt-LbltAjmtSprtLbltInfoInqDscsnAply-selectScrn`

### [고객 미수령금 신청 · yesom] 못 받은 돈, 온라인으로 신청하는 사이트가 어디예요? 인증은 뭘로 하죠?
- 정답 gt_docs: ['kdic-fins-ua-aplygudn-NramtItgrAplyItrdMthdGudn-selectScrn', 'kdic-www-sp-dpstrprot-ProtSystNramtInqAplyNramtGudn-selectScrn']
- dense rank: 3 · hybrid rank: 4
- hybrid top-3:
  1. [⚠️타업무혼입] 착오송금 반환 신청 / 착오송금반환지원 신청방법  `kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn`
  2. [⚠️타업무혼입] 채무조정 안내 / 채무정보조회  `kdic-fins-cm-bbs-selectFaqLbltInfoInq`
  3. [⚠️타업무혼입] 착오송금 반환 신청 / 착오송금반환지원신청  `kdic-fins-cm-bbs-selectFaqMsdrGvbkAply`

### [예금보험금 안내 · simple] 인터넷 신청도 미성년자는 안 되나요?
- 정답 gt_docs: ['kdic-www-sp-dpstrprot-DpsmIbamtExpln-selectScrn']
- dense rank: 미적중 · hybrid rank: 8
- hybrid top-3:
  1. [⚠️타업무혼입] 고객 미수령금 신청 / 미수령금통합신청  `kdic-fins-cm-bbs-selectFaqNramtAply`
  2. [⚠️타업무혼입] 착오송금 반환 신청 / 착오송금인  `kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn`
  3. [⚠️타업무혼입] 채무조정 안내 / 채무정보조회  `kdic-fins-cm-bbs-selectFaqLbltInfoInq`

### [예금보험금 안내 · yesom] 예금보험금을 창구에서 직접 받으려면 어느 지점으로 가야 하나요?
- 정답 gt_docs: ['kdic-www-sp-dpstrprot-DpsmIbamtAplyProc-selectScrn']
- dense rank: 7 · hybrid rank: 4
- hybrid top-3:
  1. [⚠️타업무혼입] 고객 미수령금 신청 / 미수령금통합신청  `kdic-fins-cm-bbs-selectFaqNramtAply`
  2. [❌동일업무오답] 예금보험금 안내 / 예금보험금이란?  `kdic-www-sp-dpstrprot-DpsmIbamtExpln-selectScrn`
  3. [⚠️타업무혼입] 착오송금 반환 신청 / 방문접수안내  `kdic-fins-ir-aplygudn-MtrsVstRcptGudn-selectScrn`

### [예금보험금 안내 · yesom] 은행 망했을 때 보험금은 어떤 방법으로 신청할 수 있어?
- 정답 gt_docs: ['kdic-www-sp-dpstrprot-DpsmIbamtAplyProc-selectScrn']
- dense rank: 5 · hybrid rank: 6
- hybrid top-3:
  1. [⚠️타업무혼입] 채무조정 안내 / 소개와 방법 안내  `kdic-fins-lb-lbltinfo-LbltInfoInqItrdMthdGudn-selectScrn`
  2. [⚠️타업무혼입] 채무조정 안내 / 채무조정제도  `kdic-www-rb-lbltajmt-LbltAjmtSprtLbltAjmtSyst-selectScrn`
  3. [⚠️타업무혼입] 고객 미수령금 신청 / 미수령금통합신청  `kdic-fins-cm-bbs-selectFaqNramtAply`

### [예금자보호제도 · short] 예금보험 가입 따로 해야 하나요?
- 정답 gt_docs: ['kdic-www-sp-dpstrprot-ProtSystFaq-selectScrn']
- dense rank: 9 · hybrid rank: 5
- hybrid top-3:
  1. [❌동일업무오답] 예금자보호제도 / 예금자보호제도  `kdic-www-sp-dpstrprot-ProtSyst-selectScrn`
  2. [⚠️타업무혼입] 예금보험금 안내 / 예금보험금이란?  `kdic-www-sp-dpstrprot-DpsmIbamtExpln-selectScrn`
  3. [❌동일업무오답] 예금자보호제도 / 개요  `kdic-www-sp-dpstrprot-selectProtSystProtTrgtPrdctSumr`

### [은닉재산 신고 · new] 그 사람이 가족 이름으로 재산을 몰래 넘겨놓은 것 같은데 이것도 신고할 수 있나요?
- 정답 gt_docs: ['kdic-www-sp-sprtfund-SprtFndCncmDclrGudn-selectScrn']
- dense rank: 미적중 · hybrid rank: 8
- hybrid top-3:
  1. [❌동일업무오답] 은닉재산 신고 / FAQ  `kdic-www-sp-sprtfund-SprtFndCncmDclrFaq-selectScrn`
  2. [❌동일업무오답] 은닉재산 신고 / 은닉재산신고  `kdic-fins-cm-bbs-selectFaqCncmPrptDclr`
  3. [⚠️타업무혼입] 예금보험금 안내 / 신청시 구비서류  `kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn`

### [은닉재산 신고 · new] 신고하고 나서 어떻게 처리되고 있는지 나중에 확인해볼 수 있나요?
- 정답 gt_docs: ['kdic-www-sp-sprtfund-SprtCncmDclrInqGudn-selectScrn']
- dense rank: 9 · hybrid rank: 4
- hybrid top-3:
  1. [❌동일업무오답] 은닉재산 신고 / FAQ  `kdic-www-sp-sprtfund-SprtFndCncmDclrFaq-selectScrn`
  2. [❌동일업무오답] 은닉재산 신고 / 은닉재산신고  `kdic-fins-cm-bbs-selectFaqCncmPrptDclr`
  3. [⚠️타업무혼입] 고객 미수령금 신청 / 상속인 금융거래조회  `kdic-www-sp-dpstrprot-ProtSystHrpeHistInq-selectScrn`

### [은닉재산 신고 · simple] 일반인도 은닉재산 신고할 수 있어요?
- 정답 gt_docs: ['kdic-www-sp-sprtfund-SprtFndCncmDclrGudn-selectScrn']
- dense rank: 9 · hybrid rank: 4
- hybrid top-3:
  1. [❌동일업무오답] 은닉재산 신고 / 은닉재산신고  `kdic-fins-cm-bbs-selectFaqCncmPrptDclr`
  2. [❌동일업무오답] 은닉재산 신고 / FAQ  `kdic-www-sp-sprtfund-SprtFndCncmDclrFaq-selectScrn`
  3. [❌동일업무오답] 은닉재산 신고 / 신고 및 조회  `kdic-www-sp-sprtfund-SprtCncmDclrInqGudn-selectScrn`

### [착오송금 반환 신청 · paraphrase] 착오송금 반환지원 대상이 어떻게 돼요?
- 정답 gt_docs: ['kdic-www-sp-kmrs-kmrsItrdAplyTrgt-selectScrn', 'kdic-www-sp-kmrs-kmrsItrd-selectScrn']
- dense rank: 미적중 · hybrid rank: 6
- hybrid top-3:
  1. [❌동일업무오답] 착오송금 반환 신청 / 착오송금반환지원신청  `kdic-fins-cm-bbs-selectFaqMsdrGvbkAply`
  2. [⚠️타업무혼입] 공통 / TOP 10  `kdic-fins-cm-bbs-selectFaqTop10`
  3. [❌동일업무오답] 착오송금 반환 신청 / 유의사항  `kdic-fins-ir-msdrpr-MsdrprAttnMttr-selectScrn`

### [착오송금 반환 신청 · short] 이의제기 서류 뭐 필요해요?
- 정답 gt_docs: ['kdic-fins-ir-aplygudn-MsdrAddrsePossDcmntGudn-selectScrn']
- dense rank: 미적중 · hybrid rank: 7
- hybrid top-3:
  1. [⚠️타업무혼입] 고객 미수령금 신청 / 미수령금통합신청  `kdic-fins-cm-bbs-selectFaqNramtAply`
  2. [⚠️타업무혼입] 채무조정 안내 / 소개와 방법 안내  `kdic-fins-lb-lbltinfo-LbltInfoInqItrdMthdGudn-selectScrn`
  3. [⚠️타업무혼입] 채무조정 안내 / 채무조정제도  `kdic-www-rb-lbltajmt-LbltAjmtSprtLbltAjmtSyst-selectScrn`

### [착오송금 반환 신청 · short] 잘못 송금한 거 온라인 접수돼요?
- 정답 gt_docs: ['kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn']
- dense rank: 미적중 · hybrid rank: 6
- hybrid top-3:
  1. [❌동일업무오답] 착오송금 반환 신청 / 착오송금반환지원신청  `kdic-fins-cm-bbs-selectFaqMsdrGvbkAply`
  2. [⚠️타업무혼입] 공통 / TOP 10  `kdic-fins-cm-bbs-selectFaqTop10`
  3. [❌동일업무오답] 착오송금 반환 신청 / 착오송금인  `kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn`

### [착오송금 반환 신청 · short] 착오송금 어떻게 신청해요?
- 정답 gt_docs: ['kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn']
- dense rank: 7 · hybrid rank: 9
- hybrid top-3:
  1. [❌동일업무오답] 착오송금 반환 신청 / 착오송금인  `kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn`
  2. [❌동일업무오답] 착오송금 반환 신청 / 착오송금반환지원 신청대상  `kdic-www-sp-kmrs-kmrsItrdAplyTrgt-selectScrn`
  3. [❌동일업무오답] 착오송금 반환 신청 / 착오송금수취인  `kdic-fins-ir-aplygudn-MsdrAddrsePossDcmntGudn-selectScrn`

### [착오송금 반환 신청 · yesom] 계좌 잘못 눌러서 딴 사람한테 돈을 보냈는데, 나라에서 받아주는 제도가 있다던데?
- 정답 gt_docs: ['kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn']
- dense rank: 미적중 · hybrid rank: 미적중(top10밖)
- hybrid top-3:
  1. [❌동일업무오답] 착오송금 반환 신청 / 착오송금반환지원신청  `kdic-fins-cm-bbs-selectFaqMsdrGvbkAply`
  2. [❌동일업무오답] 착오송금 반환 신청 / 반환지원절차  `kdic-fins-ir-aplygudn-MtrsGvbkSprtProc-selectScrn`
  3. [❌동일업무오답] 착오송금 반환 신청 / 착오송금반환지원 제도란  `kdic-www-sp-kmrs-kmrsItrd-selectScrn`

### [착오송금 반환 신청 · yesom] 돈을 잘못 보낸 사람은 반환 신청을 무슨 방법으로 하면 돼요?
- 정답 gt_docs: ['kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn']
- dense rank: 미적중 · hybrid rank: 미적중(top10밖)
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

### [착오송금 반환 신청 · yesom] 이의제기를 온라인으로 넣는 방법은 어떻게 되나요?
- 정답 gt_docs: ['kdic-fins-ir-aplygudn-MsdrAddrsePossDcmntGudn-selectScrn']
- dense rank: 미적중 · hybrid rank: 6
- hybrid top-3:
  1. [⚠️타업무혼입] 공통 / TOP 10  `kdic-fins-cm-bbs-selectFaqTop10`
  2. [❌동일업무오답] 착오송금 반환 신청 / 착오송금인  `kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn`
  3. [⚠️타업무혼입] 채무조정 안내 / 개인회생  `kdic-www-rb-lbltajmt-LbltAjmtSprtPsnRg-selectScrn`

### [착오송금 반환 신청 · yesom] 잘못 송금한 거 온라인으로 접수하는 절차가 어떻게 되나요?
- 정답 gt_docs: ['kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn']
- dense rank: 9 · hybrid rank: 7
- hybrid top-3:
  1. [❌동일업무오답] 착오송금 반환 신청 / 반환지원절차  `kdic-fins-ir-aplygudn-MtrsGvbkSprtProc-selectScrn`
  2. [❌동일업무오답] 착오송금 반환 신청 / 착오송금반환지원 신청대상  `kdic-www-sp-kmrs-kmrsItrdAplyTrgt-selectScrn`
  3. [❌동일업무오답] 착오송금 반환 신청 / 착오송금인  `kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn`

### [착오송금 반환 신청 · yesom] 제가 직접 가서 잘못 보낸 돈 반환 신청하면 뭘 들고 가야 하나요?
- 정답 gt_docs: ['kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn']
- dense rank: 미적중 · hybrid rank: 미적중(top10밖)
- hybrid top-3:
  1. [❌동일업무오답] 착오송금 반환 신청 / 반환지원절차  `kdic-fins-ir-aplygudn-MtrsGvbkSprtProc-selectScrn`
  2. [❌동일업무오답] 착오송금 반환 신청 / 착오송금반환지원 신청대상  `kdic-www-sp-kmrs-kmrsItrdAplyTrgt-selectScrn`
  3. [❌동일업무오답] 착오송금 반환 신청 / 유의사항  `kdic-fins-ir-addrse-AddrseAttnMttr-selectScrn`

### [착오송금 반환 신청 · yesom] 회사 돈을 잘못 이체했는데 법인 반환 신청 서류가 따로 있나요?
- 정답 gt_docs: ['kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn']
- dense rank: 9 · hybrid rank: 6
- hybrid top-3:
  1. [❌동일업무오답] 착오송금 반환 신청 / 착오송금반환지원 신청대상  `kdic-www-sp-kmrs-kmrsItrdAplyTrgt-selectScrn`
  2. [⚠️타업무혼입] 공통 / TOP 10  `kdic-fins-cm-bbs-selectFaqTop10`
  3. [❌동일업무오답] 착오송금 반환 신청 / 유의사항  `kdic-fins-ir-msdrpr-MsdrprAttnMttr-selectScrn`

### [채무조정 안내 · new] 형편이 정말 어려운 사람은 빚을 더 많이 깎아주기도 하나요?
- 정답 gt_docs: ['kdic-www-rb-lbltajmt-LbltAjmtSprtCredRcvrySprt-selectScrn']
- dense rank: 4 · hybrid rank: 5
- hybrid top-3:
  1. [❌동일업무오답] 채무조정 안내 / 소개와 방법 안내  `kdic-fins-lb-lbltinfo-LbltInfoInqItrdMthdGudn-selectScrn`
  2. [❌동일업무오답] 채무조정 안내 / 개인회생  `kdic-www-rb-lbltajmt-LbltAjmtSprtPsnRg-selectScrn`
  3. [❌동일업무오답] 채무조정 안내 / 채무조정제도  `kdic-www-rb-lbltajmt-LbltAjmtSprtLbltAjmtSyst-selectScrn`

### [채무조정 안내 · short] 빚 조정 신청은 어디서 해요?
- 정답 gt_docs: ['kdic-www-rb-lbltajmt-LbltAjmtSprtLbltInfoInqDscsnAply-selectScrn', 'kdic-fins-cm-bbs-selectFaqLbltInfoInq']
- dense rank: 5 · hybrid rank: 4
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

