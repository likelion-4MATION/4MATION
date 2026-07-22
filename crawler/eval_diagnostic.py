"""읽기전용 진단 도구 — 문항별 GT vs Top-3, Hit@1/Hit@3, 미적중 목록.

기존 파일(eval.py/testset_merged.jsonl/chunks.jsonl) 무수정. 신규 산출물만 생성:
  data/diag_full.csv  · 전체 문항 진단 (Excel용)
  data/diag_miss.md   · Miss(hit@3 미적중) 전건 비교표
정답 판정은 eval.py와 동일: top-k 청크의 parent_doc_id 가 gt_docs 에 있으면 적중(문서 단위).
"""
import csv
import json

import rag

TESTSET = "data/testset_merged.jsonl"
K = 10


def load():
    return [json.loads(l) for l in open(TESTSET, encoding="utf-8") if l.strip()]


def prev(t, n=90):
    return " ".join(t.split())[:n]


def main():
    ts = load()
    s = rag.Searcher()
    rows = []
    for i, it in enumerate(ts, 1):
        gt = set(it["gt_docs"])
        gtc = [c for c in s.chunks if c["parent_doc_id"] in gt]
        hits = s.search(it["question"], k=K, mode="hybrid")
        rank = 0
        for r, c in enumerate(hits, 1):
            if c["parent_doc_id"] in gt:
                rank = r
                break
        t = hits[:3]
        rows.append({
            "qid": i, "q": it["question"], "bf": it["business_function"],
            "source": it.get("source", "?"), "gt_docs": ";".join(it["gt_docs"]),
            "gt_chunks": ";".join(c["chunk_id"] for c in gtc[:3]),
            "gt_n": len(gtc),
            "gt_prev": prev(gtc[0]["text"]) if gtc else "(GT청크없음)",
            "rank": rank, "hit1": int(rank == 1), "hit3": int(1 <= rank <= 3),
            "t1": t[0]["chunk_id"] if len(t) > 0 else "",
            "t1s": t[0]["_score"] if len(t) > 0 else "",
            "t2": t[1]["chunk_id"] if len(t) > 1 else "",
            "t2s": t[1]["_score"] if len(t) > 1 else "",
            "t3": t[2]["chunk_id"] if len(t) > 2 else "",
            "t3s": t[2]["_score"] if len(t) > 2 else "",
            "t1p": prev(t[0]["text"], 70) if t else "",
        })
    return rows


def write_csv(rows):
    cols = ["qid", "source", "bf", "q", "gt_docs", "gt_chunks", "gt_n",
            "rank", "hit1", "hit3", "t1", "t1s", "t2", "t2s", "t3", "t3s",
            "gt_prev", "t1p"]
    with open("data/diag_full.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})


def write_miss_md(rows):
    miss = [r for r in rows if not r["hit3"]]
    L = ["# 미적중(Miss) 진단 — hit@3 미포함 전건", "",
         f"- 전체 {len(rows)}건 · Miss {len(miss)}건 · 판정: parent_doc_id ∈ gt_docs (문서 단위)",
         "- rank=0 은 top-10 안에 정답 문서가 전혀 없음(검색 실패), rank>3 은 4위 이하.", "",
         "| QID | source | 업무 | 질문 | rank | GT문서(gt_docs) | Top1(score) | Top2 | Top3 |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in miss:
        L.append(f"| {r['qid']} | {r['source']} | {r['bf']} | {r['q']} | "
                 f"{r['rank'] or '없음'} | {r['gt_docs']} | {r['t1']} ({r['t1s']}) | "
                 f"{r['t2']} | {r['t3']} |")
    L += ["", "## 미리보기 비교 (GT vs Top1)", ""]
    for r in miss:
        L += [f"### QID {r['qid']} · {r['bf']} · {r['source']} · rank={r['rank'] or '없음'}",
              f"- 질문: {r['q']}",
              f"- GT문서: {r['gt_docs']}  (GT청크 {r['gt_n']}개: {r['gt_chunks']})",
              f"- GT preview: {r['gt_prev']}",
              f"- Top1: {r['t1']}  preview: {r['t1p']}", ""]
    open("data/diag_miss.md", "w", encoding="utf-8").write("\n".join(L) + "\n")


def main_run():
    rows = main()
    write_csv(rows)
    write_miss_md(rows)
    n = len(rows)
    h1 = sum(r["hit1"] for r in rows)
    h3 = sum(r["hit3"] for r in rows)
    miss = [r for r in rows if not r["hit3"]]
    zero = [r for r in rows if r["rank"] == 0]
    print(f"total={n} hit@1={h1/n:.3f} hit@3={h3/n:.3f} "
          f"miss={len(miss)} rank0(검색실패)={len(zero)}")
    print("산출: data/diag_full.csv · data/diag_miss.md")


if __name__ == "__main__":
    main_run()
