html = open('data/raw/kdic-fins-cm-bbs-selectFaqNramtAply.html', encoding='utf-8').read()
print("길이:", len(html))
print("--- 앞부분 1000자 ---")
print(html[:1000])
print("--- 오류/대기열 마커 검색 ---")
for marker in ["오류 | KDIC", "error404", "서비스 접속 대기", "이용자수가 많아", "접속이 차단", "요청하신 페이지를 찾을 수 없습니다"]:
    if marker in html:
        print(f"  발견: {marker!r}")
