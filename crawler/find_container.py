from bs4 import BeautifulSoup
import re

html = open('data/raw/kdic-fins-cm-bbs-selectFaqNramtAply.html', encoding='utf-8').read()
soup = BeautifulSoup(html, 'lxml')

print(".contents 존재:", bool(soup.select_one('.contents')))

target = soup.find(string=re.compile("질문시스템 이용 에러|시스템 이용 에러"))
if target:
    el = target.parent
    print("\n--- FAQ 텍스트를 감싸는 상위 태그 체인 ---")
    while el and el.name != '[document]':
        print(el.name, '| id=', el.get('id'), '| class=', el.get('class'))
        el = el.parent
else:
    print("해당 텍스트를 raw HTML에서 못 찾음 — 로그인/세션이 필요한 페이지일 수 있음")
