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
- 첨부(PDF/HWP 등)는 파싱하지 않고 attachments 목록만 보존.
"""

from __future__ import annotations

import glob
import hashlib
import json
import pathlib
import re
import sys

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
# 2026-07-23 실험 후 폐기: ".tabArea > ul"(송금인/수취인 탭 전환 메뉴 라벨) 제거를
# 시도했으나 400건 재평가 결과 착오송금 도메인이 오히려 hit@3 .847→.833(−0.014·
# 미적중 11→12건)로 악화(신규 미적중 2건 vs 신규 개선 1건, 순손실). 진단(형제 탭
# 라벨이 본문 첫머리에서 party 구분 신호를 오염시킨다는 구조적 근거)은 유효했으나
# BM25 코퍼스 전역 통계 변화 등 부작용이 더 커 net 이득 없음 — 롤백. DECISIONS.md 참고.

# 안내부 페이지 — 조회/신청 기능부 제거, coverage=안내부.
# 상속인 조회는 ASSIGNMENT_D1 T1 지정, 부채증명원은 07-13 xlsx '포함(안내부)' 판정 편입분.
COVERAGE_ANNAE = {
    "kdic-www-sp-dpstrprot-ProtSystHrpeHistInq-selectScrn",      # 상속인 금융거래조회
    "kdic-www-sp-sprtfund-SprtFndDebtDlngAplyGudn-selectScrn",   # 부채증명원/금융거래정보신청
}

ATTACH_RE = re.compile(r"\.(hwp|hwpx|pdf|xlsx?|docx?|pptx?|zip|txt|csv)(\?|$)", re.I)


def collapse(s: str) -> str:
    return re.sub(r"[ \t ]+", " ", s).strip()


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


def extract_attachments(container) -> list[dict]:
    """첨부 링크 목록만 보존 (파싱 안 함). /cm/file/ 또는 문서 확장자."""
    out, seen = [], set()
    for a in container.find_all("a", href=True):
        href = a["href"].strip()
        if "/cm/file/" in href or ATTACH_RE.search(href):
            if href in seen:
                continue
            seen.add(href)
            name = collapse(a.get_text(" ")) or href.rsplit("/", 1)[-1]
            out.append({"name": name, "url": href})
    return out


def serialize_text(container) -> str:
    """노이즈 제거된 컨테이너를 라인 구조 텍스트로 직렬화 (표는 행 텍스트로 치환)."""
    for table in container.find_all("table"):
        table.replace_with(NavigableString("\n" + table_to_lines(table) + "\n"))
    raw = container.get_text("\n")
    lines = [collapse(l) for l in raw.split("\n")]
    lines = [l for l in lines if l]
    return "\n".join(lines)


def parse_html(html: str, selector: str = CONTENT_SELECTOR) -> BeautifulSoup:
    """lxml 우선 파싱, `selector` 미탐지 시 html.parser로 재시도.

    일부 fins.kdic.or.kr 응답은 본인인증 위젯 스니펫이 <html>/<body>째로
    중복 포함돼 온다(malformed). HTML5 스펙(WHATWG §13.2.6.4.7 "in body")은
    이런 중복 body를 만나면 기존 body에 병합해 계속 파싱하도록 정의하는데,
    Windows용 lxml 휠은 libxml2 2.11에 고정돼 있어(PyPI 최신판도 동일) 이
    복구를 못 하고 두 번째(진짜) body를 통째로 버린다 — libxml2 2.14+
    (macOS/manylinux 휠 기본값)부터 HTML5 준수 토크나이저로 정상 복구됨.
    html.parser(표준 라이브러리)는 OS/휠 버전과 무관하게 이 복구를 해낸다.
    """
    soup = BeautifulSoup(html, "lxml")
    if soup.select_one(selector) is None:
        alt = BeautifulSoup(html, "html.parser")
        if alt.select_one(selector) is not None:
            return alt
    return soup


def parse_one(doc_id: str, html: str, meta: dict) -> dict:
    soup = parse_html(html)
    breadcrumb = extract_breadcrumb(soup)

    container = soup.select_one(CONTENT_SELECTOR)
    if container is None:
        # 컨테이너 미탐지 — 본문 유실 위험. 빈 텍스트로 표시하고 호출측에서 경고.
        return {"doc_id": doc_id, "text": "", "attachments": [],
                "breadcrumb": breadcrumb, "_no_container": True}

    # 첨부는 노이즈 제거 전에 수집 (기능부 안에 서식 다운로드가 있을 수 있음)
    attachments = extract_attachments(container)

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
