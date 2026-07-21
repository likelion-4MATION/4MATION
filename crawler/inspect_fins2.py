from bs4 import BeautifulSoup

html = open('data/raw/kdic-fins-ir-aplygudn-MtrsGvbkSprtProc-selectScrn.html', encoding='utf-8').read()
soup = BeautifulSoup(html, 'lxml')

# SPA 프레임워크 마운트 지점 흔적 확인
print("--- id 속성 전체 목록 (상위 40개) ---")
ids = [el.get('id') for el in soup.find_all(id=True)]
for i in ids[:40]:
    print(" ", i)

print()
print("--- body 직속 자식 태그들 ---")
if soup.body:
    for child in soup.body.find_all(recursive=False):
        print(f"<{child.name}> id={child.get('id')!r} class={child.get('class')!r}")

print()
print("--- 실제 안내 문구('착오송금') 포함 여부 ---")
print("착오송금" in html)
