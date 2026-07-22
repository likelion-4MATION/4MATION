import json
from collections import Counter

ch = [json.loads(l) for l in open("data/chunks.jsonl", encoding="utf-8") if l.strip()]
pdocs = set(c["parent_doc_id"] for c in ch)
ts = [json.loads(l) for l in open("data/testset_merged.jsonl", encoding="utf-8") if l.strip()]

missing = Counter()
qam = 0
for d in ts:
    gd = d["gt_docs"]
    if all(g not in pdocs for g in gd):
        qam += 1
    for g in gd:
        if g not in pdocs:
            missing.update([g])

out = []
out.append(f"corpus_parent_docs={len(pdocs)}")
out.append(f"total_testset={len(ts)}")
out.append(f"questions_with_ALL_GT_missing_from_corpus={qam}")
out.append("---- GT docs referenced by testset but NOT in corpus (count x id) ----")
for k, v in missing.most_common(30):
    out.append(f"{v} x {k}")
open("data/gt_check.txt", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("written data/gt_check.txt")
