import json

chunks = [json.loads(l) for l in open('data/chunks.jsonl', encoding='utf-8')]
with_att = [c for c in chunks if c.get('has_attachments')]

print(f"전체 청크: {len(chunks)}건")
print(f"첨부 보유 청크: {len(with_att)}건")
print()

print("--- 첨부 보유 청크 상세 (최대 10건) ---")
for c in with_att[:10]:
    print(f"\nchunk_id: {c['chunk_id']}")
    print(f"  business_function: {c['business_function']}")
    print(f"  page_title: {c['page_title']}")
    for a in c['attachments']:
        print(f"  - [{a['doc_kind']}/{a['file_type']}] {a['name']} -> {a['url']}")

print()
print("--- 업무별 첨부 보유 청크 수 ---")
from collections import Counter
cnt = Counter(c['business_function'] for c in with_att)
for biz, n in cnt.most_common():
    print(f"  {biz}: {n}건")
