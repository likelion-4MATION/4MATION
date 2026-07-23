"""facet(business_function) 소프트부스트 격리 실험 — 프로덕션 미접촉.

07-22 세션에 시도했던 방식(쿼리-업무영역 centroid 코사인 유사도로 예측 후
소프트부스트)을 bge-m3 기준으로 재검증한다. 사전 진단(diagnose_facet_classifier.py)
에서 분류기 정확도가 58.5%(ko-sroberta)→80.7%(bge-m3)로 개선됐으나 착오송금
반환 신청(69.4%)·예금보험금 안내(49.2%)이 가장 취약하다는 것을 확인했다 —
실패를 예단하지 않고 실측으로 판단한다.

방법: 기존 hybrid RRF 점수에 "질의의 예측 업무영역과 후보 청크의 business_function이
일치하면 +boost 점수"를 더하는 소프트부스트(하드필터 아님 — 07-22 결과상 하드필터가
더 나빴으므로 재시도하지 않음). dense/sparse 후보와 분류기 예측을 쿼리당 1회만
계산해 캐시하고, boost 강도만 바꿔가며 재평가(비용 지배 요인은 임베딩 계산).

사용: python experiment_facet_boost.py
"""

from __future__ import annotations

import collections
import json

import numpy as np

import rag

TESTSET = "data/testset_natural_400_v3.jsonl"
LOG_PATH = "data/facet_boost_grid_log.txt"
POOL = 30
KMAX = 10
RRF_K = 5
DW = 2.0
SW = 1.0
MAX_PER_DOC = 1
BOOST_CANDIDATES = [0.0, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 0.8, 1.2]
"""0.005·0.01·0.02는 사용자 문의(BF_BOOST 0.02→0.005) 검증용 추가 그리드점 —
최초 그리드(0.1~1.2)는 전부 손해였으나 그보다 5~20배 작은 이 구간은 미검증이었음."""


def build_centroids(chunks: list[dict], embs: np.ndarray) -> tuple[list[str], np.ndarray]:
    by_bf: dict[str, list[int]] = collections.defaultdict(list)
    for i, c in enumerate(chunks):
        by_bf[c["business_function"]].append(i)
    names = sorted(by_bf)
    mat = []
    for bf in names:
        v = embs[by_bf[bf]].mean(axis=0)
        v = v / (np.linalg.norm(v) + 1e-9)
        mat.append(v)
    return names, np.stack(mat)


def fuse_with_boost(d: list[tuple[int, float]], s: list[tuple[int, float]],
                     chunks: list[dict], predicted_bf: str, boost: float) -> list[int]:
    rrf: dict[int, float] = {}
    for rank, (idx, _) in enumerate(d):
        rrf[idx] = rrf.get(idx, 0.0) + DW / (RRF_K + rank + 1)
    for rank, (idx, _) in enumerate(s):
        rrf[idx] = rrf.get(idx, 0.0) + SW / (RRF_K + rank + 1)
    if boost:
        for idx in list(rrf):
            if chunks[idx]["business_function"] == predicted_bf:
                rrf[idx] += boost
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
    return {bf: metrics(v) for bf, v in groups.items()}


def main() -> None:
    chunks = [json.loads(l) for l in open("data/index/chunk_meta.jsonl", encoding="utf-8")]
    embs = np.load("data/index/emb.npy")
    testset = [json.loads(l) for l in open(TESTSET, encoding="utf-8")]
    bf_names, cent_mat = build_centroids(chunks, embs)

    searcher = rag.Searcher()
    print("후보/분류기 예측 캐시 계산 중...")
    cache = []
    correct_pred = 0
    for it in testset:
        q_emb = rag.embed_texts([it["question"]])[0]
        sims = cent_mat @ q_emb
        predicted_bf = bf_names[int(np.argmax(sims))]
        if predicted_bf == it["business_function"]:
            correct_pred += 1
        d = searcher.dense(it["question"], POOL)
        s = searcher.sparse(it["question"], POOL)
        cache.append((d, s, set(it["gt_docs"]), it["business_function"], predicted_bf))
    print(f"캐시 완료. 분류기 정확도(재확인): {correct_pred}/{len(testset)} = {correct_pred/len(testset):.3f}\n")

    results = {}
    for boost in BOOST_CANDIDATES:
        ranks_bf = []
        for d, s, gt, true_bf, pred_bf in cache:
            idxs = fuse_with_boost(d, s, chunks, pred_bf, boost)
            rank = first_hit_rank(idxs, chunks, gt)
            ranks_bf.append((rank, true_bf))
        ov = metrics(ranks_bf)
        dm = per_domain(ranks_bf)
        results[boost] = {"overall": ov, "domains": dm}

    all_domains = sorted({bf for r in results.values() for bf in r["domains"]})
    lines = ["# facet(business_function) 소프트부스트 그리드 (bge-m3 centroid 분류기)", "",
             f"- 분류기 정확도: {correct_pred}/{len(testset)} = {correct_pred/len(testset):.3f}", "",
             "## 전체(micro)", "", "| boost | hit@1 | hit@3 | MRR |", "|---|---|---|---|"]
    for b in BOOST_CANDIDATES:
        ov = results[b]["overall"]
        lines.append(f"| {b} | {ov['hit@1']:.3f} | {ov['hit@3']:.3f} | {ov['mrr']:.3f} |")

    lines += ["", "## 업무별 hit@3", "", "| boost | " + " | ".join(all_domains) + " |",
              "|---|" + "---|" * len(all_domains)]
    for b in BOOST_CANDIDATES:
        row = [f"{results[b]['domains'].get(bf, {}).get('hit@3', 0):.3f}" for bf in all_domains]
        lines.append(f"| {b} | " + " | ".join(row) + " |")

    lines += ["", "## 업무별 MRR", "", "| boost | " + " | ".join(all_domains) + " |",
              "|---|" + "---|" * len(all_domains)]
    for b in BOOST_CANDIDATES:
        row = [f"{results[b]['domains'].get(bf, {}).get('mrr', 0):.3f}" for bf in all_domains]
        lines.append(f"| {b} | " + " | ".join(row) + " |")

    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"{'boost':>6} {'hit@1':>7} {'hit@3':>7} {'MRR':>7} {'chakosongeum_h3':>15}")
    for b in BOOST_CANDIDATES:
        ov = results[b]["overall"]
        ecs = results[b]["domains"].get("착오송금 반환 신청", {}).get("hit@3", 0)
        print(f"{b:>6} {ov['hit@1']:>7.3f} {ov['hit@3']:>7.3f} {ov['mrr']:>7.3f} {ecs:>15.3f}")
    print(f"\n로그 -> {LOG_PATH}")


if __name__ == "__main__":
    main()
