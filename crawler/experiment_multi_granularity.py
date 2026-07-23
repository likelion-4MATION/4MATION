"""다중 청크 크기(granularity) 병합 검증 — CHUNK_SIZE 그리드서치의 자연스러운 후속 실험.

동기: CHUNK_SIZE 그리드서치(800/600/500/400)에서 업무별 최적 크기가 서로 달랐다
(예: 착오송금·예금보험금은 500이 800보다 우수, 은닉재산·고객미수령금은 800이 500보다
우수). 이는 "단일 청크 크기로는 모든 업무를 동시에 만족시킬 수 없다"는 관찰이며,
서로 다른 크기의 인덱스를 별도 검색기(retriever)로 보고 RRF로 병합하면 두 크기의
강점을 모두 취할 수 있다는 가설을 세울 근거가 된다.

근거: RRF(Cormack, Clarke & Buettcher, SIGIR 2009)는 "두 개 이상의 순위 리스트를
융합"하는 일반 기법으로, 이 프로젝트가 이미 dense+sparse 융합에 쓰고 있는 바로 그
수식이다 — 융합 대상이 "검색기 2개(dense/sparse)"에서 "청크 크기별 하이브리드
결과 N개"로 바뀔 뿐 새 이론이 아니다. 청크 크기별로 이미 만든 hybrid(dense+sparse
RRF 완료) 결과를 문서(parent_doc_id) 단위로 다시 RRF 융합한다(2단계 융합, 가중치는
튜닝 없이 전부 동일 1.0 — 추측 배제, "병합 자체가 이득인가"만 먼저 검증).

기존 data/index_backup_chunk{500,600,800,400} 인덱스를 그대로 재사용 —
재임베딩 없음(수 초 내 완료), 프로덕션 데이터 미접촉.

사용: python experiment_multi_granularity.py
"""

from __future__ import annotations

import collections
import itertools
import json
import pathlib

import rag

TESTSET = "data/testset_natural_400_v3.jsonl"
LOG_PATH = "data/multi_granularity_grid_log.txt"
SIZES = [400, 500, 600, 800]
RRF_K2 = 5  # 융합-of-융합 상수. 기존 rrf_k 기본값 그대로(추측 튜닝 없음).
POOL_PER_SIZE = 10  # 각 크기별 hybrid() 결과에서 가져올 문서 수(max_per_doc=1이라 문서=청크)


def load_testset() -> list[dict]:
    return [json.loads(l) for l in open(TESTSET, encoding="utf-8")]


def per_size_doc_ranks(searchers: dict[int, rag.Searcher], question: str) -> dict[int, list[str]]:
    """크기별 hybrid() 결과를 문서ID 순위 리스트로 변환."""
    out = {}
    for size, searcher in searchers.items():
        hits = searcher.search(question, k=POOL_PER_SIZE, mode="hybrid")
        out[size] = [h["parent_doc_id"] for h in hits]
    return out


def fuse_docs(doc_lists: list[list[str]], rrf_k: int) -> list[str]:
    score: dict[str, float] = {}
    for docs in doc_lists:
        for rank, doc_id in enumerate(docs):
            score[doc_id] = score.get(doc_id, 0.0) + 1.0 / (rrf_k + rank + 1)
    return [d for d, _ in sorted(score.items(), key=lambda x: x[1], reverse=True)]


def first_hit_rank(doc_ranked: list[str], gt: set[str]) -> int:
    for r, d in enumerate(doc_ranked, 1):
        if d in gt:
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
    return {bf: metrics(v) for bf, v in groups.items()}


def main() -> None:
    testset = load_testset()
    print("검색기 로드 중...")
    searchers = {size: rag.Searcher(index_dir=f"data/index_backup_chunk{size}") for size in SIZES}

    # 쿼리별 크기별 문서 순위를 1회만 계산해 캐시 (조합 그리드는 캐시 재사용)
    cache = []
    for it in testset:
        ranks = per_size_doc_ranks(searchers, it["question"])
        cache.append((ranks, set(it["gt_docs"]), it["business_function"]))
    print("캐시 완료.\n")

    combos = []
    for r in (1, 2, 3, 4):
        combos.extend(itertools.combinations(SIZES, r))

    results = {}
    for combo in combos:
        ranks_bf = []
        for ranks, gt, bf in cache:
            doc_lists = [ranks[s] for s in combo]
            fused = fuse_docs(doc_lists, RRF_K2)
            rank = first_hit_rank(fused, gt)
            ranks_bf.append((rank, bf))
        ov = metrics(ranks_bf)
        dm = per_domain(ranks_bf)
        results[combo] = {"overall": ov, "domains": dm}

    # 콘솔 요약(단일 크기 먼저, 그 다음 조합)
    print(f"{'조합':20} {'hit@1':>7} {'hit@3':>7} {'MRR':>7} {'chakosongeum_h3':>15}")
    for combo in sorted(combos, key=lambda c: (len(c), c)):
        r = results[combo]
        ov, dm = r["overall"], r["domains"]
        ecs = dm.get("착오송금 반환 신청", {}).get("hit@3", 0)
        label = "+".join(str(s) for s in combo)
        print(f"{label:20} {ov['hit@1']:>7.3f} {ov['hit@3']:>7.3f} {ov['mrr']:>7.3f} {ecs:>15.3f}")

    all_domains = sorted({bf for r in results.values() for bf in r["domains"]})
    lines = ["# 다중 청크 크기(granularity) 병합 그리드 (RRF_K2=5, 가중치 전부 1.0)", "",
              "## 전체(micro)", "", "| 조합 | hit@1 | hit@3 | MRR |", "|---|---|---|---|"]
    for combo in sorted(combos, key=lambda c: (len(c), c)):
        ov = results[combo]["overall"]
        label = "+".join(str(s) for s in combo)
        lines.append(f"| {label} | {ov['hit@1']:.3f} | {ov['hit@3']:.3f} | {ov['mrr']:.3f} |")

    lines += ["", "## 업무별 hit@3", "", "| 조합 | " + " | ".join(all_domains) + " |",
              "|---|" + "---|" * len(all_domains)]
    for combo in sorted(combos, key=lambda c: (len(c), c)):
        label = "+".join(str(s) for s in combo)
        row = [f"{results[combo]['domains'].get(bf, {}).get('hit@3', 0):.3f}" for bf in all_domains]
        lines.append(f"| {label} | " + " | ".join(row) + " |")

    lines += ["", "## 업무별 MRR", "", "| 조합 | " + " | ".join(all_domains) + " |",
              "|---|" + "---|" * len(all_domains)]
    for combo in sorted(combos, key=lambda c: (len(c), c)):
        label = "+".join(str(s) for s in combo)
        row = [f"{results[combo]['domains'].get(bf, {}).get('mrr', 0):.3f}" for bf in all_domains]
        lines.append(f"| {label} | " + " | ".join(row) + " |")

    pathlib.Path(LOG_PATH).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n로그 -> {LOG_PATH}")


if __name__ == "__main__":
    main()
