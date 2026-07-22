# 미적중(Miss) 진단 — hit@3 미포함 전건

- 전체 150건 · Miss 48건 · 판정: parent_doc_id ∈ gt_docs (문서 단위)
- rank=0 은 top-10 안에 정답 문서가 전혀 없음(검색 실패), rank>3 은 4위 이하.

| QID | source | 업무 | 질문 | rank | GT문서(gt_docs) | Top1(score) | Top2 | Top3 |
|---|---|---|---|---|---|---|---|---|
| 41 | heading | 고객 미수령금 신청 | 파산배당금이란? | 없음 | kdic-www-sp-dpstrprot-ProtSystNramtInqAplyNramtGudn-selectScrn;kdic-fins-ua-aplygudn-NramtItgrAplyItrdMthdGudn-selectScrn | kdic-www-rb-lbltajmt-LbltAjmtSprtPsnBr-selectScrn#01 (0.0315) | kdic-www-rb-lbltajmt-LbltAjmtSprtPsnBr-selectScrn#00 | kdic-www-rb-lbltajmt-LbltAjmtSprtPsnBr-selectScrn#02 |
| 42 | heading | 고객 미수령금 신청 | 개산지급금 정산금이란? | 8 | kdic-www-sp-dpstrprot-ProtSystNramtInqAplyNramtGudn-selectScrn;kdic-fins-ua-aplygudn-NramtItgrAplyItrdMthdGudn-selectScrn | kdic-www-sp-dpstrprot-DpsmIbamtExpln-selectScrn#01 (0.0305) | kdic-www-sp-sprtfund-SprtFndCncmDclrFaq-selectScrn#10 | kdic-www-sp-dpstrprot-DpsmIbamtExpln-selectScrn#02 |
| 48 | heading | 착오송금 반환 신청 | 송금하시겠습니까? | 4 | kdic-fins-ir-aplygudn-MtrsGvbkSprtProc-selectScrn;kdic-www-sp-kmrs-kmrsItrd-selectScrn | kdic-www-sp-kmrs-kmrsItrdAplyTrgt-selectScrn#00 (0.0325) | kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00 | kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00 |
| 55 | yesom | 예금자보호제도 | 예금자보호제도 | 8 | kdic-www-sp-dpstrprot-ProtSyst-selectScrn | kdic-www-sp-dpstrprot-ProtSystProtLmts-selectScrn#00 (0.0325) | kdic-www-sp-dpstrprot-ProtSystProtGudn-selectScrn#00 | kdic-www-sp-dpstrprot-ProtSystFaq-selectScrn#03 |
| 57 | yesom | 착오송금 반환 신청 | 착오송금 반환 신청 | 4 | kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn | kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00 (0.0325) | kdic-www-sp-kmrs-kmrsItrd-selectScrn#00 | kdic-www-sp-kmrs-kmrsItrdAplyTrgt-selectScrn#00 |
| 74 | yesom | 착오송금 반환 신청 | 착오송금수취인 이의제기 | 없음 | kdic-fins-ir-aplygudn-MsdrAddrsePossDcmntGudn-selectScrn;kdic-fins-ir-addrse-AddrseAttnMttr-selectScrn | kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00 (0.0328) | kdic-www-sp-kmrs-kmrsItrd-selectScrn#00 | kdic-www-sp-kmrs-kmrsItrdAplyTrgt-selectScrn#00 |
| 75 | yesom | 착오송금 반환 신청 | 착오송금수취인 이체수수료 환급신청 | 없음 | kdic-fins-ir-aplygudn-MsdrAddrsePossDcmntGudn-selectScrn | kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00 (0.0323) | kdic-www-sp-kmrs-kmrsItrdAplyTrgt-selectScrn#00 | kdic-www-sp-kmrs-kmrsItrd-selectScrn#00 |
| 83 | yesom | 고객 미수령금 신청 | 군인 신청서류 | 없음 | kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn;kdic-fins-cm-bbs-selectFaqNramtAply | kdic-www-rb-lbltajmt-LbltAjmtSprtLbltAjmtSyst-selectScrn#01 (0.0325) | kdic-www-rb-lbltajmt-LbltAjmtSprtCredRcvrySprt-selectScrn#02 | kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00 |
| 84 | yesom | 고객 미수령금 신청 | 대리인 신청서류 | 5 | kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn;kdic-fins-cm-bbs-selectFaqNramtAply | kdic-www-rb-lbltajmt-LbltAjmtSprtCredRcvrySprt-selectScrn#02 (0.0328) | kdic-www-rb-lbltajmt-LbltAjmtSprtLbltAjmtSyst-selectScrn#01 | kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00 |
| 86 | yesom | 예금보험금 안내 | 방문 신청방법 | 없음 | kdic-www-sp-dpstrprot-DpsmIbamtAplyProc-selectScrn | kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00 (0.0328) | kdic-www-rb-lbltajmt-LbltAjmtSprtCredRcvrySprt-selectScrn#04 | kdic-www-sp-sprtfund-SprtFndDebtDlngAplyGudn-selectScrn#00 |
| 87 | yesom | 착오송금 반환 신청 | 착오송금반환 방문 신청 | 4 | kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn;kdic-fins-ir-aplygudn-MtrsVstRcptGudn-selectScrn | kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00 (0.0328) | kdic-www-sp-kmrs-kmrsItrd-selectScrn#00 | kdic-www-sp-kmrs-kmrsItrdAplyTrgt-selectScrn#00 |
| 88 | yesom | 고객 미수령금 신청 | 법인 및 단체 신청서류 | 없음 | kdic-fins-cm-bbs-selectFaqNramtAply;kdic-www-sp-dpstrprot-ProtSystNramtInqAplyNramtGudn-selectScrn | kdic-www-rb-lbltajmt-LbltAjmtSprtLbltAjmtSyst-selectScrn#01 (0.0313) | kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00 | kdic-www-rb-lbltajmt-LbltAjmtSprtCredRcvrySprt-selectScrn#02 |
| 91 | yesom | 예금보험금 안내 | 보험금신청서류 | 없음 | kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn;kdic-fins-cm-bbs-selectFaqNramtAply | kdic-www-sp-dpstrprot-DpsmIbamtAplyProc-selectScrn#00 (0.032) | kdic-www-sp-dpstrprot-DpsmIbamtExpln-selectScrn#02 | kdic-www-sp-dpstrprot-ProtSystHrpeHistInq-selectScrn#01 |
| 99 | yesom | 예금보험금 안내 | 인터넷 신청방법 | 없음 | kdic-www-sp-dpstrprot-DpsmIbamtAplyProc-selectScrn | kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00 (0.0323) | kdic-www-sp-sprtfund-SprtFndDebtDlngAplyGudn-selectScrn#00 | kdic-www-sp-sprtfund-SprtFndDebtDlngAplyGudn-selectScrn#01 |
| 101 | yesom | 착오송금 반환 신청 | 착오송금반환 신청 서류 | 4 | kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn;kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn | kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00 (0.0328) | kdic-www-sp-kmrs-kmrsItrd-selectScrn#00 | kdic-www-sp-kmrs-kmrsItrdAplyTrgt-selectScrn#00 |
| 102 | yesom | 착오송금 반환 신청 | 착오송금 이의제기 방문 신청 | 없음 | kdic-fins-ir-aplygudn-MsdrAddrsePossDcmntGudn-selectScrn | kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00 (0.0325) | kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00 | kdic-www-sp-kmrs-kmrsItrdAplyTrgt-selectScrn#00 |
| 103 | yesom | 착오송금 반환 신청 | 착오송금 이의제기 인터넷 신청 | 없음 | kdic-fins-ir-aplygudn-MsdrAddrsePossDcmntGudn-selectScrn | kdic-www-sp-kmrs-kmrsItrdAplyTrgt-selectScrn#00 (0.0323) | kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00 | kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00 |
| 104 | yesom | 착오송금 반환 신청 | 착오송금수취인 이체수수료환급 방문 신청 | 없음 | kdic-fins-ir-aplygudn-MsdrAddrsePossDcmntGudn-selectScrn | kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00 (0.0325) | kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00 | kdic-www-sp-kmrs-kmrsItrdAplyTrgt-selectScrn#00 |
| 105 | yesom | 착오송금 반환 신청 | 착오송금수취인 이체수수료환급 인터넷 신청 | 없음 | kdic-fins-ir-aplygudn-MsdrAddrsePossDcmntGudn-selectScrn | kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00 (0.0323) | kdic-www-sp-kmrs-kmrsItrdAplyTrgt-selectScrn#00 | kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00 |
| 106 | yesom | 예금보험금 안내 | 국외거주 또는 유학생 신청서류 (보험금신청서류) | 4 | kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn;kdic-fins-cm-bbs-selectFaqNramtAply | kdic-www-rb-lbltajmt-LbltAjmtSprtLbltAjmtSyst-selectScrn#01 (0.0323) | kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00 | kdic-www-sp-dpstrprot-DpsmIbamtExpln-selectScrn#02 |
| 107 | yesom | 착오송금 반환 신청 | 국외거주 또는 유학생 신청서류 (착오송금반환 신청 서류) | 없음 | kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn | kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00 (0.032) | kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00 | kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn#02 |
| 109 | yesom | 착오송금 반환 신청 | 군복무자 신청서류 (착오송금반환 신청 서류) | 없음 | kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn | kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00 (0.0325) | kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00 | kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn#02 |
| 110 | yesom | 예금보험금 안내 | 대리인 신청서류 (보험금신청서류) | 8 | kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn;kdic-fins-cm-bbs-selectFaqNramtAply | kdic-www-rb-lbltajmt-LbltAjmtSprtLbltAjmtSyst-selectScrn#01 (0.0325) | kdic-www-rb-lbltajmt-LbltAjmtSprtCredRcvrySprt-selectScrn#02 | kdic-www-sp-sprtfund-SprtFndDebtDlngAplyGudn-selectScrn#00 |
| 112 | yesom | 착오송금 반환 신청 | 미성년자 신청서류 (착오송금반환 신청 서류) | 없음 | kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn | kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00 (0.0323) | kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00 | kdic-www-rb-lbltajmt-LbltAjmtSprtLbltAjmtSyst-selectScrn#01 |
| 113 | yesom | 착오송금 반환 신청 | 대리인방문 착오송금반환 신청서류 | 없음 | kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn | kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00 (0.0325) | kdic-www-rb-lbltajmt-LbltAjmtSprtCredRcvrySprt-selectScrn#02 | kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00 |
| 114 | yesom | 착오송금 반환 신청 | 본인방문 착오송금반환 신청서류 | 없음 | kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn | kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00 (0.0323) | kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00 | kdic-www-sp-kmrs-kmrsItrdAplyTrgt-selectScrn#00 |
| 115 | yesom | 예금보험금 안내 | 법인 및 단체 신청서류 (보험금신청서류) | 없음 | kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn;kdic-fins-cm-bbs-selectFaqNramtAply | kdic-www-sp-dpstrprot-ProtSystFaq-selectScrn#12 (0.0318) | kdic-www-sp-dpstrprot-DpsmIbamtAplyProc-selectScrn#00 | kdic-www-rb-lbltajmt-LbltAjmtSprtLbltAjmtSyst-selectScrn#01 |
| 116 | yesom | 착오송금 반환 신청 | 법인 및 단체 신청서류 (착오송금반환 신청 서류) | 없음 | kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn | kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00 (0.0325) | kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00 | kdic-www-rb-lbltajmt-LbltAjmtSprtCredRcvrySprt-selectScrn#02 |
| 120 | yesom | 예금자보호제도 | 보호 금융상품 - 종합금융회사 | 4 | kdic-www-sp-dpstrprot-selectProtSystProtTrgtPrdctSumr | kdic-www-sp-dpstrprot-ProtSystFaq-selectScrn#03 (0.032) | kdic-www-sp-dpstrprot-selectProtSystProtSumr#00 | kdic-www-sp-dpstrprot-ProtSystProtGudn-selectScrn#00 |
| 124 | yesom | 착오송금 반환 신청 | 예금자 본인 신청서류 (착오송금반환 신청 서류) | 없음 | kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn | kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00 (0.0323) | kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00 | kdic-www-sp-kmrs-kmrsItrdAplyTrgt-selectScrn#00 |
| 125 | yesom | 착오송금 반환 신청 | 비법인단체 신청서류 | 없음 | kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn | kdic-www-rb-lbltajmt-LbltAjmtSprtLbltAjmtSyst-selectScrn#01 (0.0313) | kdic-www-rb-lbltajmt-LbltAjmtSprtCredRcvrySprt-selectScrn#02 | kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00 |
| 131 | yesom | 예금보험금 안내 | 사망 예금자 신청서류 (보험금신청서류) | 6 | kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn;kdic-fins-cm-bbs-selectFaqNramtAply | kdic-www-sp-dpstrprot-ProtSystHrpeHistInq-selectScrn#01 (0.0328) | kdic-www-sp-dpstrprot-DpsmIbamtAplyProc-selectScrn#00 | kdic-www-sp-dpstrprot-DpsmIbamtExpln-selectScrn#02 |
| 132 | yesom | 착오송금 반환 신청 | 대리인 인터넷 신청서류 | 없음 | kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn | kdic-www-sp-sprtfund-SprtFndDebtDlngAplyGudn-selectScrn#00 (0.032) | kdic-www-rb-lbltajmt-LbltAjmtSprtCredRcvrySprt-selectScrn#02 | kdic-www-sp-sprtfund-SprtFndDebtDlngAplyGudn-selectScrn#01 |
| 133 | yesom | 착오송금 반환 신청 | 본인 인터넷 신청서류 | 없음 | kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn | kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00 (0.0325) | kdic-www-sp-sprtfund-SprtFndDebtDlngAplyGudn-selectScrn#00 | kdic-www-sp-sprtfund-SprtFndDebtDlngAplyGudn-selectScrn#01 |
| 136 | yesom | 착오송금 반환 신청 | 방문 국외거주 착오송금 서류 | 없음 | kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn | kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00 (0.0325) | kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00 | kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn#02 |
| 137 | yesom | 착오송금 반환 신청 | 방문 군복무 착오송금 서류 | 없음 | kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn | kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn#02 (0.0325) | kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00 | kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00 |
| 138 | yesom | 착오송금 반환 신청 | 방문 미성년자 착오송금 서류 | 없음 | kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn | kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00 (0.0315) | kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00 | kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn#02 |
| 139 | yesom | 착오송금 반환 신청 | 법인 및 단체 대표 방문 신청서류 | 없음 | kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn | kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00 (0.0313) | kdic-www-sp-sprtfund-SprtFndCncmDclrGudn-selectScrn#03 | kdic-www-rb-lbltajmt-LbltAjmtSprtCredRcvrySprt-selectScrn#04 |
| 140 | yesom | 착오송금 반환 신청 | 법인 및 단체 직원 방문 신청서류 | 없음 | kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn | kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00 (0.032) | kdic-www-sp-sprtfund-SprtFndCncmDclrGudn-selectScrn#03 | kdic-www-rb-lbltajmt-LbltAjmtSprtCredRcvrySprt-selectScrn#04 |
| 141 | yesom | 착오송금 반환 신청 | 비법인단체 대표 방문 신청서류 | 없음 | kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn | kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00 (0.031) | kdic-www-sp-sprtfund-SprtFndCncmDclrGudn-selectScrn#03 | kdic-www-rb-lbltajmt-LbltAjmtSprtCredRcvrySprt-selectScrn#04 |
| 142 | yesom | 착오송금 반환 신청 | 비법인단체 직원 방문 신청서류 | 없음 | kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn | kdic-www-sp-sprtfund-SprtFndCncmDclrGudn-selectScrn#03 (0.0315) | kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00 | kdic-www-rb-lbltajmt-LbltAjmtSprtCredRcvrySprt-selectScrn#04 |
| 144 | yesom | 착오송금 반환 신청 | 인터넷 국외거주 착오송금 서류 | 없음 | kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn | kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00 (0.0323) | kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00 | kdic-www-sp-kmrs-kmrsItrdAplyTrgt-selectScrn#00 |
| 145 | yesom | 착오송금 반환 신청 | 인터넷 군복무 착오송금 서류 | 없음 | kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn | kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00 (0.0323) | kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00 | kdic-www-sp-kmrs-kmrsItrd-selectScrn#00 |
| 146 | yesom | 착오송금 반환 신청 | 인터넷 미성년자 착오송금 서류 | 없음 | kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn | kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00 (0.032) | kdic-www-sp-kmrs-kmrsItrd-selectScrn#00 | kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00 |
| 147 | yesom | 착오송금 반환 신청 | 인터넷 법인 대표 착오송금 서류 | 없음 | kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn | kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00 (0.0318) | kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00 | kdic-www-sp-kmrs-kmrsItrd-selectScrn#00 |
| 148 | yesom | 착오송금 반환 신청 | 인터넷 법인 직원 착오송금 서류 | 없음 | kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn | kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00 (0.032) | kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00 | kdic-www-sp-kmrs-kmrsItrd-selectScrn#00 |
| 149 | yesom | 착오송금 반환 신청 | 인터넷 비법인 대표 착오송금 서류 | 없음 | kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn | kdic-www-sp-kmrs-kmrsItrd-selectScrn#00 (0.032) | kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00 | kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00 |
| 150 | yesom | 착오송금 반환 신청 | 인터넷 비법인 직원 착오송금 서류 | 없음 | kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn | kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00 (0.0318) | kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00 | kdic-www-sp-kmrs-kmrsItrd-selectScrn#00 |

## 미리보기 비교 (GT vs Top1)

### QID 41 · 고객 미수령금 신청 · heading · rank=없음
- 질문: 파산배당금이란?
- GT문서: kdic-www-sp-dpstrprot-ProtSystNramtInqAplyNramtGudn-selectScrn;kdic-fins-ua-aplygudn-NramtItgrAplyItrdMthdGudn-selectScrn  (GT청크 1개: kdic-www-sp-dpstrprot-ProtSystNramtInqAplyNramtGudn-selectScrn#00)
- GT preview: 예금보험공사는 부실화된 금융회사의 예금자등이 찾아가지 아니한 금액을 고객 미수령금으로 분류하여 통합 관리하고 있으며, 지속적인 홍보 및 안내를 통한 적극적인 미수
- Top1: kdic-www-rb-lbltajmt-LbltAjmtSprtPsnBr-selectScrn#01  preview: 문 이송 각하·기각 예납명령 기각 파산선고 파산관재인 선임 파산관재인 재산관리·조사 채권자집회 의견청취기일(면책심문기일) 파산

### QID 42 · 고객 미수령금 신청 · heading · rank=8
- 질문: 개산지급금 정산금이란?
- GT문서: kdic-www-sp-dpstrprot-ProtSystNramtInqAplyNramtGudn-selectScrn;kdic-fins-ua-aplygudn-NramtItgrAplyItrdMthdGudn-selectScrn  (GT청크 1개: kdic-www-sp-dpstrprot-ProtSystNramtInqAplyNramtGudn-selectScrn#00)
- GT preview: 예금보험공사는 부실화된 금융회사의 예금자등이 찾아가지 아니한 금액을 고객 미수령금으로 분류하여 통합 관리하고 있으며, 지속적인 홍보 및 안내를 통한 적극적인 미수
- Top1: kdic-www-sp-dpstrprot-DpsmIbamtExpln-selectScrn#01  preview: 예금보험금/개산지급금/가지급금 신청 바로가기」 에 접속하여 예금보험금/개산지급금/가지급금을 신청하실 수 있습니다. 예금보험금이

### QID 48 · 착오송금 반환 신청 · heading · rank=4
- 질문: 송금하시겠습니까?
- GT문서: kdic-fins-ir-aplygudn-MtrsGvbkSprtProc-selectScrn;kdic-www-sp-kmrs-kmrsItrd-selectScrn  (GT청크 1개: kdic-www-sp-kmrs-kmrsItrd-selectScrn#00)
- GT preview: 제도 소개 안내영상 영상내용입니다. 제도 소개 안내영상입니다. 잘못 보낸 돈 되찾기 서비스란 착오송금인이 실수로 잘못 보낸 돈을 최소한의 비용으로 빠르게 되찾을 
- Top1: kdic-www-sp-kmrs-kmrsItrdAplyTrgt-selectScrn#00  preview: 신청 가능한 착오송금 금액 한도가 있나요? 신청 가능 한도는 착오송금 건당 5만원 이상 ~ 1억원 이하 입니다. 언제까지 신청

### QID 55 · 예금자보호제도 · yesom · rank=8
- 질문: 예금자보호제도
- GT문서: kdic-www-sp-dpstrprot-ProtSyst-selectScrn  (GT청크 1개: kdic-www-sp-dpstrprot-ProtSyst-selectScrn#00)
- GT preview: 예금보험의 구조 금융회사가 평소에 예금보험료를 예금보험공사에 납부하고 예금보험공사는 수납받은 예금보험료를 기금으로 적립하고 있다가 금융회사가 부실화되어 고객의 예
- Top1: kdic-www-sp-dpstrprot-ProtSystProtLmts-selectScrn#00  preview: 예금자보호제도는 다수의 소액예금자를 우선 보호하고 부실 금융회사를 선택한 예금자도 일정부분 책임을 분담한다는 차원에서 예금의 

### QID 57 · 착오송금 반환 신청 · yesom · rank=4
- 질문: 착오송금 반환 신청
- GT문서: kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn  (GT청크 1개: kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00)
- GT preview: 신청방법 온라인 신청 사이트 : fins.kdic.or.kr (상단 아이콘 클릭 시 사이트 연결) 접속방법 : PC (모바일은 추후 지원 예정) 준비물 : 공동인
- Top1: kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00  preview: 착오송금반환지원 절차 ( 착오송금인-예금보험공사-착오송금 수취인, 중앙행정기관 금융회사등 - 예금보험공사 - 법원 ) 1. 착

### QID 74 · 착오송금 반환 신청 · yesom · rank=없음
- 질문: 착오송금수취인 이의제기
- GT문서: kdic-fins-ir-aplygudn-MsdrAddrsePossDcmntGudn-selectScrn;kdic-fins-ir-addrse-AddrseAttnMttr-selectScrn  (GT청크 0개: )
- GT preview: (GT청크없음)
- Top1: kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00  preview: 착오송금반환지원 절차 ( 착오송금인-예금보험공사-착오송금 수취인, 중앙행정기관 금융회사등 - 예금보험공사 - 법원 ) 1. 착

### QID 75 · 착오송금 반환 신청 · yesom · rank=없음
- 질문: 착오송금수취인 이체수수료 환급신청
- GT문서: kdic-fins-ir-aplygudn-MsdrAddrsePossDcmntGudn-selectScrn  (GT청크 0개: )
- GT preview: (GT청크없음)
- Top1: kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00  preview: 착오송금반환지원 절차 ( 착오송금인-예금보험공사-착오송금 수취인, 중앙행정기관 금융회사등 - 예금보험공사 - 법원 ) 1. 착

### QID 83 · 고객 미수령금 신청 · yesom · rank=없음
- 질문: 군인 신청서류
- GT문서: kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn;kdic-fins-cm-bbs-selectFaqNramtAply  (GT청크 4개: kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn#00;kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn#01;kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn#02)
- GT preview: 01 예금자 본인이 찾을 경우 열기 예금자 본인의 확인 증명 주민등록증, 경로우대증, 운전면허증, 여권 등 공공기관에서 발행한 사진이 들어간 본인임을 확인할 수 
- Top1: kdic-www-rb-lbltajmt-LbltAjmtSprtLbltAjmtSyst-selectScrn#01  preview: 주민등록 등ㆍ초본 및 신분증(주민등록증, 운전면허증) 소득증명서류(급여명세서, 근로소득원천징수영수증 등) 재산증명서류(부동산등

### QID 84 · 고객 미수령금 신청 · yesom · rank=5
- 질문: 대리인 신청서류
- GT문서: kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn;kdic-fins-cm-bbs-selectFaqNramtAply  (GT청크 4개: kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn#00;kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn#01;kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn#02)
- GT preview: 01 예금자 본인이 찾을 경우 열기 예금자 본인의 확인 증명 주민등록증, 경로우대증, 운전면허증, 여권 등 공공기관에서 발행한 사진이 들어간 본인임을 확인할 수 
- Top1: kdic-www-rb-lbltajmt-LbltAjmtSprtCredRcvrySprt-selectScrn#02  preview: 구분 | 내용 | 비고 신청인 | 채무자 또는 대리인 | 대리인의 경우 채무자의 인감증명서와 위임장 (동의서)등 권리 위임에 

### QID 86 · 예금보험금 안내 · yesom · rank=없음
- 질문: 방문 신청방법
- GT문서: kdic-www-sp-dpstrprot-DpsmIbamtAplyProc-selectScrn  (GT청크 2개: kdic-www-sp-dpstrprot-DpsmIbamtAplyProc-selectScrn#00;kdic-www-sp-dpstrprot-DpsmIbamtAplyProc-selectScrn#01)
- GT preview: 01 부보금융회사 보험사고 발생 열기 1종 보험사고 금융회사의 재무상황 악화 등으로 인해 예금의 지급이 정지된 경우 2종 보험사고 금융회사가 인 · 허가 취소, 
- Top1: kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00  preview: 신청방법 온라인 신청 사이트 : fins.kdic.or.kr (상단 아이콘 클릭 시 사이트 연결) 접속방법 : PC (모바일은

### QID 87 · 착오송금 반환 신청 · yesom · rank=4
- 질문: 착오송금반환 방문 신청
- GT문서: kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn;kdic-fins-ir-aplygudn-MtrsVstRcptGudn-selectScrn  (GT청크 1개: kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00)
- GT preview: 신청방법 온라인 신청 사이트 : fins.kdic.or.kr (상단 아이콘 클릭 시 사이트 연결) 접속방법 : PC (모바일은 추후 지원 예정) 준비물 : 공동인
- Top1: kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00  preview: 착오송금반환지원 절차 ( 착오송금인-예금보험공사-착오송금 수취인, 중앙행정기관 금융회사등 - 예금보험공사 - 법원 ) 1. 착

### QID 88 · 고객 미수령금 신청 · yesom · rank=없음
- 질문: 법인 및 단체 신청서류
- GT문서: kdic-fins-cm-bbs-selectFaqNramtAply;kdic-www-sp-dpstrprot-ProtSystNramtInqAplyNramtGudn-selectScrn  (GT청크 1개: kdic-www-sp-dpstrprot-ProtSystNramtInqAplyNramtGudn-selectScrn#00)
- GT preview: 예금보험공사는 부실화된 금융회사의 예금자등이 찾아가지 아니한 금액을 고객 미수령금으로 분류하여 통합 관리하고 있으며, 지속적인 홍보 및 안내를 통한 적극적인 미수
- Top1: kdic-www-rb-lbltajmt-LbltAjmtSprtLbltAjmtSyst-selectScrn#01  preview: 주민등록 등ㆍ초본 및 신분증(주민등록증, 운전면허증) 소득증명서류(급여명세서, 근로소득원천징수영수증 등) 재산증명서류(부동산등

### QID 91 · 예금보험금 안내 · yesom · rank=없음
- 질문: 보험금신청서류
- GT문서: kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn;kdic-fins-cm-bbs-selectFaqNramtAply  (GT청크 4개: kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn#00;kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn#01;kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn#02)
- GT preview: 01 예금자 본인이 찾을 경우 열기 예금자 본인의 확인 증명 주민등록증, 경로우대증, 운전면허증, 여권 등 공공기관에서 발행한 사진이 들어간 본인임을 확인할 수 
- Top1: kdic-www-sp-dpstrprot-DpsmIbamtAplyProc-selectScrn#00  preview: 01 부보금융회사 보험사고 발생 열기 1종 보험사고 금융회사의 재무상황 악화 등으로 인해 예금의 지급이 정지된 경우 2종 보험

### QID 99 · 예금보험금 안내 · yesom · rank=없음
- 질문: 인터넷 신청방법
- GT문서: kdic-www-sp-dpstrprot-DpsmIbamtAplyProc-selectScrn  (GT청크 2개: kdic-www-sp-dpstrprot-DpsmIbamtAplyProc-selectScrn#00;kdic-www-sp-dpstrprot-DpsmIbamtAplyProc-selectScrn#01)
- GT preview: 01 부보금융회사 보험사고 발생 열기 1종 보험사고 금융회사의 재무상황 악화 등으로 인해 예금의 지급이 정지된 경우 2종 보험사고 금융회사가 인 · 허가 취소, 
- Top1: kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00  preview: 신청방법 온라인 신청 사이트 : fins.kdic.or.kr (상단 아이콘 클릭 시 사이트 연결) 접속방법 : PC (모바일은

### QID 101 · 착오송금 반환 신청 · yesom · rank=4
- 질문: 착오송금반환 신청 서류
- GT문서: kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn;kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn  (GT청크 1개: kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00)
- GT preview: 신청방법 온라인 신청 사이트 : fins.kdic.or.kr (상단 아이콘 클릭 시 사이트 연결) 접속방법 : PC (모바일은 추후 지원 예정) 준비물 : 공동인
- Top1: kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00  preview: 착오송금반환지원 절차 ( 착오송금인-예금보험공사-착오송금 수취인, 중앙행정기관 금융회사등 - 예금보험공사 - 법원 ) 1. 착

### QID 102 · 착오송금 반환 신청 · yesom · rank=없음
- 질문: 착오송금 이의제기 방문 신청
- GT문서: kdic-fins-ir-aplygudn-MsdrAddrsePossDcmntGudn-selectScrn  (GT청크 0개: )
- GT preview: (GT청크없음)
- Top1: kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00  preview: 착오송금반환지원 절차 ( 착오송금인-예금보험공사-착오송금 수취인, 중앙행정기관 금융회사등 - 예금보험공사 - 법원 ) 1. 착

### QID 103 · 착오송금 반환 신청 · yesom · rank=없음
- 질문: 착오송금 이의제기 인터넷 신청
- GT문서: kdic-fins-ir-aplygudn-MsdrAddrsePossDcmntGudn-selectScrn  (GT청크 0개: )
- GT preview: (GT청크없음)
- Top1: kdic-www-sp-kmrs-kmrsItrdAplyTrgt-selectScrn#00  preview: 신청 가능한 착오송금 금액 한도가 있나요? 신청 가능 한도는 착오송금 건당 5만원 이상 ~ 1억원 이하 입니다. 언제까지 신청

### QID 104 · 착오송금 반환 신청 · yesom · rank=없음
- 질문: 착오송금수취인 이체수수료환급 방문 신청
- GT문서: kdic-fins-ir-aplygudn-MsdrAddrsePossDcmntGudn-selectScrn  (GT청크 0개: )
- GT preview: (GT청크없음)
- Top1: kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00  preview: 착오송금반환지원 절차 ( 착오송금인-예금보험공사-착오송금 수취인, 중앙행정기관 금융회사등 - 예금보험공사 - 법원 ) 1. 착

### QID 105 · 착오송금 반환 신청 · yesom · rank=없음
- 질문: 착오송금수취인 이체수수료환급 인터넷 신청
- GT문서: kdic-fins-ir-aplygudn-MsdrAddrsePossDcmntGudn-selectScrn  (GT청크 0개: )
- GT preview: (GT청크없음)
- Top1: kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00  preview: 신청방법 온라인 신청 사이트 : fins.kdic.or.kr (상단 아이콘 클릭 시 사이트 연결) 접속방법 : PC (모바일은

### QID 106 · 예금보험금 안내 · yesom · rank=4
- 질문: 국외거주 또는 유학생 신청서류 (보험금신청서류)
- GT문서: kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn;kdic-fins-cm-bbs-selectFaqNramtAply  (GT청크 4개: kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn#00;kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn#01;kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn#02)
- GT preview: 01 예금자 본인이 찾을 경우 열기 예금자 본인의 확인 증명 주민등록증, 경로우대증, 운전면허증, 여권 등 공공기관에서 발행한 사진이 들어간 본인임을 확인할 수 
- Top1: kdic-www-rb-lbltajmt-LbltAjmtSprtLbltAjmtSyst-selectScrn#01  preview: 주민등록 등ㆍ초본 및 신분증(주민등록증, 운전면허증) 소득증명서류(급여명세서, 근로소득원천징수영수증 등) 재산증명서류(부동산등

### QID 107 · 착오송금 반환 신청 · yesom · rank=없음
- 질문: 국외거주 또는 유학생 신청서류 (착오송금반환 신청 서류)
- GT문서: kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn  (GT청크 0개: )
- GT preview: (GT청크없음)
- Top1: kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00  preview: 신청방법 온라인 신청 사이트 : fins.kdic.or.kr (상단 아이콘 클릭 시 사이트 연결) 접속방법 : PC (모바일은

### QID 109 · 착오송금 반환 신청 · yesom · rank=없음
- 질문: 군복무자 신청서류 (착오송금반환 신청 서류)
- GT문서: kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn  (GT청크 0개: )
- GT preview: (GT청크없음)
- Top1: kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00  preview: 착오송금반환지원 절차 ( 착오송금인-예금보험공사-착오송금 수취인, 중앙행정기관 금융회사등 - 예금보험공사 - 법원 ) 1. 착

### QID 110 · 예금보험금 안내 · yesom · rank=8
- 질문: 대리인 신청서류 (보험금신청서류)
- GT문서: kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn;kdic-fins-cm-bbs-selectFaqNramtAply  (GT청크 4개: kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn#00;kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn#01;kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn#02)
- GT preview: 01 예금자 본인이 찾을 경우 열기 예금자 본인의 확인 증명 주민등록증, 경로우대증, 운전면허증, 여권 등 공공기관에서 발행한 사진이 들어간 본인임을 확인할 수 
- Top1: kdic-www-rb-lbltajmt-LbltAjmtSprtLbltAjmtSyst-selectScrn#01  preview: 주민등록 등ㆍ초본 및 신분증(주민등록증, 운전면허증) 소득증명서류(급여명세서, 근로소득원천징수영수증 등) 재산증명서류(부동산등

### QID 112 · 착오송금 반환 신청 · yesom · rank=없음
- 질문: 미성년자 신청서류 (착오송금반환 신청 서류)
- GT문서: kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn  (GT청크 0개: )
- GT preview: (GT청크없음)
- Top1: kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00  preview: 착오송금반환지원 절차 ( 착오송금인-예금보험공사-착오송금 수취인, 중앙행정기관 금융회사등 - 예금보험공사 - 법원 ) 1. 착

### QID 113 · 착오송금 반환 신청 · yesom · rank=없음
- 질문: 대리인방문 착오송금반환 신청서류
- GT문서: kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn  (GT청크 0개: )
- GT preview: (GT청크없음)
- Top1: kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00  preview: 착오송금반환지원 절차 ( 착오송금인-예금보험공사-착오송금 수취인, 중앙행정기관 금융회사등 - 예금보험공사 - 법원 ) 1. 착

### QID 114 · 착오송금 반환 신청 · yesom · rank=없음
- 질문: 본인방문 착오송금반환 신청서류
- GT문서: kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn  (GT청크 0개: )
- GT preview: (GT청크없음)
- Top1: kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00  preview: 신청방법 온라인 신청 사이트 : fins.kdic.or.kr (상단 아이콘 클릭 시 사이트 연결) 접속방법 : PC (모바일은

### QID 115 · 예금보험금 안내 · yesom · rank=없음
- 질문: 법인 및 단체 신청서류 (보험금신청서류)
- GT문서: kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn;kdic-fins-cm-bbs-selectFaqNramtAply  (GT청크 4개: kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn#00;kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn#01;kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn#02)
- GT preview: 01 예금자 본인이 찾을 경우 열기 예금자 본인의 확인 증명 주민등록증, 경로우대증, 운전면허증, 여권 등 공공기관에서 발행한 사진이 들어간 본인임을 확인할 수 
- Top1: kdic-www-sp-dpstrprot-ProtSystFaq-selectScrn#12  preview: 질문 법인의 예금도 보호되나요? 답변 네. 기업 등 법인의 예금도 개인예금과 마찬가지로 법인별 1억원까지 보호됩니다. 다만, 

### QID 116 · 착오송금 반환 신청 · yesom · rank=없음
- 질문: 법인 및 단체 신청서류 (착오송금반환 신청 서류)
- GT문서: kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn  (GT청크 0개: )
- GT preview: (GT청크없음)
- Top1: kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00  preview: 착오송금반환지원 절차 ( 착오송금인-예금보험공사-착오송금 수취인, 중앙행정기관 금융회사등 - 예금보험공사 - 법원 ) 1. 착

### QID 120 · 예금자보호제도 · yesom · rank=4
- 질문: 보호 금융상품 - 종합금융회사
- GT문서: kdic-www-sp-dpstrprot-selectProtSystProtTrgtPrdctSumr  (GT청크 10개: kdic-www-sp-dpstrprot-selectProtSystProtTrgtPrdctSumr#00;kdic-www-sp-dpstrprot-selectProtSystProtTrgtPrdctSumr#01;kdic-www-sp-dpstrprot-selectProtSystProtTrgtPrdctSumr#02)
- GT preview: 예금보험공사는 예금보험 가입 금융회사가 취급하는 '예금' 등 만을 보호합니다. 그런데 여기서 꼭 알아두어야 할 점은 모든 금융상품이 보호대상 '예금' 등에 해당하
- Top1: kdic-www-sp-dpstrprot-ProtSystFaq-selectScrn#03  preview: 질문 어떤 금융상품이 보호되나요? 답변 ☞ 예금보험공사 홈페이지 > 제도·정책 > 예금자보호제도 > 보호대상 > 금융상품 보호

### QID 124 · 착오송금 반환 신청 · yesom · rank=없음
- 질문: 예금자 본인 신청서류 (착오송금반환 신청 서류)
- GT문서: kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn  (GT청크 0개: )
- GT preview: (GT청크없음)
- Top1: kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00  preview: 신청방법 온라인 신청 사이트 : fins.kdic.or.kr (상단 아이콘 클릭 시 사이트 연결) 접속방법 : PC (모바일은

### QID 125 · 착오송금 반환 신청 · yesom · rank=없음
- 질문: 비법인단체 신청서류
- GT문서: kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn  (GT청크 0개: )
- GT preview: (GT청크없음)
- Top1: kdic-www-rb-lbltajmt-LbltAjmtSprtLbltAjmtSyst-selectScrn#01  preview: 주민등록 등ㆍ초본 및 신분증(주민등록증, 운전면허증) 소득증명서류(급여명세서, 근로소득원천징수영수증 등) 재산증명서류(부동산등

### QID 131 · 예금보험금 안내 · yesom · rank=6
- 질문: 사망 예금자 신청서류 (보험금신청서류)
- GT문서: kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn;kdic-fins-cm-bbs-selectFaqNramtAply  (GT청크 4개: kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn#00;kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn#01;kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn#02)
- GT preview: 01 예금자 본인이 찾을 경우 열기 예금자 본인의 확인 증명 주민등록증, 경로우대증, 운전면허증, 여권 등 공공기관에서 발행한 사진이 들어간 본인임을 확인할 수 
- Top1: kdic-www-sp-dpstrprot-ProtSystHrpeHistInq-selectScrn#01  preview: 센터 민원실에서도 접수 가능(단,사망일이 속한 달의 말일로부터 6개월 이내에만 신청이 가능) 자세한 사항은 금융감독원 홈페이지

### QID 132 · 착오송금 반환 신청 · yesom · rank=없음
- 질문: 대리인 인터넷 신청서류
- GT문서: kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn  (GT청크 0개: )
- GT preview: (GT청크없음)
- Top1: kdic-www-sp-sprtfund-SprtFndDebtDlngAplyGudn-selectScrn#00  preview: 예금보험공사에서 관리하는 파산금융회사에 대한 부채증명원/금융거래정보 발급을 도와드리는 서비스 입니다. 신청대상 파산금융회사에 

### QID 133 · 착오송금 반환 신청 · yesom · rank=없음
- 질문: 본인 인터넷 신청서류
- GT문서: kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn  (GT청크 0개: )
- GT preview: (GT청크없음)
- Top1: kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00  preview: 신청방법 온라인 신청 사이트 : fins.kdic.or.kr (상단 아이콘 클릭 시 사이트 연결) 접속방법 : PC (모바일은

### QID 136 · 착오송금 반환 신청 · yesom · rank=없음
- 질문: 방문 국외거주 착오송금 서류
- GT문서: kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn  (GT청크 0개: )
- GT preview: (GT청크없음)
- Top1: kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00  preview: 착오송금반환지원 절차 ( 착오송금인-예금보험공사-착오송금 수취인, 중앙행정기관 금융회사등 - 예금보험공사 - 법원 ) 1. 착

### QID 137 · 착오송금 반환 신청 · yesom · rank=없음
- 질문: 방문 군복무 착오송금 서류
- GT문서: kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn  (GT청크 0개: )
- GT preview: (GT청크없음)
- Top1: kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn#02  preview: 의서(양식에 구애받지 않고 동의한 사실이 나타나면 됨)를 받으면 예외적으로 방문없이 신청이 가능하며, 추후 동 각서나 동의서를

### QID 138 · 착오송금 반환 신청 · yesom · rank=없음
- 질문: 방문 미성년자 착오송금 서류
- GT문서: kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn  (GT청크 0개: )
- GT preview: (GT청크없음)
- Top1: kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00  preview: 착오송금반환지원 절차 ( 착오송금인-예금보험공사-착오송금 수취인, 중앙행정기관 금융회사등 - 예금보험공사 - 법원 ) 1. 착

### QID 139 · 착오송금 반환 신청 · yesom · rank=없음
- 질문: 법인 및 단체 대표 방문 신청서류
- GT문서: kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn  (GT청크 0개: )
- GT preview: (GT청크없음)
- Top1: kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00  preview: 신청방법 온라인 신청 사이트 : fins.kdic.or.kr (상단 아이콘 클릭 시 사이트 연결) 접속방법 : PC (모바일은

### QID 140 · 착오송금 반환 신청 · yesom · rank=없음
- 질문: 법인 및 단체 직원 방문 신청서류
- GT문서: kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn  (GT청크 0개: )
- GT preview: (GT청크없음)
- Top1: kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00  preview: 신청방법 온라인 신청 사이트 : fins.kdic.or.kr (상단 아이콘 클릭 시 사이트 연결) 접속방법 : PC (모바일은

### QID 141 · 착오송금 반환 신청 · yesom · rank=없음
- 질문: 비법인단체 대표 방문 신청서류
- GT문서: kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn  (GT청크 0개: )
- GT preview: (GT청크없음)
- Top1: kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00  preview: 신청방법 온라인 신청 사이트 : fins.kdic.or.kr (상단 아이콘 클릭 시 사이트 연결) 접속방법 : PC (모바일은

### QID 142 · 착오송금 반환 신청 · yesom · rank=없음
- 질문: 비법인단체 직원 방문 신청서류
- GT문서: kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn  (GT청크 0개: )
- GT preview: (GT청크없음)
- Top1: kdic-www-sp-sprtfund-SprtFndCncmDclrGudn-selectScrn#03  preview: 신고방법 상담전화(이메일) : 02-758-0102~04 ( cpreport@kdic.or.kr ) (필요시 공사 직원이 신고

### QID 144 · 착오송금 반환 신청 · yesom · rank=없음
- 질문: 인터넷 국외거주 착오송금 서류
- GT문서: kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn  (GT청크 0개: )
- GT preview: (GT청크없음)
- Top1: kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00  preview: 착오송금반환지원 절차 ( 착오송금인-예금보험공사-착오송금 수취인, 중앙행정기관 금융회사등 - 예금보험공사 - 법원 ) 1. 착

### QID 145 · 착오송금 반환 신청 · yesom · rank=없음
- 질문: 인터넷 군복무 착오송금 서류
- GT문서: kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn  (GT청크 0개: )
- GT preview: (GT청크없음)
- Top1: kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00  preview: 착오송금반환지원 절차 ( 착오송금인-예금보험공사-착오송금 수취인, 중앙행정기관 금융회사등 - 예금보험공사 - 법원 ) 1. 착

### QID 146 · 착오송금 반환 신청 · yesom · rank=없음
- 질문: 인터넷 미성년자 착오송금 서류
- GT문서: kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn  (GT청크 0개: )
- GT preview: (GT청크없음)
- Top1: kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00  preview: 신청방법 온라인 신청 사이트 : fins.kdic.or.kr (상단 아이콘 클릭 시 사이트 연결) 접속방법 : PC (모바일은

### QID 147 · 착오송금 반환 신청 · yesom · rank=없음
- 질문: 인터넷 법인 대표 착오송금 서류
- GT문서: kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn  (GT청크 0개: )
- GT preview: (GT청크없음)
- Top1: kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00  preview: 신청방법 온라인 신청 사이트 : fins.kdic.or.kr (상단 아이콘 클릭 시 사이트 연결) 접속방법 : PC (모바일은

### QID 148 · 착오송금 반환 신청 · yesom · rank=없음
- 질문: 인터넷 법인 직원 착오송금 서류
- GT문서: kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn  (GT청크 0개: )
- GT preview: (GT청크없음)
- Top1: kdic-www-sp-kmrs-kmrsItrdProc-selectScrn#00  preview: 착오송금반환지원 절차 ( 착오송금인-예금보험공사-착오송금 수취인, 중앙행정기관 금융회사등 - 예금보험공사 - 법원 ) 1. 착

### QID 149 · 착오송금 반환 신청 · yesom · rank=없음
- 질문: 인터넷 비법인 대표 착오송금 서류
- GT문서: kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn  (GT청크 0개: )
- GT preview: (GT청크없음)
- Top1: kdic-www-sp-kmrs-kmrsItrd-selectScrn#00  preview: 제도 소개 안내영상 영상내용입니다. 제도 소개 안내영상입니다. 잘못 보낸 돈 되찾기 서비스란 착오송금인이 실수로 잘못 보낸 돈

### QID 150 · 착오송금 반환 신청 · yesom · rank=없음
- 질문: 인터넷 비법인 직원 착오송금 서류
- GT문서: kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn  (GT청크 0개: )
- GT preview: (GT청크없음)
- Top1: kdic-www-sp-kmrs-kmrsItrdAplyMthd-selectScrn#00  preview: 신청방법 온라인 신청 사이트 : fins.kdic.or.kr (상단 아이콘 클릭 시 사이트 연결) 접속방법 : PC (모바일은

