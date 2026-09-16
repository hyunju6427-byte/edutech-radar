"""수집 대상 및 실행 설정."""
import os

SITES = {
    "티처빌": "https://www.teacherville.co.kr/trainapply/allCourseList.edu",
    "아이스크림": "https://teacher.i-scream.co.kr/course/crs/creditList.do?searchOrdinalTyCode=TY01&searchOrderField=NEW",
    "한국교원": "https://www.hstudy.co.kr/newmain/sub2.asp",
    "사제동행": "https://www.education.or.kr/studyjob/course.asp?sec=GNBL&tabId=JTSYV",
    "교육사랑": "https://www.edulove.co.kr/main/sub2.asp?inx=1&jnx=0",
    "T셀파": "https://edu.tsherpa.co.kr/Product/List/",
    # 카운피아는 카테고리가 나뉘어 있어 하위 카테고리 URL을 다 모아야 전체 목록이 된다(실측 확인).
    "카운피아": [
        "https://counpia.com/ncs/main.html?category_id=A00010002&parent_two=A000100020001",
        "https://counpia.com/ncs/main.html?category_id=A00010002&parent_two=A000100020004",
        "https://counpia.com/ncs/main.html?category_id=A00010002&parent_two=A000100020005",
        "https://counpia.com/ncs/main.html?category_id=A00010002&parent_two=A000100020006",
        "https://counpia.com/ncs/main.html?category_id=A00010005&parent_two=A000100050001",
        "https://counpia.com/ncs/main.html?category_id=A00010005&parent_two=A000100050002",
    ],
}

# Playwright 동작
HEADLESS = os.environ.get("HEADLESS", "1") != "0"
MAX_LOAD_MORE = int(os.environ.get("MAX_LOAD_MORE", "120"))
PAGE_TIMEOUT_MS = 30000
