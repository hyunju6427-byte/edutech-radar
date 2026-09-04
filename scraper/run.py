"""매일 실행: courses.json(상태) 로드 → 4개 사이트 수집 → 신규만 추가 →
종료 자동정리(사라짐 감지) → courses.json 저장. GitHub Actions에서 돌아간다.

로컬 확인:  cd scraper && pip install -r requirements.txt && python -m playwright install chromium && python run.py
"""
import json, os, re, datetime, sys

sys.path.insert(0, os.path.dirname(__file__))
from scrapers.generic import run_spec
from scrapers.sites import SPECS

DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'courses.json')

# ── 종료 자동정리 설정 ─────────────────────────────────────────
# 전체 목록을 '빠짐없이' 긁는 사이트만 넣는다(아니면 정상 과정이 매번 미노출로 잡혀 오판).
# 처음엔 비워두고, 운영하며 확신이 서면 예: ['사제동행','한국교원'] 추가.
FULL_CATALOG_SITES = []
GRACE_RUNS = 2   # 연속 N회 미노출 시 종료 확정

def today(): return datetime.date.today().isoformat()
def norm(s): return re.sub(r'\s+', '', str(s or '')).lower()

def load():
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, encoding='utf-8') as f:
            return json.load(f)
    return []

def save(rows):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(rows, f, ensure_ascii=False, indent=0)

def main():
    state = load()
    seen = {r['_key']: r for r in state}
    seeding = len(state) == 0          # courses.json이 비었으면 최초 백필
    live = {}                          # site -> set(_key) : 이번에 '현재 서비스중'으로 확인된 것
    total_new = 0

    for name, spec in SPECS.items():
        try:
            courses = run_spec(spec)
        except Exception as e:
            print(f'[{name}] 수집 오류: {e}')
            continue
        live[name] = set()
        added = 0
        for c in courses:
            key = f'{c.site}::{norm(c.name)}'
            live[name].add(key)
            if key not in seen:
                rec = {
                    '연수원': c.site, '과정명': c.name, '학점': c.credit, '시간': c.hours,
                    '주제': c.field_name, '강사명': '', '서비스일자': today(),
                    '서비스상태': '서비스중', '구분': '기존' if seeding else '신규',
                    '신규오픈월': today()[:7], 'url': c.url, '_key': key, '미노출횟수': 0,
                }
                state.append(rec); seen[key] = rec; added += 1
        total_new += added
        flag = '' if courses else '  ← 0건(선택자 확인 필요)'
        print(f'[{name}] 수집 {len(courses)} / 신규 {added}{flag}')

    # ── 종료 자동정리 ──
    if not seeding and FULL_CATALOG_SITES:
        ended = revived = 0
        for r in state:
            site = r['연수원']
            if site not in FULL_CATALOG_SITES or site not in live:
                continue
            if r['_key'] in live[site]:
                if r.get('미노출횟수'): r['미노출횟수'] = 0
                if r.get('서비스상태') == '종료':
                    r['서비스상태'] = '서비스중'; r['종료확인일'] = ''; revived += 1
            else:
                r['미노출횟수'] = int(r.get('미노출횟수') or 0) + 1
                if r['미노출횟수'] >= GRACE_RUNS and r.get('서비스상태') != '종료':
                    r['서비스상태'] = '종료'; r['종료확인일'] = today(); ended += 1
        print(f'종료 대조: 신규 종료 {ended} / 복구 {revived} (대상 {FULL_CATALOG_SITES})')

    save(state)
    print(f'{"[백필] " if seeding else ""}신규 {total_new}건 / 총 {len(state)}건 저장')

if __name__ == '__main__':
    main()
