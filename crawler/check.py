import glob, json
for f in glob.glob('data/parsed/*cm-bbs*.json'):
    d = json.load(open(f, encoding='utf-8'))
    print(f, '| _no_container:', d.get('_no_container'), '| text_len:', len(d.get('text', '')))
