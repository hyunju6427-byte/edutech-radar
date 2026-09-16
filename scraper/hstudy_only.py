"""한국교원(hstudy) 전용 로컬 수집기 — 브라우저를 전혀 쓰지 않는다.

GitHub Actions 서버 IP가 hstudy.co.kr에서 차단돼 있어(run.py의 PREFETCHED_SITES 참고),
국내 IP(이 스크립트를 실행하는 PC)에서만 이 사이트를 직접 수집하고,
그 결과를 data/hstudy_raw.json 에 저장한다.

처음엔 scrapers.generic.run_spec(Playwright)로 구현했었는데, Windows 작업 스케줄러로
무인 실행할 때 화면 잠금 등의 이유로 Chromium이 응답 없이 멈추는 문제가 있었다(2026-09-14
자동 트리거 테스트에서 confirm — 10분 뒤 강제종료됨). 이 사이트는 애초에 순수 HTML이라
파싱에 브라우저가 필요 없으므로, urllib + 정규식만으로 완전히 다시 작성해 이 문제를 근본
제거했다(예약 작업/화면 잠금 여부와 무관하게 항상 안정적으로 동작).

사용법(국내 PC에서 매일 실행 — Windows 작업 스케줄러 등):
    cd scraper && python hstudy_only.py
    (이 스크립트는 저장만 하고 git commit/push는 하지 않는다 — run_hstudy_and_push.bat 참고)
"""
import json, os, re, sys, datetime, dataclasses

sys.path.insert(0, os.path.dirname(__file__))
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8')
    except Exception:
        pass

import config
from models import Course
from scrapers.base import clean, parse_credit, parse_hours
from scrapers.generic import _fetch_html

LIST_URL = config.SITES['한국교원']
OUT_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'hstudy_raw.json')

# 카드 구조(실측, 2026-09):
#   <div class="photo" onclick="javascript:detail_view('s1898');return false;" style="...(긴 썸네일 URL)...">
#   ...
#   <div class="title"><span ...>[직무 2학점]</span>&nbsp;<span ... onclick="...">과정명</span></div>
# photo와 title 사이 style 속성(썸네일 경로 포함)이 길어 여유 있게 잡는다.
CARD_RE = re.compile(
    r'class="photo"\s+onclick="javascript:detail_view\(\'(\w+)\'\);return false;"'
    r'.{1,2000}?<div class="title">(.*?)</div>',
    re.S,
)
TAG_RE = re.compile(r'<[^>]+>')
BRACKET_RE = re.compile(r'\[([^\]]+)\]')


def parse(html: str) -> list[Course]:
    today = datetime.date.today().isoformat()
    out = []
    for gcode, title_html in CARD_RE.findall(html):
        text = clean(TAG_RE.sub('', title_html).replace('&nbsp;', ' '))
        m = BRACKET_RE.search(text)
        meta = m.group(1) if m else ''          # 예: "직무 2학점"
        name = clean(BRACKET_RE.sub('', text))   # 대괄호 메타 제거한 나머지가 과정명
        if not name:
            continue
        out.append(Course(
            site='한국교원', name=name,
            credit=parse_credit(meta), hours=parse_hours(meta),
            field_name='', open_month='',
            url=f'https://www.hstudy.co.kr/newmain/subject_view.asp?inx=1&jnx=2&gcode={gcode}',
            course_id=gcode, raw_text=text[:500], first_seen=today,
        ))
    return out


def main():
    html = _fetch_html(LIST_URL)
    courses = parse(html)
    if not courses:
        print('[한국교원] 0건 수집 — 파일을 덮어쓰지 않고 종료(페이지 구조 확인 필요)')
        sys.exit(1)

    payload = {
        'collected_at': datetime.datetime.now().isoformat(timespec='seconds'),
        'count': len(courses),
        'courses': [dataclasses.asdict(c) for c in courses],
    }
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=0)
    print(f'[한국교원] {len(courses)}건 수집 → {OUT_PATH} 저장')


if __name__ == '__main__':
    main()
