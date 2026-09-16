"""SiteSpec 하나로 사이트를 기술하면 공통 로직이 과정 목록을 뽑아준다."""
from __future__ import annotations

import re
import urllib.request
from dataclasses import dataclass
from datetime import date
from urllib.parse import urljoin

from models import Course
from scrapers.base import (browser_page, load_all, clean,
                           parse_credit, parse_hours, parse_open_month)

_ID_IN_URL = re.compile(r"(?:classKey|courseSeq|crsId|crsCd|seq|code|id|no|key)=([\w-]+)", re.I)
# onclick="fn('s1898')" 처럼 따옴표 있는 문자열 ID, onclick="fn(2014)" 처럼 따옴표 없는 숫자 ID 둘 다 지원.
# 여는 괄호 바로 뒤 첫 인자에 고정해서(다른 곳의 우연한 단어와 잘못 매칭되는 것 방지).
_ID_IN_CALL = re.compile(r"""\(\s*['"]?([\w-]+)['"]?\s*[,)]""")


def _fetch_html(url: str) -> str:
    """브라우저 없이 직접 HTTP GET으로 HTML을 받아온다(EUC-KR 자동 처리).
    브라우저 자동화를 차단하는 서버 대응용."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
        ct = (r.headers.get("Content-Type") or "").lower()
    enc = "euc-kr" if ("euc-kr" in ct or "ks_c_5601" in ct) else "utf-8"
    try:
        return raw.decode(enc, errors="replace")
    except Exception:
        return raw.decode("utf-8", errors="replace")


@dataclass
class SiteSpec:
    site: str
    list_url: str | list[str]   # 카테고리가 나뉜 사이트는 리스트로 여러 페이지를 지정(예: 카운피아)
    wait_selector: str
    card: str
    name_sel: str = ""
    field_sel: str = ""
    meta_sel: str = ""
    open_month_sel: str = ""
    link_sel: str = "a"
    id_attr: str = ""
    id_sel: str = ""
    url_template: str = ""
    require_sel: str = ""
    more_selector: str = ""
    http_html: bool = False   # True면 브라우저 대신 직접 HTTP로 HTML을 받아 파싱(봇 차단 우회)
    name_strip_re: str = ""   # 과정명에 붙는 사이트 고유 꼬리표 제거용 정규식(예: 에듀니티 "[상시연수]"/"-직무")


def _txt(node, sel: str) -> str:
    if not sel:
        return ""
    el = node.query_selector(sel)
    return clean(el.inner_text()) if el else ""


def _course_id(card, link_href: str, spec: SiteSpec) -> str:
    if spec.id_attr:
        target = card.query_selector(spec.id_sel) if spec.id_sel else card
        v = target.get_attribute(spec.id_attr) if target else None
        if v:
            if "(" in v:                       # onclick 등 함수호출 → 첫 인자
                m = _ID_IN_CALL.search(v)
                if m:
                    return m.group(1)
            else:
                return v
    if link_href:
        m = _ID_IN_URL.search(link_href)
        if m:
            return m.group(1)
    return ""


def run_spec(spec: SiteSpec) -> list[Course]:
    today = date.today().isoformat()
    this_month = today[:7]
    out: list[Course] = []
    seen_ids: set[str] = set()   # list_url이 여러 개일 때 카테고리 간 중복(교차 등록) 방지

    list_urls = spec.list_url if isinstance(spec.list_url, (list, tuple)) else [spec.list_url]

    with browser_page() as page:
        page.set_default_navigation_timeout(60000)
        for list_url in list_urls:
            # http_html=True면 직접 HTTP로 HTML을 받아 렌더링(브라우저 자동화 차단 우회). 실패 시 goto로 폴백.
            prefetched = None
            if spec.http_html:
                try:
                    prefetched = _fetch_html(list_url)
                except Exception:
                    prefetched = None

            if prefetched:
                page.set_content(prefetched, wait_until="domcontentloaded")
            else:
                nav_ok = False
                for attempt in range(2):
                    try:
                        page.goto(list_url, wait_until="commit", timeout=60000)
                        nav_ok = True
                        break
                    except Exception as e:
                        if attempt == 0:
                            page.wait_for_timeout(3000)
                        else:
                            raise e
                if not nav_ok:
                    continue
            try:
                page.wait_for_selector(spec.wait_selector, timeout=25000)
            except Exception:
                page.wait_for_timeout(4000)
            load_info = load_all(page, more_selector=spec.more_selector or None,
                                  card_selector=spec.card)
            if spec.more_selector:
                print(f"  [{spec.site}] 더보기 {load_info['clicks']}회 · 로드 {load_info['count']}개")

            for card in page.query_selector_all(spec.card):
                if spec.require_sel and not card.query_selector(spec.require_sel):
                    continue
                raw = clean(card.inner_text())
                if not raw:
                    continue

                name = _txt(card, spec.name_sel) or raw.split("\n")[0][:120]
                if spec.name_strip_re:
                    name = clean(re.sub(spec.name_strip_re, "", name))
                meta_text = _txt(card, spec.meta_sel) or raw
                link = card.query_selector(spec.link_sel)
                href = link.get_attribute("href") if link else ""
                cid = _course_id(card, href, spec)
                if spec.url_template and cid:
                    url = spec.url_template.format(id=cid)
                elif href:
                    url = urljoin(list_url, href)
                else:
                    url = ""   # 상세 URL을 못 찾으면 비워둔다(목록 URL을 넣으면 "상세 링크 있음"으로 오인됨)

                dedupe_key = cid or name
                if dedupe_key in seen_ids:
                    continue
                seen_ids.add(dedupe_key)

                open_month = parse_open_month(_txt(card, spec.open_month_sel) or raw)

                out.append(Course(
                    site=spec.site, name=name,
                    credit=parse_credit(meta_text), hours=parse_hours(meta_text),
                    field_name=_txt(card, spec.field_sel),
                    open_month=open_month or this_month,
                    url=url, course_id=cid, raw_text=raw[:500], first_seen=today,
                ))
    return out
