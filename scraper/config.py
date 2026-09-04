"""수집 대상 및 실행 설정."""
import os

SITES = {
    "티처빌": "https://www.teacherville.co.kr/trainapply/allCourseList.edu",
    "아이스크림": "https://teacher.i-scream.co.kr/course/crs/creditList.do?searchOrdinalTyCode=TY01&searchOrderField=NEW",
    "한국교원": "https://www.hstudy.co.kr/newmain/sub2.asp",
    "사제동행": "https://www.education.or.kr/studyjob/course.asp?sec=GNBL&tabId=JTSYV",
}

# Playwright 동작
HEADLESS = os.environ.get("HEADLESS", "1") != "0"
MAX_LOAD_MORE = int(os.environ.get("MAX_LOAD_MORE", "120"))
PAGE_TIMEOUT_MS = 30000
