"""facet(business_function) 분류기 정확도 재진단 — bge-m3 기준.

07-22 세션에서 ko-sroberta 임베딩 기준 centroid 분류기가 정확도 58.5%에 그쳐
하드필터(hit@3 최대 -4.3%p)·소프트부스트(net 이득 없음) 둘 다 미채택됐다
(DECISIONS.md 참고). 이후 임베딩 모델을 bge-m3로 교체했고 dense 단독 성능도
크게 개선됐으므로(hit@3 .665→.845), facet boost를 재검토하기 전에 **분류기
정확도부터 재확인**한다 — 이전과 같은 취약점(분류기 품질)이 재현되는지,
아니면 bge-m3 덕에 개선됐는지 먼저 진단(추측 금지, 매 단계 실측).

방법: 현재 프로덕션 인덱스(data/index/emb.npy, chunk_meta.jsonl)의 청크 임베딩을
business_function별로 평균해 centroid를 만들고, 400건 테스트 질의 임베딩과의
코사인 유사도로 top-1 예측 → 실제 gt 업무영역과 비교.

사용: python diagnose_facet_classifier.py
"""

from __future__ import annotations

import collections
import json

import numpy as np

import rag


def main() -> None:
    chunks = [json.loads(l) for l in open("data/index/chunk_meta.jsonl", encoding="utf-8")]
    embs = np.load("data/index/emb.npy")
    testset = [json.loads(l) for l in open("data/testset_natural_400_v3.jsonl", encoding="utf-8")]

    by_bf: dict[str, list[int]] = collections.defaultdict(list)
    for i, c in enumerate(chunks):
        by_bf[c["business_function"]].append(i)

    centroids: dict[str, np.ndarray] = {}
    for bf, idxs in by_bf.items():
        v = embs[idxs].mean(axis=0)
        v = v / (np.linalg.norm(v) + 1e-9)
        centroids[bf] = v

    bf_names = sorted(centroids)
    cent_mat = np.stack([centroids[b] for b in bf_names])

    correct = 0
    confusion = collections.Counter()
    per_true = collections.Counter()
    per_true_correct = collections.Counter()
    margins = []
    for it in testset:
        q = rag.embed_texts([it["question"]])[0]
        sims = cent_mat @ q
        order = np.argsort(sims)[::-1]
        pred = bf_names[order[0]]
        true = it["business_function"]
        per_true[true] += 1
        top2_margin = sims[order[0]] - sims[order[1]]
        margins.append(top2_margin)
        if pred == true:
            correct += 1
            per_true_correct[true] += 1
        else:
            confusion[(true, pred)] += 1

    n = len(testset)
    print(f"분류 대상 업무영역({len(bf_names)}개): {bf_names}")
    print(f"\n전체 정확도: {correct}/{n} = {correct/n:.3f}")
    print(f"top1-top2 평균 마진: {np.mean(margins):.4f} (마진이 작을수록 오분류 위험)")
    print("\n업무별 정확도:")
    for bf in sorted(per_true, key=lambda b: per_true_correct[b] / per_true[b]):
        print(f"  {bf:20} n={per_true[bf]:3d}  acc={per_true_correct[bf]/per_true[bf]:.3f}")
    print("\n혼동 top 10 (true -> pred):")
    for (true, pred), cnt in confusion.most_common(10):
        print(f"  {true} -> {pred}: {cnt}")


if __name__ == "__main__":
    main()
