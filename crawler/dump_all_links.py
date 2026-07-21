from bs4 import BeautifulSoup
import glob

found_any = False
for f in sorted(glob.glob('data/raw/*.html')):
    if 'fins' in f:
        continue  # fins는 컨테이너 자체가 없으니 일단 제외
    html = open(f, encoding='utf-8', errors='replace').read()
    soup = BeautifulSoup(html, 'lxml')
    container = soup.select_one('.contents')
    if not container:
        continue
    links = container.find_all('a', href=True)
    if links:
        found_any = True
        print(f"\n=== {f} ({len(links)}개 링크) ===")
        for a in links[:15]:
            text = a.get_text(' ', strip=True)[:40]
            print(f"  '{text}' -> {a['href'][:90]}")

if not found_any:
    print("www 페이지 .contents 안에 <a href> 링크가 단 하나도 없습니다.")
