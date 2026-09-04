"""스크레이퍼 공통 기반: 브라우저 컨텍스트 + 한국어 텍스트 파서."""
from __future__ import annotations

import re
from contextlib import contextmanager

from playwright.sync_api import sync_playwright

import config

_CREDIT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*학점")
_HOUR_RE = re.compile(r"(\d+)\s*시간")
_CHASI_RE = re.compile(r"(\d+)\s*차시")
_MIN_RE = re.compile(r"(\d+)\s*분")
_MONTH_RE = re.compile(r"(20\d{2})\s*[.\-/년]\s*(\d{1,2})")


def parse_credit(text: str) -> str:
    m = _CREDIT_RE.search(text or "")
    return m.group(1) if m else ""


def parse_hours(text: str) -> str:
    """시간 → 차시 → 분(÷60) → 학점(×15) 순으로 추정."""
    text = text or ""
    m = _HOUR_RE.search(text)
    if m:
        return m.group(1)
    m = _CHASI_RE.search(text)
    if m:
        return m.group(1)
    m = _MIN_RE.search(text)
    if m:
        return str(round(int(m.group(1)) / 60))
    c = parse_credit(text)
    if c:
        try:
            return str(int(float(c) * 15))
        except ValueError:
            pass
    return ""


def parse_open_month(text: str) -> str:
    m = _MONTH_RE.search(text or "")
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}"
    return ""


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").replace("\xa0", " ")).strip()


_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


@contextmanager
def browser_page(headless: bool | None = None):
    headless = config.HEADLESS if headless is None else headless
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context(user_agent=_UA, locale="ko-KR",
                                  viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page.set_default_timeout(config.PAGE_TIMEOUT_MS)
        try:
            yield page
        finally:
            browser.close()


def load_all(page, more_selector: str | None = None, card_selector: str | None = None,
             scroll: bool = True, max_rounds: int | None = None):
    """'더보기' 버튼 반복 클릭 + 스크롤로 전체 목록을 펼친다.
    카드 개수가 더 늘지 않으면 종료(무한 반복 방지). {clicks, count} 반환."""
    rounds = config.MAX_LOAD_MORE if max_rounds is None else max_rounds
    candidates = [s.strip() for s in (more_selector or "").split(",") if s.strip()]

    def count():
        if not card_selector:
            return -1
        try:
            return len(page.query_selector_all(card_selector))
        except Exception:
            return -1

    clicks = 0
    last = count()
    stale = 0  # 카드가 안 늘어난 라운드 누적
    for _ in range(rounds):
        # 1) '더보기' 후보들 중 보이는 첫 버튼 클릭
        btn = None
        for sel in candidates:
            try:
                b = page.query_selector(sel)
            except Exception:
                b = None
            if b and b.is_visible():
                btn = b
                break
        if btn:
            try:
                btn.scroll_into_view_if_needed(timeout=2000)
                btn.click(timeout=3000)
                clicks += 1
            except Exception:
                try:
                    page.evaluate("(el)=>el.click()", btn)
                    clicks += 1
                except Exception:
                    pass
        # 2) 스크롤(무한 스크롤 대응)
        if scroll:
            page.mouse.wheel(0, 30000)
        page.wait_for_timeout(900)
        # 3) 진행 판정은 '카드가 늘었는지'로만 한다(버튼만 남아 헛클릭하는 것 방지)
        cur = count()
        if card_selector:
            if cur > last:
                last = cur
                stale = 0
            else:
                stale += 1
            if stale >= 2:      # 2회 연속 안 늘면 종료
                break
            if not btn and cur == last:  # 누를 것도 없고 안 늘면 종료
                break
        else:
            if not btn:         # 카드 기준이 없으면 버튼 없을 때 종료
                break
    return {"clicks": clicks, "count": last if last >= 0 else None}
