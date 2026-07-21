import json, glob

total = 0
docs_with_att = []
for f in glob.glob('data/parsed/*.json'):
    d = json.load(open(f, encoding='utf-8'))
    atts = d.get('attachments', [])
    if atts:
        docs_with_att.append((f, atts))
        total += len(atts)

print(f"파서 단계에서 첨부 발견 문서: {len(docs_with_att)}건 / 총 {total}개")
for f, atts in docs_with_att:
    print(f, "->", [a['name'] for a in atts])
