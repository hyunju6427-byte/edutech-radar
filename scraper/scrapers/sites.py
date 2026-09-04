"""4개 연수원 SiteSpec 등록소 (라이브 카드 구조로 확정)."""
import config
from scrapers.generic import SiteSpec

# ── 티처빌 ── 카드: div.info-box / ID: .info-item[data-seq] / href 없음(onclick)
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
    link_sel="a",
    more_selector="#divMore, text=더보기, .btn_more, .btn-more, .more, button.more, a.more",
)

# ── 한국교원 ── td.left 카드 / ID: .photo onclick detail_view('s1898') / 분야 미표기
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

SPECS = {
    "티처빌": TEACHERVILLE,
    "아이스크림": ISCREAM,
    "한국교원": HSTUDY,
    "사제동행": EDUCATION,
}
