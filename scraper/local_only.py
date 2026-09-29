"""국내 IP 전용 로컬 수집기 — 브라우저를 전혀 쓰지 않는다.

GitHub Actions 서버(Azure 해외 IP)에서 접근이 막히거나 응답이 없는 사이트들을
국내 IP(이 스크립트를 실행하는 PC)에서만 직접 수집해서 결과를 data/*_raw.json 에 저장한다.
run.py(GitHub Actions 쪽)는 PREFETCHED_SITES 설정에 따라 이 파일들을 읽어 병합한다.

대상(2026-09-29 기준, 실제 Actions 로그로 확인됨):
  - 한국교원(hstudy.co.kr): GET/POST 모두 응답 없음(IP 차단으로 추정, 이전부터 알려짐)
  - 교육사랑(edulove.co.kr): 순수 HTTP GET도 브라우저 navigate도 전부 60초 타임아웃
  - T셀파(edu.tsherpa.co.kr): 브라우저 navigate가 60초 타임아웃(정적 HTML 자체엔 목록이 있어
    브라우저 없이도 파싱 가능 — 애초에 브라우저가 필요 없던 사이트라 이 참에 같이 옮김)
  이 세 곳 다 국내 IP(사용자 PC)에서는 전부 정상 응답한다.

전부 처음엔 scrapers.generic.run_spec(Playwright)로 구현했었는데, Windows 작업 스케줄러로
무인 실행할 때 화면 잠금 등의 이유로 Chromium이 응답 없이 멈추는 문제가 있었다(한국교원에서
2026-09-14 자동 트리거 테스트로 confirm — 10분 뒤 강제종료됨). 셋 다 순수 HTML이라 파싱에
브라우저가 필요 없으므로, urllib + 정규식만으로 작성해 이 문제를 근본 제거했다(예약 작업/화면
잠금 여부와 무관하게 항상 안정적으로 동작).

사용법(국내 PC에서 매일 실행 — Windows 작업 스케줄러 등):
    cd scraper && python local_only.py
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

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
TAG_RE = re.compile(r'<[^>]+>')
BRACKET_RE = re.compile(r'\[([^\]]+)\]')


# ── 한국교원 ──────────────────────────────────────────────────────────
# 카드: <div class="photo" onclick="javascript:detail_view('s1898');return false;" style="...">
#       ... <div class="title"><span>[직무 2학점]</span>&nbsp;<span onclick="...">과정명</span></div>
HSTUDY_CARD_RE = re.compile(
    r'class="photo"\s+onclick="javascript:detail_view\(\'(\w+)\'\);return false;"'
    r'.{1,2000}?<div class="title">(.*?)</div>',
    re.S,
)


def collect_hstudy() -> list[Course]:
    today = datetime.date.today().isoformat()
    html = _fetch_html(config.SITES['한국교원'])
    out = []
    for gcode, title_html in HSTUDY_CARD_RE.findall(html):
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


# ── 교육사랑 ──────────────────────────────────────────────────────────
# 카드: class="lecture-box ..." 로 시작하는 블록 안에
#   <span class='flag-point1'>1학점</span> <span class="flag-cate">디지털활용</span>
#   <div class="subject_title1 ..." onclick="javascript:detail_view('s0760');">제목</div>
#   <div class="subject_title2 ...">15시간 / ...</div>
EDULOVE_CARD_SPLIT_RE = re.compile(r'class="lecture-box')
EDULOVE_TITLE_RE = re.compile(
    r'class="subject_title1[^"]*"[^>]*onclick="javascript:detail_view\(\'(\w+)\'\);"[^>]*>([^<]*)</div>')
EDULOVE_HOURS_RE = re.compile(r'class="subject_title2[^"]*"[^>]*>([^<]*)</div>')
EDULOVE_FIELD_RE = re.compile(r'class="flag-cate">([^<]*)</span>')
EDULOVE_CREDIT_RE = re.compile(r"flag-point1'>([^<]*)</span>")


def collect_edulove() -> list[Course]:
    today = datetime.date.today().isoformat()
    html = _fetch_html(config.SITES['교육사랑'])
    out = []
    for chunk in EDULOVE_CARD_SPLIT_RE.split(html)[1:]:
        m = EDULOVE_TITLE_RE.search(chunk)
        if not m:
            continue
        cid, name = m.group(1), clean(m.group(2))
        if not name:
            continue
        hm = EDULOVE_HOURS_RE.search(chunk)
        cm = EDULOVE_CREDIT_RE.search(chunk)
        fm = EDULOVE_FIELD_RE.search(chunk)
        meta = (cm.group(1) if cm else '') + ' ' + (hm.group(1) if hm else '')
        out.append(Course(
            site='교육사랑', name=name,
            credit=parse_credit(meta), hours=parse_hours(meta),
            field_name=clean(fm.group(1)) if fm else '', open_month='',
            url=f'https://www.edulove.co.kr/main/subject_view.asp?gcode={cid}&inx=1&jnx=0',
            course_id=cid, raw_text=name[:500], first_seen=today,
        ))
    return out


# ── T셀파 ────────────────────────────────────────────────────────────
# 카드: <li><div class="img_area">...<span class="line time">5시간</span>...</div>
#           <p class="tla_msg"><a href="#" onclick="javascript:detail(2014);">제목</a></p></li>
# #productListArea 안의 목록만(위쪽 "BEST PICK" 추천 위젯은 같은 detail() 패턴을 재사용하므로 제외).
TSHERPA_CARD_SPLIT_RE = re.compile(r'<li>\s*<div class="img_area">')
TSHERPA_NAME_RE = re.compile(
    r'<p class="tla_msg"><a href="#" onclick="javascript:detail\((\d+)\);">([^<]*)</a></p>')
TSHERPA_HOURS_RE = re.compile(r'class="line time">([^<]*)</span>')


def collect_tsherpa() -> list[Course]:
    today = datetime.date.today().isoformat()
    html = _fetch_html(config.SITES['T셀파'])
    idx = html.find('id="productListArea"')
    scope = html[idx:] if idx >= 0 else html
    out = []
    for chunk in TSHERPA_CARD_SPLIT_RE.split(scope)[1:]:
        m = TSHERPA_NAME_RE.search(chunk)
        if not m:
            continue
        cid, name = m.group(1), clean(m.group(2))
        if not name:
            continue
        hm = TSHERPA_HOURS_RE.search(chunk)
        meta = hm.group(1) if hm else ''
        out.append(Course(
            site='T셀파', name=name,
            credit=parse_credit(meta), hours=parse_hours(meta),
            field_name='', open_month='',
            url=f'https://edu.tsherpa.co.kr/Product/Detail/{cid}',
            course_id=cid, raw_text=name[:500], first_seen=today,
        ))
    return out


SITES = {
    '한국교원': ('hstudy_raw.json', collect_hstudy),
    '교육사랑': ('edulove_raw.json', collect_edulove),
    'T셀파': ('tsherpa_raw.json', collect_tsherpa),
}


def main():
    any_fail = False
    any_ok = False
    for name, (filename, collect_fn) in SITES.items():
        try:
            courses = collect_fn()
        except Exception as e:
            print(f'[{name}] 수집 오류: {e} — 이 파일은 건너뜀, 기존 파일 유지')
            any_fail = True
            continue
        if not courses:
            print(f'[{name}] 0건 수집 — 파일을 덮어쓰지 않고 건너뜀(페이지 구조 확인 필요)')
            any_fail = True
            continue
        payload = {
            'collected_at': datetime.datetime.now().isoformat(timespec='seconds'),
            'count': len(courses),
            'courses': [dataclasses.asdict(c) for c in courses],
        }
        out_path = os.path.join(DATA_DIR, filename)
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=0)
        print(f'[{name}] {len(courses)}건 수집 → {out_path} 저장')
        any_ok = True

    # 하나라도 성공했으면 그 파일들은 커밋할 가치가 있으니 정상 종료(0)한다 — 배치스크립트가
    # 이 exit code로 "전부 건너뛸지"를 판단하는 게 아니라 파일별로 이미 알아서 건너뛰기 때문.
    # 전부 실패했을 때만 실패로 표시(호출자가 로그를 남기도록).
    if any_fail and not any_ok:
        sys.exit(1)


if __name__ == '__main__':
    main()
