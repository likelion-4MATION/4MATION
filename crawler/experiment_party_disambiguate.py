"""송금인/수취인 문서쌍에 기존 disambiguate(sub_category prefix) 메커니즘 확장 적용 —
격리 실험, 프로덕션 미접촉.

현재 disambiguate=True는 page_title이 서로 다른 문서 간 충돌하는 2쌍(유의사항·개요)에만
적용된다. `MsdrprPossDcmntGudn`(송금인)·`MsdrAddrsePossDcmntGudn`(수취인)은 title이
이미 다르므로("착오송금인"/"착오송금수취인") 이 조건에 걸리지 않는다.

주의(사전 구조 확인, party_prefix_check.txt): 두 문서의 page_title이 이미 각 청크
맨 앞에 "착오송금인"/"착오송금수취인"으로 붙어 있어 party 구분 신호 자체는 이미
존재한다. sub_category로 바꾸면 그 앞에 공유 상위 브레드크럼("착오송금반환지원 >
... > 구비서류안내 > ")이 추가로 붙어 오히려 희석될 가능성도 있다 — 추측하지 않고
실측으로 판단한다.

방법: 프로덕션 인덱스(bge-m3, CHUNK_SIZE=500)를 그대로 복사하되, 이 2개 문서에
속한 청크만 sub_category 프리픽스로 재임베딩 + BM25 재적합. 나머지는 전부 동일.

사용: python experiment_party_disambiguate.py
"""

from __future__ import annotations

import json
import pathlib
import pickle

import faiss
import numpy as np

import rag

TARGET_DOCS = {
    "kdic-fins-ir-aplygudn-MsdrprPossDcmntGudn-selectScrn",
    "kdic-fins-ir-aplygudn-MsdrAddrsePossDcmntGudn-selectScrn",
}
EXPERIMENT_DIR = "data/index_experiment_party_disambiguate"
TESTSET = "data/testset_natural_400_v3.jsonl"


def build_experiment_index() -> None:
    chunks = [json.loads(l) for l in open("data/index/chunk_meta.jsonl", encoding="utf-8")]
    embs = np.load("data/index/emb.npy").copy()
    colliding = rag._colliding_titles(chunks)

    target_idxs = [i for i, c in enumerate(chunks) if c["parent_doc_id"] in TARGET_DOCS]
    print(f"대상 청크 {len(target_idxs)}개 재임베딩(sub_category prefix)...")
    texts = [rag.chunk_embed_text(chunks[i], disambiguate=True) for i in target_idxs]
    embs[target_idxs] = rag.embed_texts(texts)

    d = pathlib.Path(EXPERIMENT_DIR)
    d.mkdir(parents=True, exist_ok=True)

    index = faiss.IndexFlatIP(rag.EMB_DIM)
    index.add(embs)
    faiss.write_index(index, str(d / "faiss.index"))
    np.save(d / "emb.npy", embs)

    from rank_bm25 import BM25Okapi
    corpus = []
    for i, c in enumerate(chunks):
        disamb = i in target_idxs or c.get("page_title", "") in colliding
        corpus.append(rag.tokenize(rag.chunk_embed_text(c, disambiguate=disamb)))
    bm25 = BM25Okapi(corpus, b=rag.BM25_B)
    with open(d / "bm25.pkl", "wb") as f:
        pickle.dump({"bm25": bm25, "corpus_len": len(chunks)}, f)

    with open(d / "chunk_meta.jsonl", "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    (d / "docs.json").write_text("{}", encoding="utf-8")
    print(f"실험 인덱스 빌드 완료 -> {EXPERIMENT_DIR}")


def evaluate(index_dir: str) -> None:
    import collections
    searcher = rag.Searcher(index_dir=index_dir)
    testset = [json.loads(l) for l in open(TESTSET, encoding="utf-8")]

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

    def metrics(items):
        n = len(items)
        h1 = sum(1 for r, _ in items if r == 1)
        h3 = sum(1 for r, _ in items if 1 <= r <= 3)
        mrr = sum((1.0 / r if r else 0.0) for r, _ in items)
        return {"n": n, "hit@1": h1 / n, "hit@3": h3 / n, "mrr": mrr / n}

    ov = metrics(ranks_bf)
    groups = collections.defaultdict(list)
    for r, bf in ranks_bf:
        groups[bf].append((r, bf))

    print(f"\n전체: hit@1={ov['hit@1']:.3f} hit@3={ov['hit@3']:.3f} MRR={ov['mrr']:.3f}")
    print("\n업무별:")
    for bf in sorted(groups, key=lambda b: -len(groups[b])):
        m = metrics(groups[bf])
        print(f"  {bf:16} n={m['n']:3d}  hit@1={m['hit@1']:.3f}  hit@3={m['hit@3']:.3f}  MRR={m['mrr']:.3f}")

    # 대상 문서가 gt인 문항만 별도 확인
    target_q = [(r, bf) for (r, bf), it in zip(ranks_bf, testset)
                if set(it["gt_docs"]) & TARGET_DOCS]
    if target_q:
        m = metrics(target_q)
        print(f"\n대상 문서(송금인/수취인)가 정답인 문항만(n={m['n']}): "
              f"hit@1={m['hit@1']:.3f} hit@3={m['hit@3']:.3f} MRR={m['mrr']:.3f}")


if __name__ == "__main__":
    build_experiment_index()
    evaluate(EXPERIMENT_DIR)
