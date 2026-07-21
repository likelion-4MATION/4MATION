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

첨부(PDF/HWP 등) 처리 — 정적 크롤링 범위 내에서 가능한 만큼 태깅:
  실사 결과 두 가지 패턴이 섞여 있음.
  1) www.kdic.or.kr 자료실/보도자료류: <a href="...pdf/hwp">  → 절대 URL을 그대로 확보 가능
     (link_type="direct", url 채워짐).
  2) fins.kdic.or.kr 포털(구비서류안내 등): <button class="btnIco icoHwp/icoPdf"
     onclick="gfn_downloadFile(encId, encName)">  → href가 아예 없고, 실제 다운로드는
     POST /api/cm/file/downloadFile.do 에 세션 종속(추정) 암호화 파라미터가 필요.
     정적 HTML만으로는 절대경로 URL을 만들 수 없어 url=None으로 두고
     link_type="onclick_dynamic" 태깅, 대신 존재 여부(name/file_type/doc_kind)와
     안내 페이지 자체 URL을 fallback_url로 남긴다 (답변 시 "이 페이지에서 받으세요" 용도).
     raw_onclick은 추후 동적 재수집(P2+) 대비 원본 보존용.
  doc_kind는 첨부가 속한 표의 헤더 텍스트(예: '관련 서식')를 규칙 매칭해서 부여.
  표 밖에 있는 느슨한 첨부 링크는 doc_kind="기타"로 처리.
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
# 주의: attachments 추출은 이 제거보다 먼저 수행해야 함 (button 태그가 여기서 날아감)
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

ATTACH_RE = re.compile(r"\.(hwp|hwpx|pdf|xlsx?|docx?|pptx?|zip|txt|csv)(\?|$)", re.I)

# 표 헤더 텍스트 → doc_kind 규칙 매핑 (우선순위 순서대로 첫 매치 채택)
DOC_KIND_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"서식|양식"), "양식"),
    (re.compile(r"안내|자료|첨부"), "안내자료"),
]

# button/a class="btnIco icoXxx" → file_type 매핑에 쓰는 패턴
ICO_CLASS_RE = re.compile(r"^ico([A-Za-z]+)$")


def collapse(s: str) -> str:
    return re.sub(r"[ \t ]+", " ", s).strip()


def infer_doc_kind(header_text: str) -> str:
    if not header_text:
        return "기타"
    for pattern, kind in DOC_KIND_RULES:
        if pattern.search(header_text):
            return kind
    return "기타"


def get_table_headers(table) -> list[str]:
    """표 헤더 텍스트 목록 (컬럼 인덱스 → doc_kind 추론용)."""
    header_row = None
    thead = table.find("thead")
    if thead:
        header_row = thead.find("tr")
    if header_row is None:
        first_tr = table.find("tr")
        if first_tr and first_tr.find_all("th"):
            header_row = first_tr
    if header_row is None:
        return []
    return [collapse(th.get_text(" ")) for th in header_row.find_all(["th", "td"])]


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


def _direct_attachment(a, doc_kind: str, base_url: str) -> dict | None:
    href = a.get("href", "").strip()
    if not href or href.startswith("javascript:"):
        return None
    if "/cm/file/" not in href and not ATTACH_RE.search(href):
        return None
    m = ATTACH_RE.search(href)
    file_type = m.group(1).lower() if m else "other"
    abs_url = urljoin(base_url, href)
    return {
        "name": collapse(a.get_text(" ")) or href.rsplit("/", 1)[-1],
        "file_type": file_type,
        "doc_kind": doc_kind,
        "url": abs_url,
        "link_type": "direct",
        "fallback_url": base_url,
        "raw_onclick": None,
    }


def _dynamic_attachment(btn, doc_kind: str, base_url: str) -> dict | None:
    onclick = btn.get("onclick", "") or ""
    if "gfn_downloadFile" not in onclick:
        return None
    file_type = "other"
    for c in btn.get("class", []):
        m = ICO_CLASS_RE.match(c)
        if m:
            file_type = m.group(1).lower()
            break
    return {
        "name": collapse(btn.get_text(" ")),
        "file_type": file_type,
        "doc_kind": doc_kind,
        "url": None,
        "link_type": "onclick_dynamic",
        "fallback_url": base_url,
        "raw_onclick": onclick,
    }


def extract_attachments(container, base_url: str) -> list[dict]:
    """첨부 목록 보존 + 정적 크롤링 범위 내에서 가능한 메타 태깅.

    반환 스키마 (item당):
      name, file_type, doc_kind, url, link_type("direct"|"onclick_dynamic"),
      fallback_url(항상 채움 — 안내 페이지 자체 URL), raw_onclick(dynamic만)
    """
    out: list[dict] = []
    seen: set[tuple] = set()

    def add(item: dict | None, dedup_key: tuple) -> None:
        if item is None or dedup_key in seen:
            return
        seen.add(dedup_key)
        out.append(item)

    for table in container.find_all("table"):
        headers = get_table_headers(table)
        for tr in table.find_all("tr"):
            cells = tr.find_all(["th", "td"])
            for idx, cell in enumerate(cells):
                header_text = headers[idx] if idx < len(headers) else ""
                doc_kind = infer_doc_kind(header_text)

                for a in cell.find_all("a", href=True):
                    item = _direct_attachment(a, doc_kind, base_url)
                    if item:
                        add(item, ("direct", item["url"]))

                for btn in cell.select("button.btnIco, a.btnIco"):
                    item = _dynamic_attachment(btn, doc_kind, base_url)
                    if item:
                        add(item, ("dynamic", item["name"], item["raw_onclick"]))

    # 표 밖 느슨한 첨부 링크 (자료실/보도자료 목록형 페이지 등)
    for a in container.find_all("a", href=True):
        if a.find_parent("table"):
            continue
        item = _direct_attachment(a, "기타", base_url)
        if item:
            add(item, ("direct", item["url"]))

    for btn in container.select("button.btnIco, a.btnIco"):
        if btn.find_parent("table"):
            continue
        item = _dynamic_attachment(btn, "기타", base_url)
        if item:
            add(item, ("dynamic", item["name"], item["raw_onclick"]))

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
    base_url = meta.get("final_url") or meta.get("source_url") or ""

    if container is None:
        # 컨테이너 미탐지 — 본문 유실 위험. 빈 텍스트로 표시하고 호출측에서 경고.
        return {"doc_id": doc_id, "text": "", "attachments": [],
                "has_attachments": False, "attachment_count": 0,
                "breadcrumb": breadcrumb, "_no_container": True}

    # 첨부는 노이즈 제거 전에 수집 (기능부 안에 서식 다운로드가 있을 수 있음,
    # button 태그는 NOISE_SELECTORS에서 통째로 decompose되므로 반드시 먼저 실행)
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
        "has_attachments": len(attachments) > 0,
        "attachment_count": len(attachments),
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
        ok += 1

    print(f"파싱 {ok}건 → {out_dir}/")
    if warn:
        print("경고:")
        for w in warn:
            print("  -", w)


if __name__ == "__main__":
    main()
