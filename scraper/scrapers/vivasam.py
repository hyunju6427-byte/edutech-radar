"""비바샘(자사) 실시간 수집 — Next.js 프론트가 쓰는 공개 JSON API를 직접 호출.

다른 9개 사이트와 달리 HTML 스크래핑이 아니라 진짜 REST API라 브라우저가 필요 없고
(순수 HTTP GET), 데이터도 훨씬 깔끔하다(과정코드·학점·차시·분야가 필드로 분리돼 있음).

x-visang-api-key / sitekey 헤더는 로그인 없이 공개 페이지를 열면 프론트엔드 JS 번들에
박혀있는 채로 모든 방문자의 브라우저가 그대로 보내는 값(Network 탭에서 실측 확인) —
사용자 인증 토큰이 아니라 "이 요청을 vivasam 앱이 보냈다"는 정도의 프런트 식별 키다.
"""
import json
import urllib.request
from datetime import date

from models import Course
from scrapers.base import clean, parse_credit, parse_hours

API_URL = "https://tapi.vivasam.com/v1/user/trn-aply/crs"
API_KEY = "c44b2964-6a98-481d-bde6-f878953b8677"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

# crsClsfSeCd -> 상세페이지 URL 경로(https://t.vivasam.com/courses/{path}/{crsCd})
# 010=직무연수, 020=자율연수. 그 외(실시간·오프라인·집합연수 등)는 다른 사이트들과
# 비교 축이 다르다고 보고 제외(다른 9개 사이트도 직무+자율 위주로만 수집 중인 것과 동일 기준).
CATEGORIES = {"010": "job", "020": "self"}

# 주제(분야) 태그 중 제외할 것들 — 특정 연수 상품 라인 이름일 뿐 실제 '주제' 분류가 아니라고
# 판단(사용자 요청, 2026-09). 한 과정이 이 태그만 갖고 있으면 주제가 빈 값이 될 수 있음(다른
# 사이트들도 주제 정보가 없는 경우가 흔해 문제없음).
EXCLUDE_FIELDS = {"샘크리에이티브 연수", "에듀테크 활용연수"}


def _fetch_page(crs_clsf_se_cd: str, page: int) -> dict:
    url = f"{API_URL}?crsClsfSeCd={crs_clsf_se_cd}&page={page}&searchCrdtCd=&sortOrdrType=new"
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "x-visang-api-key": API_KEY,
        "sitekey": "VIVASAM",
        "Referer": "https://t.vivasam.com/",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def collect() -> list[Course]:
    today = date.today().isoformat()
    this_month = today[:7]
    out: list[Course] = []
    seen_ids: set[str] = set()

    for crs_clsf_se_cd, path in CATEGORIES.items():
        page = 0
        while True:
            data = _fetch_page(crs_clsf_se_cd, page)
            for row in data.get("data") or []:
                cid = row.get("crsCd") or ""
                if cid in seen_ids:
                    continue
                name = clean(row.get("crsNm") or "")
                if not name:
                    continue
                seen_ids.add(cid)
                meta = row.get("crdtNm") or ""          # 예: "15차시(1학점)"
                field_raw = row.get("trnSubjNm") or row.get("stdtrShpNmList") or ""
                field = ", ".join(
                    t for t in (p.strip() for p in field_raw.split(",")) if t and t not in EXCLUDE_FIELDS
                )
                out.append(Course(
                    site="비바샘", name=name,
                    credit=parse_credit(meta), hours=parse_hours(meta),
                    field_name=clean(field),
                    open_month=this_month,
                    url=f"https://t.vivasam.com/courses/{path}/{cid}" if cid else "",
                    course_id=cid, raw_text=name[:500], first_seen=today,
                ))
            total_pages = data.get("totalPages") or 1
            page += 1
            if page >= total_pages:
                break
    return out
