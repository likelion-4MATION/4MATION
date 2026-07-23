"""Near-duplicate *candidate* generation for human qrels review.

This script never writes to a testset and never changes ``gt_docs``.  A text
similarity score is only a triage signal: a reviewer must separately decide
whether the candidate answers the query and should be added to the qrels.

The output is JSONL so each candidate can be independently reviewed and
annotated.  ``review_status`` is always ``pending`` when generated.

Run from crawler/:
    python generate_near_duplicate_candidates.py
    python generate_near_duplicate_candidates.py --min-ratio 0.40 --top-k 3

``--min-ratio`` controls output volume only; it is not a relevance or
near-duplicate decision threshold.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


DEFAULT_TESTSET = Path("data/testset_natural_400_v3.jsonl")
DEFAULT_CHUNKS = Path("data/chunks.jsonl")
DEFAULT_OUTPUT = Path("data/near_duplicate_candidates.jsonl")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def normalize(text: str) -> str:
    return " ".join(text.lower().split())


def load_document_chunks(path: Path) -> dict[str, list[dict[str, Any]]]:
    docs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for chunk in read_jsonl(path):
        docs[chunk["parent_doc_id"]].append(chunk)
    return docs


def best_chunk_match(
    source_chunks: list[dict[str, Any]], candidate_chunks: list[dict[str, Any]]
) -> tuple[float, dict[str, Any], dict[str, Any]]:
    """Return the highest character-sequence score and the supporting chunks."""
    best = (-1.0, source_chunks[0], candidate_chunks[0])
    for source in source_chunks:
        source_text = normalize(source["text"])
        for candidate in candidate_chunks:
            score = SequenceMatcher(None, source_text, normalize(candidate["text"])).ratio()
            if score > best[0]:
                best = (score, source, candidate)
    return best


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate pending near-duplicate review candidates.")
    parser.add_argument("--testset", type=Path, default=DEFAULT_TESTSET)
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--min-ratio", type=float, default=0.0,
                        help="Output filter only; not an automatic labeling threshold (default: 0.0).")
    parser.add_argument("--top-k", type=int, default=3, help="Candidates retained per source GT document.")
    parser.add_argument("--cross-business", action="store_true",
                        help="Compare all corpus documents instead of only the question's business function.")
    args = parser.parse_args()
    if not 0.0 <= args.min_ratio <= 1.0:
        parser.error("--min-ratio must be between 0 and 1")
    if args.top_k < 1:
        parser.error("--top-k must be at least 1")

    rows = read_jsonl(args.testset)
    chunks_by_doc = load_document_chunks(args.chunks)
    docs_by_business: dict[str, set[str]] = defaultdict(set)
    for doc_id, chunks in chunks_by_doc.items():
        docs_by_business[chunks[0]["business_function"]].add(doc_id)

    candidates: list[dict[str, Any]] = []
    missing_gt = set()
    for row_index, row in enumerate(rows):
        source_docs = row["gt_docs"]
        pool = set(chunks_by_doc) if args.cross_business else docs_by_business[row["business_function"]]
        for source_doc_id in source_docs:
            source_chunks = chunks_by_doc.get(source_doc_id)
            if not source_chunks:
                missing_gt.add(source_doc_id)
                continue
            scored = []
            for candidate_doc_id in pool - set(source_docs):
                score, source_chunk, candidate_chunk = best_chunk_match(
                    source_chunks, chunks_by_doc[candidate_doc_id]
                )
                if score >= args.min_ratio:
                    scored.append((score, candidate_doc_id, source_chunk, candidate_chunk))
            for score, candidate_doc_id, source_chunk, candidate_chunk in sorted(scored, reverse=True)[:args.top_k]:
                candidates.append({
                    "review_status": "pending",
                    "decision": None,
                    "testset_row": row_index,
                    "question": row["question"],
                    "business_function": row["business_function"],
                    "source_gt_doc": source_doc_id,
                    "candidate_doc": candidate_doc_id,
                    "sequence_matcher_ratio": round(score, 6),
                    "source_chunk_id": source_chunk["chunk_id"],
                    "candidate_chunk_id": candidate_chunk["chunk_id"],
                    "source_excerpt": source_chunk["text"][:500],
                    "candidate_excerpt": candidate_chunk["text"][:500],
                    "review_instruction": (
                        "Do not use this score as a label. Independently verify duplicate equivalence "
                        "and whether the candidate answers this specific question before changing gt_docs."
                    ),
                })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(candidate, ensure_ascii=False) + "\n" for candidate in candidates),
        encoding="utf-8",
    )
    print(f"pending candidates: {len(candidates)} -> {args.output}")
    if missing_gt:
        print(f"warning: {len(missing_gt)} GT documents absent from chunks: {sorted(missing_gt)}")
    print("gt_docs unchanged: candidate generation never writes the testset.")


if __name__ == "__main__":
    main()
