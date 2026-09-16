"""4개 연수원 SiteSpec 등록소 (라이브 카드 구조로 확정)."""
import config
from scrapers.generic import SiteSpec

# ── 티처빌 ── 카드: div.info-box / ID: .info-item[data-seq] / href 없음(onclick)
# 상세URL: 과정명(p.text) 클릭 시 실제 이동 결과를 확인해 확정(division=T, t=G005는 카테고리 무관 고정값으로 실측 확인됨).
TEACHERVILLE = SiteSpec(
    site="티처빌",
    list_url=config.SITES["티처빌"],
    wait_selector="div.info-box",
    card="div.info-box",
    require_sel=".info-item[data-seq]",
    name_sel="p.text",
    field_sel=".title > span",
    meta_sel=".title strong",          # "[모듈, 5차시, 300분]" / "[직무, 60차시, 4학점]"
    id_attr="data-seq",
    id_sel=".info-item",
    link_sel="a",
    url_template="https://www.teacherville.co.kr/trainapply/newCourseDetail.edu?division=T&courseSeq={id}&t=G005",
    more_selector="text=더보기, text=더 보기, .btn_more, .btn-more, .more, button.more, a.more, .list_more, .paging_more, .btnMore, .moreBtn",
)

# ── 아이스크림 ── 카드: a.tit 가진 <li> / 상세href: a.thumb_lnk 의 crsCode
ISCREAM = SiteSpec(
    site="아이스크림",
    list_url=config.SITES["아이스크림"],
    wait_selector="a.tit",
    card="li:has(a.tit)",
    name_sel="a.tit",
    field_sel=".crs_info span:nth-of-type(2)",
    meta_sel=".crs_info",              # "15차시(1학점)"
    link_sel="a.thumb_lnk",
    more_selector="#divMore, text=더보기, .btn_more, .btn-more, .more, button.more, a.more",
)

# ── 한국교원 ── td.left 카드 / ID: .photo onclick detail_view('s1898') / 분야 미표기
# 상세URL: 사이트 JS의 detail_view(gcode)는 보통 subject_view.asp?inx=1&jnx=2&gcode=<gcode>로 이동(실측 확인).
# 단, 사이트 JS에 소수(~15개) gcode는 group.asp/institutionView.asp 등 다른 페이지로 하드코딩 예외 처리되어 있어
# 그 과정들만 링크가 틀릴 수 있음 — 현재 SKIP_SITES(IP차단, 수동입력)라 당장 영향은 없음.
HSTUDY = SiteSpec(
    site="한국교원",
    list_url=config.SITES["한국교원"],
    wait_selector="td.left .title",
    card="td.left:has(.title)",
    name_sel=".title span:last-of-type",
    meta_sel=".title",                 # [2학점] → 학점2, 시간 ×15 환산
    field_sel="",
    id_sel=".photo",
    id_attr="onclick",
    link_sel="a",
    url_template="https://www.hstudy.co.kr/newmain/subject_view.asp?inx=1&jnx=2&gcode={id}",
    more_selector="",
    http_html=True,      # hstudy는 브라우저 접속이 막혀 직접 HTTP로 HTML을 받아 파싱
)

# ── 사제동행 ── tr 행: td1=학점, td2=분야, .tableLecName=과정명/링크(classKey)
EDUCATION = SiteSpec(
    site="사제동행",
    list_url=config.SITES["사제동행"],
    wait_selector=".tableLecName",
    card="tr:has(.tableLecName)",
    name_sel=".tableLecName a",
    meta_sel="td:nth-of-type(1)",      # "4학점" → 학점4, 시간 ×15=60
    field_sel="td:nth-of-type(2)",
    link_sel=".tableLecName a",
    more_selector="",
)

# ── 교육사랑 ── 카드: div.lecture-box / 학점·차시는 카드 전체 텍스트에서 파싱 / onclick detail_view('gcode')
# 한국교원과 같은 제작사 플랫폼(같은 detail_view 패턴)이지만, 여기는 예외 없이 항상
# subject_view.asp?gcode=...&inx=1&jnx=0 로 고정. 실제 브라우저 접속은 "지원되는 Browser가 아닙니다"로
# 차단되지만(자동화 탐지로 추정) 순수 HTTP GET은 막히지 않아 http_html 모드로 우회.
EDULOVE = SiteSpec(
    site="교육사랑",
    list_url=config.SITES["교육사랑"],
    wait_selector="div.lecture-box",
    card="div.lecture-box",
    name_sel=".subject_title1",
    field_sel=".flag-cate",
    id_sel=".subject_title1",
    id_attr="onclick",
    url_template="https://www.edulove.co.kr/main/subject_view.asp?gcode={id}&inx=1&jnx=0",
    more_selector="",
    http_html=True,
)

# ── T셀파 ── 카드: ul.tla_list > li / 학점 표기 없음(시간만) / onclick detail(2014) 숫자ID
# 목록 페이지가 서버에서 이미 전체 렌더링돼 있어 더보기/스크롤 불필요(정적 HTML에도 카드 존재 확인).
TSHERPA = SiteSpec(
    site="T셀파",
    list_url=config.SITES["T셀파"],
    wait_selector="ul.tla_list",
    card="#productListArea ul.tla_list li",
    name_sel=".tla_msg a",
    field_sel="",
    meta_sel="",   # "N시간"만 있고 학점 표기가 따로 없어 카드 전체 텍스트에서 파싱
    id_sel=".tla_msg a",
    id_attr="onclick",
    url_template="https://edu.tsherpa.co.kr/Product/Detail/{id}",
    more_selector="",
)

# ── 카운피아 ── 카드: div.lecture_list[data-course-id] / 학점(차시)는 .sort 안에 표기
# list_url이 리스트(카테고리별 페이지 6개) — config.py 참고. 카테고리당 카드 수가 16으로 고르게
# 찍히는 곳이 있어 페이지당 상한(더보기/페이지네이션)이 있을 가능성 있음 — 추후 숫자가 안 늘면 재점검.
COUNPIA = SiteSpec(
    site="카운피아",
    list_url=config.SITES["카운피아"],
    wait_selector="div.lecture_list",
    card="div.lecture_list",
    name_sel=".tit",
    meta_sel=".sort",           # "1학점(15차시)"
    field_sel=".ncs_3cha",
    id_attr="data-course-id",
    url_template="https://counpia.com/ncs/main_lecture.html?course_id={id}",
    more_selector="",
)

# ── 에듀니티 ── 카드: div.newclass / 진짜 href(a[href*=/preview/?p_subj=]) 있어 id_attr 불필요
# 학점·주제 표기가 카드에 없음(항상 공란) — 비바샘과 같은 성격의 제약.
# 과정명에 "[상시연수]"/"-직무" 꼬리표가 붙어 나옴(이 목록 자체가 "직무&상시연수" 필터라 전부 동일하게
# 붙음, 정보성 없음) — 기존 데이터와 이름을 맞추려면 제거해야 함. "[초등]"/"[중등]" 등 다른 대괄호
# 태그는 실제 제목의 일부라 그대로 둔다.
EDUNIETY = SiteSpec(
    site="에듀니티",
    list_url=config.SITES["에듀니티"],
    wait_selector="div.newclass",
    card="div.newclass",
    name_sel="li:not(.img) a[href*='/preview/']",  # 썸네일 li의 a는 이미지뿐이라 제외(제목 span 유무가 카드마다 달라 a 전체를 잡음)
    link_sel="a[href*='/preview/']",
    name_strip_re=r"\[상시연수\]\s*|-직무$",
    more_selector="",
)

# ── 유니텔 ── 옛날 테이블 레이아웃, 카드: tr:has(a.renew) / onclick viewCourse('코드')
# 학점 표기가 행 안에 없고 목록 URL(카테고리)이 곧 학점 — config.UNITEL_LIST_CREDIT 참고.
# 시간 정보도 목록에 없어 공란(상세페이지까지 들어가야 하는데 카탈로그 전체엔 부담이 커 보류).
UNITEL = SiteSpec(
    site="유니텔",
    list_url=config.SITES["유니텔"],
    list_url_credit=config.UNITEL_LIST_CREDIT,
    wait_selector="a.renew",
    card="tr:has(a.renew)",
    name_sel="a.renew",
    id_sel="a.renew",
    id_attr="onclick",
    url_template="https://www.teacher.co.kr/index.do/apply/view_course/{id}",
    more_selector="",
)

SPECS = {
    "티처빌": TEACHERVILLE,
    "아이스크림": ISCREAM,
    "한국교원": HSTUDY,
    "사제동행": EDUCATION,
    "교육사랑": EDULOVE,
    "T셀파": TSHERPA,
    "카운피아": COUNPIA,
    "에듀니티": EDUNIETY,
    "유니텔": UNITEL,
}
