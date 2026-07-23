# 변경사항 정리 — meta-doc 브랜치 (2026-07-23)

> origin/meta-doc 최신 커밋(`3310acb 첨부문서 메타데이터 추가`) 이후, 로컬에서 추가로 작업한 내용을 정리한 문서.
> 목적: onclick_dynamic 첨부(구비서류 hwp/pdf 등)를 "안내 페이지 URL만 남기는" 기존 방식에서 **실제 파일을 다운로드해 로컬 스토리지에 저장하고, parsed 첨부 메타에 1:1 연결**하는 단계까지 확장.

## 변경 파일 요약

| 파일 | 상태 | 내용 |
|---|---|---|
| `crawler/parser.py` | 수정 | onclick 첨부에서 다운로드 토큰(enc_real/enc_temp) 추출·보존, anchor_text div 케이스 보강, dedup 키 강화 |
| `crawler/fetch_attachments.py` | **신규** | 토큰으로 실파일 다운로드 → `data/files/{doc_id}/`에 저장, `manifest.json` 생성 |
| `crawler/link_files.py` | **신규** | `manifest.json`과 `data/parsed/*.json`을 토큰 기준으로 조인해 첨부 메타에 로컬 파일 정보 기록 |
| `crawler/data/chunks.jsonl` | 수정 | 위 파이프라인 재실행 결과가 반영되어 재생성(첨부 있는 6개 문서의 16개 청크 갱신) |
| `crawler/data/files/` | **신규 데이터** | 실다운로드된 첨부 파일 44개 + `manifest.json` (4.1MB) |
| `crawler/CHANGELOG_20260723_meta-doc.md` | **신규** | 본 문서 |

## 상세 변경 내용

### 1. `parser.py` — 다운로드 토큰 추출·보존

- 기존: `onclick="gfn_downloadFile(...)"` 첨부는 실파일 URL을 만들 수 없다고 보고, 첨부가 있는 **안내 페이지 URL**만 `url` 필드에 채우고 끝냈음.
- 실사 결과 `gfn_downloadFile('encId', 'encName')`의 두 인자(enc_real/enc_temp)가 **세션 종속이 아니라 페이지 렌더마다 고정값**임을 확인 → 이를 그대로 POST 바디로 되돌려 보내면 실파일을 받을 수 있음(`fetch_attachments.py`가 이 사실을 이용).
- 변경 사항:
  - `ONCLICK_RE` 정규식 신설, `_dynamic_attachment()`가 `enc_real`/`enc_temp`를 attachments 항목에 추가로 기록(파서 자체는 여전히 raw HTML만 읽고 네트워크 요청은 하지 않음 — 결정론성 유지).
  - `extract_attachments()`의 dedup 키를 `(name, anchor_text)`에서 `(name, anchor_text, file_type, enc_real, enc_temp)`로 강화. 이유: 동일 문서명이 한 페이지 내 여러 위치(본인/대리인 탭 등)에 노출될 때 실제로는 서로 다른 파일인데 표시 텍스트가 같아 dedup 키가 충돌하는 사례가 실사에서 발견됨(`SprtFndDebtDlngAplyGudn` 페이지의 "금융거래정보 발급신청서" 본인용/대리인용).
  - `_anchor_text()`에 `<div>` 조상 기반 폴백 추가 — `<li>`/`<tr>` 문맥이 없는 카드형 레이아웃(부보금융회사 목록 엑셀/한글 다운로드 등)에서도 문서명을 회수하되, 결과가 200자를 넘으면(엉뚱한 상위 div까지 삼킨 경우) 빈 문자열로 버림.
  - 첨부 버튼 셀렉터를 `button.btnIco, a.btnIco` 클래스 매칭에서 `onclick`에 `gfn_downloadFile` 포함 여부 판정으로 통일.

### 2. `fetch_attachments.py` (신규 스크립트)

- `data/parsed/*.json`에서 `has_attachments=true`이고 `link_type="onclick_dynamic"`인 첨부만 골라, 사이트별 다운로드 엔드포인트로 실제 파일을 받아온다.
  - `www.kdic.or.kr` → `POST /cm/file/downloadFile.do`
  - `fins.kdic.or.kr` → `POST /api/cm/file/downloadFile.do`
  - 바디: `{"encAtchFilePathNm": enc_real, "encOrgnlFileNm": enc_temp}`
- 응답의 `Content-Disposition` 헤더에서 원본 파일명을 복원해 `data/files/{doc_id}/{원본파일명}`으로 저장.
- 같은 문서가 페이지 내 여러 곳에 동일 토큰으로 중복 노출되는 경우(doc_id, enc_real, enc_temp) 캐시로 재요청을 방지.
- 결과를 `data/files/manifest.json`에 기록(문서별 doc_id, 로컬 저장 경로, 파일 크기, sha256, 성공/실패 상태 등).
- 요청 간 `config.REQUEST_INTERVAL_SEC` + 지터로 지연을 둠(기존 크롤러 정책과 동일).

### 3. `link_files.py` (신규 스크립트)

- `data/files/manifest.json`(실다운로드 결과)과 `data/parsed/*.json`(페이지 단위 첨부 메타)을 **(doc_id, enc_real, enc_temp)** — 다운로드 토큰 자체 — 기준으로 조인.
- 매칭된 각 첨부 항목에 `local_path` · `orig_filename` · `file_size` · `sha256`을 추가 기록해 `data/parsed/*.json`에 되써넣음.
- 표시 텍스트(name/anchor_text) 대신 토큰으로 매칭하는 이유: 토큰이 파일의 실제 신원이라 오매칭 여지가 없음(파서 dedup 키 강화와 동일한 근거).
- `chunk.py`는 attachments를 그대로 복사해 청크에 싣기 때문에, 이 스크립트 이후 `chunk.py`를 재실행하면 청크 단위 attachments에도 `local_path`가 자동으로 반영됨.

### 4. `data/chunks.jsonl` 재생성

- 위 파이프라인(`parser.py` → `fetch_attachments.py` → `link_files.py` → `chunk.py`) 재실행 결과가 반영되어 16개 청크가 갱신됨(첨부가 있는 6개 문서 전부):
  - `kdic-fins-ir-aplygudn-MsdrAddrsePossDcmntGudn-selectScrn`
  - `kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn`
  - `kdic-fins-ir-aplygudn-MtrsVstRcptGudn-selectScrn`
  - `kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn`
  - `kdic-www-sp-dpstrprot-selectProtSystProtSumr`
  - `kdic-www-sp-sprtfund-SprtFndDebtDlngAplyGudn-selectScrn`
- 각 청크의 `attachments[]` 항목에 `enc_real`/`enc_temp`(토큰), `local_path`/`orig_filename`/`file_size`/`sha256`(로컬 파일 정보)이 새로 채워짐. 그 외 필드/청크 경계는 변경 없음.

### 5. `data/files/` — 실다운로드 산출물

- 총 46건 다운로드 시도, 실패 0건(`manifest.json` 기준). 디스크에는 44개 파일이 저장됨 — 차이 2건은 동일 문서가 한 페이지 안에서 중복 노출돼 토큰 캐시로 재사용된 것(신규 다운로드 없이 기존 경로만 재기록).
- 첨부가 존재하는 페이지는 크롤 대상 38페이지(필수 37 + 분석포함 1) 중 6개뿐이며, 그 6개 페이지 전부에서 정상 다운로드됨:

  | doc_id | 첨부 건수 | 필수 37건 목록 포함 |
  |---|---|---|
  | `kdic-fins-ir-aplygudn-MsdrAddrsePossDcmntGudn-selectScrn` | 4 | ✅ |
  | `kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn` | 22(캐시 재사용 2건 포함, 실파일 20) | ✅ |
  | `kdic-fins-ir-aplygudn-MtrsVstRcptGudn-selectScrn` | 2 | ✅ |
  | `kdic-www-sp-dpstrprot-DpsmIbamtAplyPossDcmnt-selectScrn` | 10 | ✅ |
  | `kdic-www-sp-dpstrprot-selectProtSystProtSumr` | 3 | ✅ |
  | `kdic-www-sp-sprtfund-SprtFndDebtDlngAplyGudn-selectScrn` | 5 | ❌ (분석포함으로 추가된 38번째 페이지) |

- 용량: 약 4.1MB.

## 파이프라인 실행 순서 (참고)

```
parser.py → fetch_attachments.py → link_files.py → chunk.py
```

## 이번 커밋에서 제외한 항목

작업 디렉토리에 있었지만 이번 meta-doc 변경과 무관해 커밋에서 제외:

- `exp/` — `exp/night1_report.md` 자체에 `feat/hcx-demo` 브랜치용 git 커밋 안내가 명시돼 있음(챗봇 하네스/라우팅 실험 산출물, 다른 브랜치 작업).
- `.claude/` — Claude Code 로컬 툴 설정(권한 등), 프로젝트 코드가 아님.

## 검증

- `link_files.py` 재현 계산: 첨부 46건 중 46건 전부 `local_path` 연결 완료, 미매칭 0건.
- `fetch_attachments.py` manifest: 성공 46 / 실패 0.
- 첨부가 수집된 6개 페이지 모두 크롤 대상 38페이지(`crawl_manifest.csv`) 범위 내(37 필수 + 1 분석포함).
