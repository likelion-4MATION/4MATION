"""CHUNK_SIZE 단독 그리드서치 — 착오송금 hub 문서 완화 후보 검증(2순위 실험).

고정값(전부 현재 확정값, D2/S1 근거 그대로): OVERLAP=100 · rrf_k=5 · dw=2.0 ·
sw=1.0 · pool=30 · max_per_doc=1 · BM25_B=0.85 · MODEL_NAME=bge-m3.
변경 대상은 CHUNK_SIZE 단 하나(STEP8 "한 번에 하나씩" 원칙).

**프로덕션 data/chunks.jsonl · data/index 는 절대 건드리지 않는다.** rag.py의
Store.build_and_save()는 호출 즉시 data/chunks.jsonl을 덮어쓰므로(경로 하드코딩)
이 실험에서는 사용하지 않고, 그 핵심 로직(임베딩·BM25·FAISS)만 격리 재구현해
data/index_backup_chunk<size>/ 에만 쓴다 — 기존 index_backup_ko_sroberta와
동일한 네이밍 규칙(.gitignore의 index_backup_* 패턴)이라 커밋 대상에서도 자동 제외.

사전 확인(hub_doc_check.txt, 별도 스크립트 실행 결과): 착오송금 미적중 오염 상위
4개 문서 중 CHUNK_SIZE에 민감한 것은 최대 1.5개뿐(MtrsGvbkSprtProc=800자 4청크로
직접 영향권, kmrsItrdAplyTrgt=417자 1청크로 경계 근접, selectFaqMsdrGvbkAply는
FAQ라 split_faq() 경로라 CHUNK_SIZE 완전 무관, MsdrprPossDcmntGudn은 표/소단락
위주라 이미 800 한계 근처도 아님). 이 실험은 한계를 인지하고 진행하는 탐색적
실험이다.

사용: python experiment_chunk_size.py <size1> <size2> ...
"""

from __future__ import annotations

import collections
import glob
import json
import pathlib
import pickle
import sys
import time

import faiss
import numpy as np

import chunk as chunk_mod
import rag

PARSED_DIR = "data/parsed"
TESTSET = "data/testset_natural_400_v3.jsonl"
LOG_PATH = "data/chunk_size_grid_log.txt"


def build_chunks(chunk_size: int) -> list[dict]:
    """chunk.py의 make_chunks()를 그대로 재사용, CHUNK_SIZE만 주입."""
    chunk_mod.CHUNK_SIZE = chunk_size
    all_chunks = []
    for p in sorted(glob.glob(f"{PARSED_DIR}/*.json")):
        rec = json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
        all_chunks.extend(chunk_mod.make_chunks(rec))
    return all_chunks


def build_index(chunks: list[dict], index_dir: str) -> None:
    """rag.Store.build_and_save()의 핵심 로직만 격리 재현(chunks.jsonl 미기록)."""
    d = pathlib.Path(index_dir)
    d.mkdir(parents=True, exist_ok=True)
    colliding = rag._colliding_titles(chunks)
    texts = [rag.chunk_embed_text(c, disambiguate=c.get("page_title", "") in colliding)
             for c in chunks]
    embs = rag.embed_texts(texts) if texts else np.zeros((0, rag.EMB_DIM), "float32")

    index = faiss.IndexFlatIP(rag.EMB_DIM)
    if len(chunks):
        index.add(embs)
    faiss.write_index(index, str(d / "faiss.index"))
    np.save(d / "emb.npy", embs)

    from rank_bm25 import BM25Okapi
    corpus = [rag.tokenize(t) for t in texts]
    bm25 = BM25Okapi(corpus, b=rag.BM25_B) if corpus else None
    with open(d / "bm25.pkl", "wb") as f:
        pickle.dump({"bm25": bm25, "corpus_len": len(chunks)}, f)

    with open(d / "chunk_meta.jsonl", "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    (d / "docs.json").write_text("{}", encoding="utf-8")


def evaluate(index_dir: str, testset: list[dict]) -> list[tuple[int, str]]:
    searcher = rag.Searcher(index_dir=index_dir)
    ranks_bf = []
    for it in testset:
        gt = set(it["gt_docs"])
        hits = searcher.search(it["question"], k=10, mode="hybrid")
        rank = 0
        for r, c in enumerate(hits, 1):
            if c["parent_doc_id"] in gt:
                rank = r
                break
        ranks_bf.append((rank, it["business_function"]))
    return ranks_bf


def metrics(ranks_bf: list[tuple[int, str]]) -> dict:
    n = len(ranks_bf)
    h1 = sum(1 for r, _ in ranks_bf if r == 1)
    h3 = sum(1 for r, _ in ranks_bf if 1 <= r <= 3)
    mrr = sum((1.0 / r if r else 0.0) for r, _ in ranks_bf)
    return {"n": n, "hit@1": h1 / n, "hit@3": h3 / n, "mrr": mrr / n}


def per_domain(ranks_bf: list[tuple[int, str]]) -> dict[str, dict]:
    groups: dict[str, list] = collections.defaultdict(list)
    for r, bf in ranks_bf:
        groups[bf].append((r, bf))
    return {bf: metrics(v) for bf, v in groups.items()}


def main() -> None:
    sizes = [int(a) for a in sys.argv[1:]] or [800]
    testset = [json.loads(l) for l in open(TESTSET, encoding="utf-8")]

    lines = ["# CHUNK_SIZE 단독 그리드서치 (OVERLAP=100 고정, 그 외 전부 확정값 고정)", ""]
    results = {}
    for size in sizes:
        t0 = time.time()
        idx_dir = f"data/index_backup_chunk{size}"
        chunks = build_chunks(size)
        build_index(chunks, idx_dir)
        ranks_bf = evaluate(idx_dir, testset)
        ov = metrics(ranks_bf)
        dm = per_domain(ranks_bf)
        elapsed = time.time() - t0
        results[size] = {"overall": ov, "domains": dm, "n_chunks": len(chunks)}
        ecs = dm.get('착오송금 반환 신청', {}).get('hit@3', 0)
        print(f"size={size} chunks={len(chunks)} hit@1={ov['hit@1']:.3f} "
              f"hit@3={ov['hit@3']:.3f} mrr={ov['mrr']:.3f} "
              f"chakosongeum_hit@3={ecs:.3f} ({elapsed:.0f}s)")

    all_domains = sorted({bf for r in results.values() for bf in r["domains"]})
    lines += ["## 전체(micro)", "", "| CHUNK_SIZE | 청크수 | hit@1 | hit@3 | MRR |",
              "|---|---|---|---|---|"]
    for size in sizes:
        r = results[size]["overall"]
        lines.append(f"| {size} | {results[size]['n_chunks']} | {r['hit@1']:.3f} | "
                      f"{r['hit@3']:.3f} | {r['mrr']:.3f} |")

    lines += ["", "## 업무별 hit@3", "", "| CHUNK_SIZE | " + " | ".join(all_domains) + " |",
              "|---|" + "---|" * len(all_domains)]
    for size in sizes:
        row = [f"{results[size]['domains'].get(bf, {}).get('hit@3', 0):.3f}"
               for bf in all_domains]
        lines.append(f"| {size} | " + " | ".join(row) + " |")

    lines += ["", "## 업무별 MRR", "", "| CHUNK_SIZE | " + " | ".join(all_domains) + " |",
              "|---|" + "---|" * len(all_domains)]
    for size in sizes:
        row = [f"{results[size]['domains'].get(bf, {}).get('mrr', 0):.3f}"
               for bf in all_domains]
        lines.append(f"| {size} | " + " | ".join(row) + " |")

    pathlib.Path(LOG_PATH).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nlog -> {LOG_PATH}")


if __name__ == "__main__":
    main()
