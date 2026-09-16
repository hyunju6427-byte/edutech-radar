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
    "에듀니티": "https://happy.eduniety.net/html/online/list/?isonoff=ON",
    # 유니텔은 카드 안에 학점 표기가 없고, 목록 URL(list1~4=직무 4~1학점, list6=자율연수) 자체가 학점을 의미한다.
    "유니텔": [
        "https://www.teacher.co.kr/index.do/apply/list1/",
        "https://www.teacher.co.kr/index.do/apply/list2/",
        "https://www.teacher.co.kr/index.do/apply/list3/",
        "https://www.teacher.co.kr/index.do/apply/list4/",
        "https://www.teacher.co.kr/index.do/apply/list6/",
    ],
}

# 유니텔: list_url별 학점(위 목록과 순서 대응) — 카드 자체엔 학점 표기가 없어 URL로 구분.
UNITEL_LIST_CREDIT = {
    "https://www.teacher.co.kr/index.do/apply/list1/": "4",
    "https://www.teacher.co.kr/index.do/apply/list2/": "3",
    "https://www.teacher.co.kr/index.do/apply/list3/": "2",
    "https://www.teacher.co.kr/index.do/apply/list4/": "1",
    "https://www.teacher.co.kr/index.do/apply/list6/": "자율",
}

# Playwright 동작
HEADLESS = os.environ.get("HEADLESS", "1") != "0"
MAX_LOAD_MORE = int(os.environ.get("MAX_LOAD_MORE", "120"))
PAGE_TIMEOUT_MS = 30000
