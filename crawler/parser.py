"""파서 v0 — 결정론적 BeautifulSoup 본문 추출. LLM 미사용 (동일 입력=동일 출력).

입력: run1/data/raw/*.html + data/meta/*.json (D0 산출)
출력: data/parsed/{doc_id}.json (doc_id · text · attachments · 메타 상속)

설계 근거(03 문서 + D1 DOM 정찰):
- KDIC 페이지는 텍스트의 90%+가 GNB 네비 노이즈 → 본문 컨테이너 `.contents`로 좁혀 잡는다.
  (#container는 브레드크럼/타이틀 포함, `.contents`가 실제 본문 — 32건 전부 1개씩 존재 확인)
- `.contents` 내부 크롬/기능부 제거: floatTop(글자크기·언어) · floatBottom(챗봇·상단이동)
  · btnBottomArea(조회/신청 바로가기 버튼) · script/style · form/input/button.
- 표는 값 유실 없이 행 텍스트("cell | cell")로 직렬화. 구조 미화(markdown)는 P2 몫이라 안 함.
- 브레드크럼은 `.location` 최상위 li 직계자식의 첫 링크만 (드롭다운 형제메뉴 무시).
- coverage=안내부 페이지(상속인 금융거래조회)는 조회 기능부(btnBottomArea) 제거로 안내부만 남김.

[meta-doc] 답변 시 문서·양식을 반환하기 위한 "문서 존재/링크" 메타데이터 태깅:
  - has_attachments: 이 페이지에 첨부(서식·양식·안내자료)가 있는지 여부.
  - attachments: [{name, url, file_type}, ...] — 기존 링크를 그대로 절대경로로 반환.
  탐지 조건을 두 가지 OR로 잡는다:
    1) href 자체에 파일 경로/확장자 패턴이 있는 경우 (기존 방식, /cm/file/ 또는 확장자).
    2) href엔 패턴이 없어도(예: javascript:void(0) 같은 JS 트리거 다운로드) 앵커
       텍스트 자체에 "위임장.hwp"처럼 파일 확장자가 노출된 경우.
  2)를 추가한 이유: 국내 공공기관 사이트는 fileDown.do?atchFileId=... 같은 확장자
  없는 서블릿형 다운로드를 흔히 쓰는데, 실제 크롤 데이터로 확인해보니(33건) href
  기준 탐지가 0건이었다. 실제 KDIC 다운로드 URL 패턴이 확정되면(find_file_links.py
  결과) FILE_URL_KEYWORDS를 그 패턴으로 좁혀 정확도를 올릴 것 — 지금은 놓치는 것보다
  넓게 잡는 쪽으로 설계.
  JS 트리거 다운로드(href="javascript:void(0)")는 실제 다운로드 URL을 href에서 알
  수 없다 — 이 경우 url 필드엔 href 원문(javascript:...)이 그대로 들어가고, onclick
  속성을 onclick 필드에 별도 보존해 사람이 나중에 실제 엔드포인트를 확인할 수 있게 한다.
"""

from __future__ import annotations

import glob
import hashlib
import json
import pathlib
import re
import sys
from urllib.parse import urljoin

from bs4 import BeautifulSoup, NavigableString

RAW_DIR = "data/raw"
META_DIR = "data/meta"
OUT_DIR = "data/parsed"

CONTENT_SELECTOR = ".contents"

# .contents 내부에서 제거할 크롬/기능부 (결정론적)
NOISE_SELECTORS = [
    "script", "style", "noscript",
    ".floatTop", ".floatBottom", ".btnBottomArea",
    "form", "input", "button",
]

# 안내부 페이지 — 조회/신청 기능부 제거, coverage=안내부.
# 상속인 조회는 ASSIGNMENT_D1 T1 지정, 부채증명원은 07-13 xlsx '포함(안내부)' 판정 편입분.
COVERAGE_ANNAE = {
    "kdic-www-sp-dpstrprot-ProtSystHrpeHistInq-selectScrn",      # 상속인 금융거래조회
    "kdic-www-sp-sprtfund-SprtFndDebtDlngAplyGudn-selectScrn",   # 부채증명원/금융거래정보신청
}

# [meta-doc] href 기반 탐지 — 기존 확장자 패턴 + 서블릿형 다운로드 키워드
FILE_EXT_RE = re.compile(r"\.(hwp|hwpx|pdf|xlsx?|docx?|pptx?|zip|txt|csv)(\?|$)", re.I)
FILE_URL_KEYWORDS = ("/cm/file/", "filedown", "atchfile", "atchFile", "download", "fileview")

# [meta-doc] href에 패턴이 없을 때 앵커 텍스트에서 확장자를 찾는 보조 탐지
FILE_EXT_IN_TEXT_RE = re.compile(r"\.(hwp|hwpx|pdf|xlsx?|docx?|pptx?|zip)\b", re.I)


def collapse(s: str) -> str:
    return re.sub(r"[ \t ]+", " ", s).strip()


def table_to_lines(table) -> str:
    """표를 값 유실 없이 행 텍스트로 직렬화 (미화 없음)."""
    lines = []
    cap = table.find("caption")
    if cap:
        t = collapse(cap.get_text(" "))
        if t:
            lines.append(t)
    for tr in table.find_all("tr"):
        cells = [collapse(c.get_text(" ")) for c in tr.find_all(["th", "td"])]
        cells = [c for c in cells if c]
        if cells:
            lines.append(" | ".join(cells))
    return "\n".join(lines)


def extract_breadcrumb(soup) -> list[str]:
    """`.location` 최상위 li 직계자식의 첫 링크만 취해 홈>…>현재 경로 구성."""
    loc = soup.select_one(".location")
    if not loc:
        return []
    top = loc.find(["ol", "ul"])
    if not top:
        return []
    out: list[str] = []
    for li in top.find_all("li", recursive=False):
        a = li.find("a")
        t = collapse((a.get_text(" ") if a else li.get_text(" ")))
        if t and t not in out:
            out.append(t)
    return out


def extract_attachments(container, base_url: str = "") -> list[dict]:
    """첨부(서식·양식·안내자료) 링크를 "문서 존재/링크" 메타데이터로 태깅한다.

    반환 각 항목: {name, url, file_type, onclick}
      - url: href가 실제 경로면 base_url 기준 절대경로로 정규화해서 그대로 반환.
             href가 javascript:... 같은 JS 트리거면 원문 그대로 두고 onclick에
             실제 핸들러를 남긴다 (사람이 실제 다운로드 엔드포인트를 확인해야 함).
      - file_type: href 또는 앵커 텍스트에서 찾은 확장자.
    """
    out, seen = [], set()
    for a in container.find_all("a", href=True):
        href = a["href"].strip()
        name = collapse(a.get_text(" "))

        href_ext = FILE_EXT_RE.search(href)
        href_kw = any(k.lower() in href.lower() for k in FILE_URL_KEYWORDS)
        text_ext = FILE_EXT_IN_TEXT_RE.search(name) if name else None

        if not (href_ext or href_kw or text_ext):
            continue

        is_js_href = href.lower().startswith("javascript:") or href == "#"
        key = f"{href}|{name}" if is_js_href else href
        if key in seen:
            continue
        seen.add(key)

        ext_match = href_ext or text_ext
        file_type = ext_match.group(1).lower() if ext_match else ""
        url = href if is_js_href else (urljoin(base_url, href) if base_url else href)

        out.append({
            "name": name or href.rsplit("/", 1)[-1],
            "url": url,
            "file_type": file_type,
            "onclick": a.get("onclick", "") if is_js_href else "",
        })
    return out


def serialize_text(container) -> str:
    """노이즈 제거된 컨테이너를 라인 구조 텍스트로 직렬화 (표는 행 텍스트로 치환)."""
    for table in container.find_all("table"):
        table.replace_with(NavigableString("\n" + table_to_lines(table) + "\n"))
    raw = container.get_text("\n")
    lines = [collapse(l) for l in raw.split("\n")]
    lines = [l for l in lines if l]
    return "\n".join(lines)


def parse_one(doc_id: str, html: str, meta: dict) -> dict:
    soup = BeautifulSoup(html, "lxml")
    breadcrumb = extract_breadcrumb(soup)

    container = soup.select_one(CONTENT_SELECTOR)
    if container is None:
        # 컨테이너 미탐지 — 본문 유실 위험. 빈 텍스트로 표시하고 호출측에서 경고.
        return {"doc_id": doc_id, "text": "", "attachments": [], "has_attachments": False,
                "breadcrumb": breadcrumb, "_no_container": True}

    # [meta-doc] 첨부 url 정규화 기준 — final_url 우선(리다이렉트 반영), 없으면 source_url
    base_url = meta.get("final_url") or meta.get("source_url", "")

    # 첨부는 노이즈 제거 전에 수집 (기능부 안에 서식 다운로드가 있을 수 있음)
    attachments = extract_attachments(container, base_url)

    for sel in NOISE_SELECTORS:
        for n in container.select(sel):
            n.decompose()

    text = serialize_text(container)

    site = "www" if "-www-" in doc_id else ("fins" if "-fins-" in doc_id else "")
    coverage = "안내부" if doc_id in COVERAGE_ANNAE else "전체"
    page_title = breadcrumb[-1] if breadcrumb else collapse(meta.get("title", ""))
    sub_category = " > ".join(breadcrumb[1:]) if len(breadcrumb) > 1 else ""

    return {
        "doc_id": doc_id,
        "source_url": meta.get("source_url", ""),
        "final_url": meta.get("final_url", ""),
        "site": site,
        "business_function": meta.get("business_function", ""),
        "sub_category": sub_category,
        "page_type": meta.get("page_type", ""),
        "coverage": coverage,
        "variant": meta.get("variant", ""),
        "page_title": page_title,
        "breadcrumb": breadcrumb,
        "title_raw": collapse(meta.get("title", "")),
        "text": text,
        "text_len": len(text),
        "attachments": attachments,
        "has_attachments": bool(attachments),
        "robots_status": meta.get("robots_status", ""),
        "collected_at": meta.get("collected_at", ""),
        "raw_sha256": meta.get("raw_sha256", ""),
        "parsed_text_sha256": hashlib.sha256(text.encode()).hexdigest(),
    }


def main() -> None:
    src_root = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(".")
    raw_glob = sorted((src_root / RAW_DIR).glob("*.html"))
    if not raw_glob:
        sys.exit(f"raw HTML 없음: {src_root / RAW_DIR}")
    out_dir = pathlib.Path(OUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    ok, warn = 0, []
    attach_docs = 0
    for p in raw_glob:
        doc_id = p.stem
        meta_path = pathlib.Path(META_DIR) / f"{doc_id}.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        html = p.read_text(encoding="utf-8", errors="replace")
        rec = parse_one(doc_id, html, meta)
        (out_dir / f"{doc_id}.json").write_text(
            json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
        if rec.get("_no_container"):
            warn.append(f"{doc_id}: 본문 컨테이너 미탐지")
        elif rec["text_len"] < 120:
            warn.append(f"{doc_id}: 본문 {rec['text_len']}자 (얇음 — 이미지/영상 위주 의심)")
        if rec.get("has_attachments"):
            attach_docs += 1
        ok += 1

    print(f"파싱 {ok}건 → {out_dir}/")
    print(f"  첨부 보유 문서: {attach_docs}건")
    if warn:
        print("경고:")
        for w in warn:
            print("  -", w)


if __name__ == "__main__":
    main()
