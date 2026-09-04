"""과정 데이터 모델."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Course:
    site: str                 # 연수원 이름 (예: '티처빌')
    name: str                 # 과정명
    credit: str = ""          # 학점
    hours: str = ""           # 시간
    field_name: str = ""      # 연수분야(주제)
    open_month: str = ""      # 신규오픈월(YYYY-MM). 사이트에 없으면 감지월
    url: str = ""             # 상세 URL
    course_id: str = ""       # 사이트 내부 ID(있으면 참고용)
    raw_text: str = ""        # 카드 원문(파싱 실패 대비)
    first_seen: str = ""      # 최초 감지일

    def key(self) -> str:
        # 과정명 기반 키(공백 제거·소문자) — 기존 백필과 라이브 수집이 같은 키로 합쳐지도록 통일
        return self.site + "::" + re.sub(r"\s+", "", self.name or "").lower()
