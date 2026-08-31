"""크롤링 청크의 Q-Form field:value 메타데이터 생성.

원문이 바뀌면 다음 크롤링/청킹에서 현재 본문으로 다시 추출한다. 특정 근거 문구나
청크 번호를 영구 키로 사용하지 않는다. 조합 테이블에 존재하는 값만 남겨 검색기가
사용자 Q-Form 슬롯과 안전하게 비교할 수 있게 한다.
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parent.parent
CHATBOT = ROOT / "chatbot"
if str(CHATBOT) not in sys.path:
    sys.path.insert(0, str(CHATBOT))

from qform_extract import extract_metadata  # noqa: E402


SLOT_FIELDS = ("party", "sub_task", "qualification", "subject", "method")
COMBO_FILES = {
    "착오송금 반환 신청": ROOT / "crawler" / "data" / "qform_combos_msdr.csv",
    "예금보험금 안내": ROOT / "crawler" / "data" / "qform_combos_dpin.csv",
}


def _tokens(value) -> list[str]:
    if isinstance(value, list):
        values = value
    else:
        values = str(value or "").split(";")
    return [str(v).strip() for v in values if str(v).strip() and str(v).strip() != "공통"]


def _allowed_by_bf() -> dict[str, dict[str, set[str]]]:
    out: dict[str, dict[str, set[str]]] = {}
    for bf, path in COMBO_FILES.items():
        allowed = {field: set() for field in SLOT_FIELDS}
        try:
            with path.open(encoding="utf-8-sig") as fh:
                rows = csv.DictReader(line for line in fh if not line.lstrip().startswith("#"))
                for row in rows:
                    for field in SLOT_FIELDS:
                        allowed[field].update(_tokens(row.get(field)))
        except (FileNotFoundError, OSError):
            pass
        out[bf] = allowed
    return out


ALLOWED_BY_BF = _allowed_by_bf()


def tag(text: str, business_function: str | None) -> dict[str, list[str]]:
    """본문에서 해당 업무 조합표에 존재하는 Q-Form 값만 추출한다."""
    allowed = ALLOWED_BY_BF.get(business_function or "")
    if not allowed:
        return {}
    raw = extract_metadata(text, business_function or "")
    out: dict[str, list[str]] = {}
    for field in SLOT_FIELDS:
        values = [v for v in _tokens(raw.get(field)) if v in allowed[field]]
        if values:
            out[field] = list(dict.fromkeys(values))
    return out


def annotate(record: dict) -> dict:
    """청크 레코드 사본에 ``qform_meta``를 항상 넣는다(미대상은 빈 객체)."""
    out = dict(record)
    out["qform_meta"] = tag(out.get("text") or "", out.get("business_function"))
    return out


def annotate_path(path: pathlib.Path) -> int:
    """기존 JSONL을 같은 순서로 다시 태깅하고 원자적으로 교체한다."""
    if not path.exists():
        return 0
    rows = [annotate(json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
                   encoding="utf-8")
    tmp.replace(path)
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="기존 청크 JSONL의 Q-Form 메타데이터 갱신")
    parser.add_argument("paths", nargs="*", type=pathlib.Path,
                        default=[ROOT / "crawler" / "data" / "chunks.jsonl",
                                 ROOT / "crawler" / "data" / "index" / "chunk_meta.jsonl"])
    args = parser.parse_args()
    for path in args.paths:
        print(f"{path}: {annotate_path(path)}청크")


if __name__ == "__main__":
    main()
