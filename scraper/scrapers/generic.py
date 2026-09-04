"""SiteSpec 하나로 사이트를 기술하면 공통 로직이 과정 목록을 뽑아준다."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from urllib.parse import urljoin

from models import Course
from scrapers.base import (browser_page, load_all, clean,
                           parse_credit, parse_hours, parse_open_month)

_ID_IN_URL = re.compile(r"(?:classKey|courseSeq|crsId|crsCd|seq|code|id|no|key)=([\w-]+)", re.I)
_ID_IN_CALL = re.compile(r"""['"]([\w-]+)['"]""")


@dataclass
class SiteSpec:
    site: str
    list_url: str
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

    with browser_page() as page:
        # 느린 사이트(예: 한국교원) 대응: 60초 + 재시도 + 완화된 로딩 판정
        page.set_default_navigation_timeout(60000)
        nav_ok = False
        for attempt in range(2):
            try:
                page.goto(spec.list_url, wait_until="commit", timeout=60000)
                nav_ok = True
                break
            except Exception as e:
                if attempt == 0:
                    page.wait_for_timeout(3000)  # 잠깐 쉬고 한 번 더
                else:
                    raise e
        if not nav_ok:
            return out
        try:
            page.wait_for_selector(spec.wait_selector, timeout=25000)
        except Exception:
            page.wait_for_timeout(4000)  # 셀렉터 못 찾아도 일단 진행
        load_all(page, more_selector=spec.more_selector or None)

        for card in page.query_selector_all(spec.card):
            if spec.require_sel and not card.query_selector(spec.require_sel):
                continue
            raw = clean(card.inner_text())
            if not raw:
                continue

            name = _txt(card, spec.name_sel) or raw.split("\n")[0][:120]
            meta_text = _txt(card, spec.meta_sel) or raw
            link = card.query_selector(spec.link_sel)
            href = link.get_attribute("href") if link else ""
            cid = _course_id(card, href, spec)
            if spec.url_template and cid:
                url = spec.url_template.format(id=cid)
            elif href:
                url = urljoin(spec.list_url, href)
            else:
                url = spec.list_url
            open_month = parse_open_month(_txt(card, spec.open_month_sel) or raw)

            out.append(Course(
                site=spec.site, name=name,
                credit=parse_credit(meta_text), hours=parse_hours(meta_text),
                field_name=_txt(card, spec.field_sel),
                open_month=open_month or this_month,
                url=url, course_id=cid, raw_text=raw[:500], first_seen=today,
            ))
    return out
