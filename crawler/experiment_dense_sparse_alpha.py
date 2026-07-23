"""dw/sw(dense/sparse RRF 가중치) 비율 재확인 — 사용자 문의(RRF_ALPHA=0.6, dense 60%/
sparse 40%)에 대한 실측 검증. rrf_k=5는 고정(현재 확정값), dw/sw 비율만 비교.

현재 확정값(DECISIONS.md, 60개 조합 그리드서치 근거): dw=2.0, sw=1.0 (dense 66.7%).
문의된 0.6/0.4(dense 60%)를 포함해 근방을 그리드로 실측 비교한다.

사용: python experiment_dense_sparse_alpha.py
"""

from __future__ import annotations

import collections
import json

import rag

TESTSET = "data/testset_natural_400_v3.jsonl"
LOG_PATH = "data/dense_sparse_alpha_grid_log.txt"
POOL = 30
KMAX = 10
RRF_K = 5
MAX_PER_DOC = 1

# (dw, sw) 후보 — 현재 확정값(2.0,1.0)과 문의값(0.6,0.4) 포함, 근방 몇 개 추가
CANDIDATES = [
    (2.0, 1.0, "현재 확정값(dense 66.7%)"),
    (1.5, 1.0, "dense 60%"),
    (0.6, 0.4, "문의값(dense 60%, 절대크기 축소)"),
    (0.55, 0.45, "dense 55%"),
    (0.65, 0.35, "dense 65%"),
    (1.0, 1.0, "동일가중(dense 50%)"),
]


def fuse(d, s, dw, sw, chunks):
    rrf: dict[int, float] = {}
    for rank, (idx, _) in enumerate(d):
        rrf[idx] = rrf.get(idx, 0.0) + dw / (RRF_K + rank + 1)
    for rank, (idx, _) in enumerate(s):
        rrf[idx] = rrf.get(idx, 0.0) + sw / (RRF_K + rank + 1)
    ranked = sorted(rrf.items(), key=lambda x: x[1], reverse=True)
    seen: dict[str, int] = {}
    out = []
    for idx, _ in ranked:
        doc_id = chunks[idx]["parent_doc_id"]
        if seen.get(doc_id, 0) >= MAX_PER_DOC:
            continue
        seen[doc_id] = seen.get(doc_id, 0) + 1
        out.append(idx)
        if len(out) >= KMAX:
            break
    return out


def first_hit_rank(idxs, chunks, gt):
    for r, idx in enumerate(idxs, 1):
        if chunks[idx]["parent_doc_id"] in gt:
            return r
    return 0


def metrics(ranks_bf):
    n = len(ranks_bf)
    h1 = sum(1 for r, _ in ranks_bf if r == 1)
    h3 = sum(1 for r, _ in ranks_bf if 1 <= r <= 3)
    mrr = sum((1.0 / r if r else 0.0) for r, _ in ranks_bf)
    return {"n": n, "hit@1": h1 / n, "hit@3": h3 / n, "mrr": mrr / n}


def per_domain(ranks_bf):
    groups = collections.defaultdict(list)
    for r, bf in ranks_bf:
        groups[bf].append((r, bf))
    return {bf: metrics(v) for bf, v in groups.items()}


def main() -> None:
    searcher = rag.Searcher()
    testset = [json.loads(l) for l in open(TESTSET, encoding="utf-8")]

    print("후보 캐시 계산 중...")
    cache = []
    for it in testset:
        d = searcher.dense(it["question"], POOL)
        s = searcher.sparse(it["question"], POOL)
        cache.append((d, s, set(it["gt_docs"]), it["business_function"]))
    print("캐시 완료.\n")

    results = {}
    for dw, sw, label in CANDIDATES:
        ranks_bf = []
        for d, s, gt, bf in cache:
            idxs = fuse(d, s, dw, sw, searcher.chunks)
            rank = first_hit_rank(idxs, searcher.chunks, gt)
            ranks_bf.append((rank, bf))
        ov = metrics(ranks_bf)
        dm = per_domain(ranks_bf)
        results[(dw, sw)] = {"overall": ov, "domains": dm, "label": label}

    all_domains = sorted({bf for r in results.values() for bf in r["domains"]})
    lines = ["# dense/sparse RRF 가중치(dw/sw) 비율 재확인 (rrf_k=5 고정)", "",
             "| dw | sw | 설명 | hit@1 | hit@3 | MRR |", "|---|---|---|---|---|---|"]
    print(f"{'dw':>5} {'sw':>5} {'설명':16} {'hit@1':>7} {'hit@3':>7} {'MRR':>7} {'chakosongeum_h3':>15}")
    for dw, sw, label in CANDIDATES:
        r = results[(dw, sw)]
        ov = r["overall"]
        ecs = r["domains"].get("착오송금 반환 신청", {}).get("hit@3", 0)
        lines.append(f"| {dw} | {sw} | {label} | {ov['hit@1']:.3f} | {ov['hit@3']:.3f} | {ov['mrr']:.3f} |")
        print(f"{dw:>5} {sw:>5} {label:16} {ov['hit@1']:>7.3f} {ov['hit@3']:>7.3f} {ov['mrr']:>7.3f} {ecs:>15.3f}")

    lines += ["", "## 업무별 hit@3", "", "| dw | sw | " + " | ".join(all_domains) + " |",
              "|---|---|" + "---|" * len(all_domains)]
    for dw, sw, label in CANDIDATES:
        row = [f"{results[(dw, sw)]['domains'].get(bf, {}).get('hit@3', 0):.3f}" for bf in all_domains]
        lines.append(f"| {dw} | {sw} | " + " | ".join(row) + " |")

    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\n로그 -> {LOG_PATH}")


if __name__ == "__main__":
    main()
