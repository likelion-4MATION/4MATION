"""rrf_k 단독 그리드서치 — 착오송금 hit@3(.819) 개선 후보 검증용.

dw=2.0 · sw=1.0 · BM25_B=0.85 · pool=30 · max_per_doc=1 은 고정(D2 확정값,
DECISIONS.md 07-22 근거)하고 rrf_k만 바꿔 400건 재평가한다. dense/sparse
후보 리스트는 쿼리당 1회만 계산해 캐시하고(비용 지배 요인은 임베딩/BM25
계산이지 RRF 재계산이 아님), rrf_k별 재계산은 캐시된 리스트에 대한 순수
연산이라 그리드 전체가 수 초 내 완료된다.

평가는 rag.Searcher.hybrid()와 완전히 동일한 RRF 수식·max_per_doc 캡
로직을 그대로 재현한다(코드 복제가 아니라 캐시 후보에 대한 재적용).

산출: data/rrf_k_grid_log.txt — 전체(micro) + 업무별(6개) hit@1/hit@3/MRR.

사용: python grid_rrf_k.py
"""

from __future__ import annotations

import collections
import json

import rag

TESTSET = "data/testset_natural_400_v3.jsonl"
LOG_PATH = "data/rrf_k_grid_log.txt"

DW = 2.0
SW = 1.0
POOL = 30
MAX_PER_DOC = 1
KMAX = 10

RRF_K_CANDIDATES = [1, 2, 3, 4, 5, 7, 10, 15, 20, 30, 50, 60, 100, 200]


def load_testset() -> list[dict]:
    return [json.loads(l) for l in open(TESTSET, encoding="utf-8")]


def fuse(d: list[tuple[int, float]], s: list[tuple[int, float]],
         rrf_k: int, chunks: list[dict]) -> list[int]:
    """rag.Searcher.hybrid()와 동일한 RRF+max_per_doc 로직(캐시된 후보 재사용)."""
    rrf: dict[int, float] = {}
    for rank, (idx, _) in enumerate(d):
        rrf[idx] = rrf.get(idx, 0.0) + DW / (rrf_k + rank + 1)
    for rank, (idx, _) in enumerate(s):
        rrf[idx] = rrf.get(idx, 0.0) + SW / (rrf_k + rank + 1)
    ranked = sorted(rrf.items(), key=lambda x: x[1], reverse=True)
    seen: dict[str, int] = {}
    out: list[int] = []
    for idx, _ in ranked:
        doc_id = chunks[idx]["parent_doc_id"]
        if seen.get(doc_id, 0) >= MAX_PER_DOC:
            continue
        seen[doc_id] = seen.get(doc_id, 0) + 1
        out.append(idx)
        if len(out) >= KMAX:
            break
    return out


def first_hit_rank(idxs: list[int], chunks: list[dict], gt: set[str]) -> int:
    for r, idx in enumerate(idxs, 1):
        if chunks[idx]["parent_doc_id"] in gt:
            return r
    return 0


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
    return {bf: metrics(items) for bf, items in groups.items()}


def main() -> None:
    testset = load_testset()
    searcher = rag.Searcher()

    print(f"후보 캐시 계산 중 (dense+sparse, pool={POOL}, {len(testset)}건)...")
    cache = []
    for it in testset:
        d = searcher.dense(it["question"], POOL)
        s = searcher.sparse(it["question"], POOL)
        cache.append((d, s, set(it["gt_docs"]), it["business_function"]))
    print("캐시 완료.\n")

    lines = ["# rrf_k 단독 그리드서치 (dw=2.0 · sw=1.0 · BM25_B=0.85 · pool=30 · "
             "max_per_doc=1 고정)", "",
             f"- 평가셋: {len(testset)}건 · KMAX={KMAX}", "",
             "## 전체(micro) 지표", "",
             "| rrf_k | hit@1 | hit@3 | MRR |", "|---|---|---|---|"]

    results = {}
    for rrf_k in RRF_K_CANDIDATES:
        ranks_bf = []
        for d, s, gt, bf in cache:
            idxs = fuse(d, s, rrf_k, searcher.chunks)
            rank = first_hit_rank(idxs, searcher.chunks, gt)
            ranks_bf.append((rank, bf))
        overall = metrics(ranks_bf)
        domains = per_domain(ranks_bf)
        results[rrf_k] = {"overall": overall, "domains": domains}
        lines.append(f"| {rrf_k} | {overall['hit@1']:.3f} | {overall['hit@3']:.3f} | "
                      f"{overall['mrr']:.3f} |")

    # 업무별 상세 (착오송금 우선 확인)
    all_domains = sorted({bf for r in results.values() for bf in r["domains"]})
    lines += ["", "## 업무별 hit@3 (rrf_k별)", "",
              "| rrf_k | " + " | ".join(all_domains) + " |",
              "|---|" + "---|" * len(all_domains)]
    for rrf_k in RRF_K_CANDIDATES:
        row = [f"{results[rrf_k]['domains'][bf]['hit@3']:.3f}" for bf in all_domains]
        lines.append(f"| {rrf_k} | " + " | ".join(row) + " |")

    lines += ["", "## 업무별 MRR (rrf_k별)", "",
              "| rrf_k | " + " | ".join(all_domains) + " |",
              "|---|" + "---|" * len(all_domains)]
    for rrf_k in RRF_K_CANDIDATES:
        row = [f"{results[rrf_k]['domains'][bf]['mrr']:.3f}" for bf in all_domains]
        lines.append(f"| {rrf_k} | " + " | ".join(row) + " |")

    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"현재값(rrf_k=5) 착오송금 hit@3: {results[5]['domains']['착오송금 반환 신청']['hit@3']:.3f}")
    print("\nrrf_k별 착오송금 hit@3 / 전체 hit@3:")
    for rrf_k in RRF_K_CANDIDATES:
        c = results[rrf_k]["domains"].get("착오송금 반환 신청", {})
        o = results[rrf_k]["overall"]
        print(f"  rrf_k={rrf_k:4d}  착오송금 hit@3={c.get('hit@3', 0):.3f}  "
              f"전체 hit@3={o['hit@3']:.3f}  전체 MRR={o['mrr']:.3f}")
    print(f"\n로그 → {LOG_PATH}")


if __name__ == "__main__":
    main()
