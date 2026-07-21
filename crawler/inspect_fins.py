from bs4 import BeautifulSoup

html = open('data/raw/kdic-fins-ir-aplygudn-MtrsGvbkSprtProc-selectScrn.html', encoding='utf-8').read()
soup = BeautifulSoup(html, 'lxml')

print("title:", soup.title.get_text() if soup.title else None)
print("전체 길이:", len(html))
print()

print("--- id 또는 class에 'cont'/'view'/'article'/'wrap' 포함된 요소들 ---")
for el in soup.find_all(True):
    id_ = el.get('id', '')
    cls = ' '.join(el.get('class', []))
    combined = (id_ + ' ' + cls).lower()
    if any(k in combined for k in ['cont', 'view', 'article', 'wrap', 'body']):
        text_preview = el.get_text(' ', strip=True)[:40]
        print(f"<{el.name}> id={id_!r} class={cls!r}  text={text_preview!r}")
