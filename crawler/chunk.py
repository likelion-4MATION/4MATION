"""청킹 + 스키마 부착 → data/chunks.jsonl

설정(고정, 03 문서 노션 권고 준용):
- CHUNK_SIZE=800자, OVERLAP=100자 (문단/섹션 경계 우선)
- 표(연속 "cell | cell" 라인)는 절대 중간분할 금지 → 단독 청크
- FAQ 페이지(page_type/title에 'FAQ')는 질문-답변 1쌍 = 1청크 (크기 무시), '열기' 토글 제거

청크 스키마(13필드, [meta-doc]에서 11→13 확장): chunk_id · parent_doc_id · business_function ·
  sub_category · page_type · coverage · variant · source_url · page_title · breadcrumb · text ·
  attachments · has_attachments

[meta-doc] 첨부 메타데이터를 페이지 단위가 아니라 "그 문서를 실제로 언급하는 청크"에만
붙인다. parser.py가 만든 페이지 전체 첨부 후보 목록(rec['attachments'])에서, 첨부의 앵커
텍스트(name)가 각 청크의 본문에 실제로 등장하는지 문자열 포함 여부로 판단한다 — 첨부를
설명하는 문단과 그 문단이 속한 청크가 항상 같은 조각이 되도록 보장하기 위함(잘못된 청크에
서식을 안내하는 오류 방지). 어떤 청크에도 매칭되지 않은 첨부는 조용히 버리지 않고
main()에서 경고로 출력한다 — 매칭 실패 원인(앵커 텍스트가 너무 짧거나 공용 문구인 경우
등)을 사람이 확인할 수 있게.
"""

from __future__ import annotations

import glob
import json
import pathlib
import sys

PARSED_DIR = "data/parsed"
OUT_PATH = "data/chunks.jsonl"

CHUNK_SIZE = 800
OVERLAP = 100
MIN_CHUNK = 60   # 표 사이 낀 짧은 헤딩/라인 파편 병합 임계

SCHEMA_FIELDS = ["chunk_id", "parent_doc_id", "business_function", "sub_category",
                 "page_type", "coverage", "variant", "source_url",
                 "page_title", "breadcrumb", "text",
                 "attachments", "has_attachments", "attachment_count"]


def is_faq(rec: dict) -> bool:
    tag = (rec.get("page_type", "") or "") + (rec.get("page_title", "") or "")
    return "FAQ" in tag or "faq" in tag


def split_faq(text: str) -> list[str]:
    """'질문' 라인마다 새 Q&A 청크 시작. '열기' 토글 라인 제거."""
    lines = [l for l in text.split("\n") if l.strip() and l.strip() != "열기"]
    chunks, cur = [], []
    for l in lines:
        if l.strip() == "질문" and cur:
            chunks.append("\n".join(cur))
            cur = [l]
        else:
            cur.append(l)
    if cur:
        chunks.append("\n".join(cur))
    return [c.strip() for c in chunks if c.strip()]


def _blocks(text: str) -> list[tuple[str, str]]:
    """표(연속 |라인)는 ('table', ...) 원자 블록, 그 외는 ('text', 라인)."""
    lines = [l for l in text.split("\n") if l.strip()]
    out, i = [], 0
    while i < len(lines):
        if "|" in lines[i]:
            j = i
            while j < len(lines) and "|" in lines[j]:
                j += 1
            out.append(("table", "\n".join(lines[i:j])))
            i = j
        else:
            out.append(("text", lines[i]))
            i += 1
    return out


def split_generic(text: str) -> list[str]:
    chunks, cur = [], ""
    for kind, blk in _blocks(text):
        if kind == "table":
            if cur.strip():
                chunks.append(cur.strip())
            chunks.append(blk)          # 표 단독 청크 (중간분할 금지)
            cur = ""
            continue
        cand = (cur + "\n" + blk).strip() if cur else blk
        if len(cand) <= CHUNK_SIZE:
            cur = cand
        else:
            if cur.strip():
                chunks.append(cur.strip())
                cur = (cur[-OVERLAP:] + "\n" + blk).strip()   # 오버랩
            else:
                cur = blk
            while len(cur) > CHUNK_SIZE + OVERLAP:             # 긴 단일 문단 하드분할
                chunks.append(cur[:CHUNK_SIZE])
                cur = cur[CHUNK_SIZE - OVERLAP:]
    if cur.strip():
        chunks.append(cur.strip())
    return _merge_small(chunks)


def _merge_small(chunks: list[str], min_len: int = MIN_CHUNK) -> list[str]:
    """표 사이에 낀 짧은 헤딩/파편 청크를 인접 청크에 병합 (검색 노이즈 제거)."""
    out: list[str] = []
    for c in chunks:
        if out and (len(c) < min_len or len(out[-1]) < min_len):
            out[-1] = (out[-1] + "\n" + c).strip()
        else:
            out.append(c)
    return out


def match_attachments(chunk_text: str, page_attachments: list[dict]) -> list[dict]:
    """[meta-doc] 페이지 단위 첨부 후보 중, 이 청크 본문에 실제 등장하는 것만 골라 반환.

    판단 기준: 첨부의 anchor_text가 청크 텍스트에 부분 문자열로 포함되는지.
    name(표시용 문서명)이 아니라 anchor_text로 매칭한다 — onclick_dynamic(버튼) 첨부는
    parser.py의 serialize_text() 단계에서 버튼 자체가 통째로 제거되어 버튼 자신의
    텍스트(name)는 본문에 남지 않고, 버튼을 감싸는 li/td의 안내 문구만 남기 때문
    (parser.py의 _anchor_text 참고). direct 링크는 anchor_text=name이라 동일하게 동작.
    구 파싱 데이터(anchor_text 없음) 호환을 위해 없으면 name으로 폴백한다.

    한계(팀 확인 필요): anchor_text가 "다운로드"처럼 일반적인 문구면 무관한 청크에
    오매칭될 수 있다. 실제 크롤 데이터로 돌려본 뒤 오매칭 사례가 보이면 href의
    파일명 쪽으로 기준을 좁히는 걸 권장.
    """
    if not page_attachments:
        return []
    out = []
    for att in page_attachments:
        anchor = att.get("anchor_text") or att.get("name")
        if anchor and anchor in chunk_text:
            out.append(att)
    return out


def make_chunks(rec: dict) -> list[dict]:
    text = rec.get("text", "")
    if not text.strip():
        return []
    parts = split_faq(text) if is_faq(rec) else split_generic(text)
    doc_id = rec["doc_id"]
    page_attachments = rec.get("attachments", [])
    out = []
    for i, part in enumerate(parts):
        chunk_atts = match_attachments(part, page_attachments)
        out.append({
            "chunk_id": f"{doc_id}#{i:02d}",
            "parent_doc_id": doc_id,
            "business_function": rec.get("business_function", ""),
            "sub_category": rec.get("sub_category", ""),
            "page_type": rec.get("page_type", ""),
            "coverage": rec.get("coverage", ""),
            "variant": rec.get("variant", ""),
            "source_url": rec.get("source_url", ""),
            "page_title": rec.get("page_title", ""),
            "breadcrumb": rec.get("breadcrumb", []),
            "text": part,
            "attachments": chunk_atts,
            "has_attachments": bool(chunk_atts),
            "attachment_count": len(chunk_atts),
        })
    return out


def main() -> None:
    parsed = sorted(glob.glob(f"{PARSED_DIR}/*.json"))
    if not parsed:
        sys.exit(f"파싱 결과 없음: {PARSED_DIR}")
    all_chunks, skipped, attach_warn = [], [], []
    for p in parsed:
        rec = json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
        cs = make_chunks(rec)
        if not cs:
            skipped.append(rec["doc_id"])
        else:
            # [meta-doc] 페이지 첨부 중 어떤 청크에도 안 붙은 게 있으면 경고
            # url이 None인 항목(onclick_dynamic)이 여러 개면 url만으로는 구분이 안 되므로
            # (name, url, anchor_text) 조합을 키로 써서 정확히 식별한다.
            def _att_key(a: dict) -> tuple:
                return (a.get("name"), a.get("url"), a.get("anchor_text"))

            page_atts = rec.get("attachments", [])
            matched_keys = {_att_key(a) for c in cs for a in c.get("attachments", [])}
            unmatched = [a for a in page_atts if _att_key(a) not in matched_keys]
            if unmatched:
                names = [a["name"] for a in unmatched]
                attach_warn.append(f"{rec['doc_id']}: 첨부 {len(unmatched)}건 청크 매칭 실패 — {names}")
        all_chunks.extend(cs)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    # 스키마 검증
    bad = []
    for c in all_chunks:
        miss = [k for k in SCHEMA_FIELDS if k not in c]
        empty = [k for k in ("chunk_id", "parent_doc_id", "business_function",
                             "source_url", "text") if not c.get(k)]
        if miss or empty:
            bad.append((c.get("chunk_id"), miss, empty))

    print(f"청크 {len(all_chunks)}건 (문서 {len(parsed)}건) → {OUT_PATH}")
    if skipped:
        print(f"  본문 비어 스킵: {skipped}")
    faqn = sum(1 for c in all_chunks if is_faq(c))
    print(f"  FAQ 청크: {faqn} · 일반 청크: {len(all_chunks)-faqn}")
    attn = sum(1 for c in all_chunks if c.get("has_attachments"))
    print(f"  첨부 보유 청크: {attn}건")
    lens = [len(c["text"]) for c in all_chunks]
    print(f"  청크 길이 min/avg/max: {min(lens)}/{sum(lens)//len(lens)}/{max(lens)}")
    print("  스키마 검증:", "전건 유효" if not bad else f"위반 {len(bad)}건: {bad[:5]}")
    if attach_warn:
        print("  첨부 매칭 경고:")
        for w in attach_warn:
            print("   -", w)
    if bad:
        sys.exit(1)


if __name__ == "__main__":
    main()