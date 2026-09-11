"""한국교원(hstudy) 전용 로컬 수집기.

GitHub Actions 서버 IP가 hstudy.co.kr에서 차단돼 있어(run.py의 SKIP_SITES),
국내 IP(이 스크립트를 실행하는 PC)에서만 이 사이트를 직접 수집하고,
그 결과를 data/hstudy_raw.json 에 저장한다.

GitHub Actions 쪽 run.py는 이 파일이 있고 너무 오래되지 않았으면(PREFETCH_MAX_AGE_HOURS)
직접 접속하는 대신 이 파일을 '오늘의 수집 결과'로 읽어서 평소처럼 병합한다.

사용법(국내 PC에서 매일 실행 — Windows 작업 스케줄러 등):
    cd scraper && python hstudy_only.py
    (이 스크립트는 저장만 하고 git commit/push는 하지 않는다 — push_hstudy.bat 참고)
"""
import json, os, sys, dataclasses, datetime

sys.path.insert(0, os.path.dirname(__file__))
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8')
    except Exception:
        pass

from scrapers.generic import run_spec
from scrapers.sites import SPECS

OUT_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'hstudy_raw.json')


def main():
    spec = SPECS['한국교원']
    courses = run_spec(spec)
    if not courses:
        print('[한국교원] 0건 수집 — 파일을 덮어쓰지 않고 종료(선택자 확인 필요)')
        sys.exit(1)

    payload = {
        'collected_at': datetime.datetime.now().isoformat(timespec='seconds'),
        'count': len(courses),
        'courses': [dataclasses.asdict(c) for c in courses],
    }
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=0)
    print(f'[한국교원] {len(courses)}건 수집 → {OUT_PATH} 저장')


if __name__ == '__main__':
    main()
