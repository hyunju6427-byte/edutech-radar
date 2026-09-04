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


def load_all(page, more_selector: str | None = None, scroll: bool = True,
             max_rounds: int | None = None):
    """'더보기' 버튼 반복 클릭 + 스크롤로 지연 로딩 목록을 펼친다."""
    rounds = config.MAX_LOAD_MORE if max_rounds is None else max_rounds
    for _ in range(rounds):
        changed = False
        if more_selector:
            btn = page.query_selector(more_selector)
            if btn and btn.is_visible():
                try:
                    btn.click()
                    page.wait_for_timeout(800)
                    changed = True
                except Exception:
                    pass
        if scroll:
            before = page.evaluate("document.body.scrollHeight")
            page.mouse.wheel(0, 20000)
            page.wait_for_timeout(600)
            after = page.evaluate("document.body.scrollHeight")
            if after > before:
                changed = True
        if not changed:
            break
