"""매일 실행: courses.json(상태) 로드 → 4개 사이트 수집 → 신규만 추가 →
종료 자동정리(사라짐 감지) → courses.json 저장. GitHub Actions에서 돌아간다.

로컬 확인:  cd scraper && pip install -r requirements.txt && python -m playwright install chromium && python run.py
"""
import json, os, re, datetime, sys, types

# 로컬 Windows 콘솔(cp949)에서 한글/특수문자 로그 출력 시 깨지지 않도록(GitHub Actions는 이미 UTF-8이라 영향 없음)
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(__file__))
import config
from scrapers.generic import run_spec
from scrapers.sites import SPECS

DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'courses.json')

# ── 종료 자동정리 설정 ─────────────────────────────────────────
# 전체 목록을 '빠짐없이' 긁는 사이트만 넣는다(아니면 정상 과정이 매번 미노출로 잡혀 오판).
# 처음엔 비워두고, 운영하며 확신이 서면 예: ['사제동행','한국교원'] 추가.
FULL_CATALOG_SITES = ['티처빌', '사제동행', '아이스크림']  # 종료 자동정리 대상
# (아이스크림은 예전엔 이름 불일치로 제외했으나, norm_loose 보조매칭 도입 후 재활성화 — 2026-09-11)
GRACE_RUNS = 2   # 연속 N회 미노출 시 종료 확정
# 일회성: 여기 넣은 연수원의 '종료' 딱지를 전부 '서비스중'으로 되돌린다(정리 후 [] 로 비우면 됨).
RESET_ENDED_SITES = []
# 수집 불안정 사이트: 새로 잡혀도 '신규(오늘 날짜)'가 아니라 '기존(날짜 비움)'으로 넣는다(가짜 신규 방지).
# (아이스크림은 더보기 로딩 안정화 후 자동 신규 감지 재활성화 → 비움)
BACKFILL_APPEND_SITES = []
# 일회성: 여기 넣은 연수원의 기존 '신규' 표기를 전부 '기존 + 서비스일자 비움'으로 정리(정리 후 [] 로 비우면 됨).
RESET_NEW_SITES = ['아이스크림']
# 일회성: 상세 URL 로직이 없던 시절 목록페이지 URL이 잘못 채워진 값을 비운다(정리 후 [] 로 비우면 됨).
# (해당 사이트의 url_template이 준비되면 다음 실행부터 진짜 상세 URL로 다시 채워짐)
CLEAN_FAKE_URL_SITES = ['티처빌']
# 비바샘(자사) 시드: 크롤링 대상이 아니므로 이 파일에서 없는 과정만 병합한다.
VIVASAM_SEED_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'vivasam_seed.json')

# 자동 수집에서 제외할 연수원(기존 데이터는 대시보드에 그대로 남음).
SKIP_SITES = []

# 한국교원(hstudy): GitHub Actions 서버 IP가 사이트에서 차단돼 있어 직접 수집이 안 된다.
# 대신 국내 IP(사용자 PC)에서 hstudy_only.py로 매일 미리 수집해둔 파일을 여기서 읽어 병합한다.
# 파일이 없거나 PREFETCH_MAX_AGE_HOURS보다 오래됐으면 이번 실행은 건너뛰고 기존 데이터를 유지한다.
PREFETCHED_SITES = {'한국교원': os.path.join(os.path.dirname(__file__), '..', 'data', 'hstudy_raw.json')}
PREFETCH_MAX_AGE_HOURS = 30   # 매일 08:00 KST 실행 기준(하루+여유)

# 전체수집 전환 시 '오늘'로 잘못 찍힌 대량유입분 정리용(일회성).
# 구분=신규인데 서비스일자가 이 날짜 이하면 → 기존 + 서비스일자 비움. 정리 끝나면 '' 로 두면 됨.
CLEAN_NEW_BEFORE = ''
# 한 실행에서 이 수 이상 새로 잡히면 '진짜 신규'가 아니라 백필/전체수집으로 보고 기존+날짜비움 처리.
BULK_THRESHOLD = 30
# 대시보드에서 내보낸 수동 서비스일자({_key: "YYYY-MM-DD"})를 매 실행 때 반영.
MANUAL_DATES_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'manual_dates.json')
# 대시보드에서 내보낸 편집/삭제 내역을 매 실행 때 반영.
#   {"edits": {"_key": {"과정명":..,"학점":..,"시간":..,"주제":..,"서비스일자":..}},
#    "deletes": ["_key", ...]}
OVERRIDES_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'overrides.json')

def today(): return datetime.date.today().isoformat()
def norm(s): return re.sub(r'\s+', '', str(s or '')).lower()
# 종료 자동정리 오탐 방지용: 공백 외에 흔히 붙었다 빠졌다 하는 문장부호도 무시(느낌표/따옴표/괄호/가운뎃점 등).
# _key(=norm)는 그대로 두고, "오늘 목록에 있는지" 판정에서만 이 느슨한 비교를 보조로 쓴다.
def norm_loose(s): return re.sub(r'[\s\-_(),.!?~:;\'"\[\]·]+', '', str(s or '')).lower()

def load_prefetched(name, path):
    """국내 IP에서 hstudy_only.py 등으로 미리 수집해둔 결과 파일을 읽어 Course처럼 다룬다.
    파일이 없거나 너무 오래됐으면 None(이번 실행은 건너뜀 → 기존 데이터 유지)."""
    if not os.path.exists(path):
        print(f'[{name}] 사전수집 파일 없음({os.path.basename(path)}) — 이번엔 건너뜀, 기존 데이터 유지')
        return None
    try:
        with open(path, encoding='utf-8') as f:
            payload = json.load(f)
        collected_at = datetime.datetime.fromisoformat(payload['collected_at'])
        age_h = (datetime.datetime.now() - collected_at).total_seconds() / 3600
        if age_h > PREFETCH_MAX_AGE_HOURS:
            print(f'[{name}] 사전수집 파일이 {age_h:.0f}시간 전 것 — 오래돼서 이번엔 건너뜀, 기존 데이터 유지')
            return None
        return [types.SimpleNamespace(**c) for c in payload['courses']]
    except Exception as e:
        print(f'[{name}] 사전수집 파일 처리 오류: {e} — 건너뜀')
        return None

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
    live_loose = {}                    # site -> set(norm_loose(과정명)) : 문장부호 무시 보조 대조용
    total_new = 0

    # ── 비바샘 시드 병합: 없는 과정만 추가(기존 데이터는 건드리지 않음) ──
    if os.path.exists(VIVASAM_SEED_PATH):
        try:
            with open(VIVASAM_SEED_PATH, encoding='utf-8') as f:
                vseed = json.load(f)
            added = 0
            for rec in vseed:
                k = rec.get('_key') or ('비바샘::' + norm(rec.get('과정명')))
                rec['_key'] = k
                if k not in seen:
                    state.append(rec); seen[k] = rec; added += 1
            if added:
                print(f'[비바샘] 시드 병합 신규 {added}건 (총 시드 {len(vseed)}건)')
        except Exception as e:
            print(f'[비바샘] 시드 병합 오류: {e}')

    # ── 일회성 정리: '오늘'로 잘못 찍힌 대량유입분(구분=신규 & 서비스일자<=기준일) → 기존 + 날짜비움 ──
    if CLEAN_NEW_BEFORE:
        fixed = 0
        for r in state:
            s = str(r.get('서비스일자') or '')
            if r.get('구분') == '신규' and len(s) == 10 and s[:4].isdigit() and s <= CLEAN_NEW_BEFORE:
                r['구분'] = '기존'; r['서비스일자'] = ''; fixed += 1
        if fixed:
            print(f'[정리] 잘못 찍힌 신규 {fixed}건 → 기존 + 서비스일자 비움')

    # ── 일회성 정리: 특정 연수원의 '신규' 표기를 '기존 + 서비스일자 비움'으로 정리(불안정 수집 오라벨 제거) ──
    if RESET_NEW_SITES:
        rn = 0
        for r in state:
            if r.get('연수원') in RESET_NEW_SITES and r.get('구분') == '신규':
                r['구분'] = '기존'; r['서비스일자'] = ''; r['신규오픈월'] = ''; rn += 1
        if rn:
            print(f'[정리] {RESET_NEW_SITES} 신규→기존(날짜비움) {rn}건')

    # ── 일회성 정리: 특정 연수원의 '종료' 딱지를 '서비스중'으로 되돌림(이름 불일치 오탐 복구) ──
    if RESET_ENDED_SITES:
        reset = 0
        for r in state:
            if r.get('연수원') in RESET_ENDED_SITES and r.get('서비스상태') == '종료':
                r['서비스상태'] = '서비스중'; r['종료확인일'] = ''; r['미노출횟수'] = 0; reset += 1
        if reset:
            print(f'[정리] {RESET_ENDED_SITES} 종료→서비스중 복구 {reset}건')

    # ── 일회성 정리: url 로직 도입 전 목록페이지 URL이 잘못 채워진 값을 비움(다음 수집 때 진짜 값으로 재백필됨) ──
    if CLEAN_FAKE_URL_SITES:
        cu = 0
        for r in state:
            site = r.get('연수원')
            if site in CLEAN_FAKE_URL_SITES and r.get('url') and r.get('url') == config.SITES.get(site):
                r['url'] = ''; cu += 1
        if cu:
            print(f'[정리] {CLEAN_FAKE_URL_SITES} 목록URL 오채움 {cu}건 → 비움')

    for name, spec in SPECS.items():
        if name in SKIP_SITES:
            print(f'[{name}] 자동수집 제외(SKIP_SITES) — 기존 데이터 유지')
            continue
        if name in PREFETCHED_SITES:
            courses = load_prefetched(name, PREFETCHED_SITES[name])
            if courses is None:
                continue
        else:
            try:
                courses = run_spec(spec)
            except Exception as e:
                print(f'[{name}] 수집 오류: {e}')
                continue
        live[name] = set()
        live_loose[name] = set()
        fresh = []
        url_filled = 0
        for c in courses:
            key = f'{c.site}::{norm(c.name)}'
            live[name].add(key)
            live_loose[name].add(norm_loose(c.name))
            if key not in seen:
                rec = {
                    '연수원': c.site, '과정명': c.name, '학점': c.credit, '시간': c.hours,
                    '주제': c.field_name, '강사명': '', '서비스일자': today(),
                    '서비스상태': '서비스중', '구분': '신규',
                    '신규오픈월': today()[:7], 'url': c.url, '_key': key, '미노출횟수': 0,
                }
                state.append(rec); seen[key] = rec; fresh.append(rec)
            elif c.url and not seen[key].get('url'):
                # 기존 과정: 상세 URL이 비어있던 걸 이번 수집값으로 채운다(과거엔 url 로직이 없어 비어있던 레코드 백필)
                seen[key]['url'] = c.url; url_filled += 1
        # 대량유입(전체수집/백필)이거나, 수집 불안정 사이트면 진짜 신규가 아니므로 기존+날짜비움 처리
        if seeding or len(fresh) >= BULK_THRESHOLD or name in BACKFILL_APPEND_SITES:
            for rec in fresh:
                rec['구분'] = '기존'; rec['서비스일자'] = ''; rec['신규오픈월'] = ''
            label = '백필' if seeding else ('불안정(기존처리)' if name in BACKFILL_APPEND_SITES else '대량(기존처리)')
            print(f'[{name}] 수집 {len(courses)} / {label} {len(fresh)}' + (f' / url백필 {url_filled}' if url_filled else ''))
        else:
            total_new += len(fresh)
            flag = '' if courses else '  ← 0건(선택자 확인 필요)'
            print(f'[{name}] 수집 {len(courses)} / 신규 {len(fresh)}{flag}' + (f' / url백필 {url_filled}' if url_filled else ''))

    # ── 종료 자동정리 ──
    if not seeding and FULL_CATALOG_SITES:
        ended = revived = 0
        for r in state:
            site = r['연수원']
            if site not in FULL_CATALOG_SITES or site not in live:
                continue
            # 정확한 키가 안 잡혀도, 문장부호만 다른 채 오늘 목록에 그대로 있으면 '있음'으로 본다
            # (사이트가 느낌표/따옴표/괄호를 붙였다 뺐다 해서 키가 흔들리는 경우의 오탐 방지).
            still_here = r['_key'] in live[site] or norm_loose(r.get('과정명')) in live_loose.get(site, set())
            if still_here:
                if r.get('미노출횟수'): r['미노출횟수'] = 0
                if r.get('서비스상태') == '종료':
                    r['서비스상태'] = '서비스중'; r['종료확인일'] = ''; revived += 1
            else:
                r['미노출횟수'] = int(r.get('미노출횟수') or 0) + 1
                if r['미노출횟수'] >= GRACE_RUNS and r.get('서비스상태') != '종료':
                    r['서비스상태'] = '종료'; r['종료확인일'] = today(); ended += 1
        print(f'종료 대조: 신규 종료 {ended} / 복구 {revived} (대상 {FULL_CATALOG_SITES})')

    # ── 수동 서비스일자 반영(대시보드에서 내보낸 값) ──
    if os.path.exists(MANUAL_DATES_PATH):
        try:
            with open(MANUAL_DATES_PATH, encoding='utf-8') as f:
                manual = json.load(f)
            applied = 0
            for r in state:
                d = manual.get(r['_key'])
                if d:
                    r['서비스일자'] = d
                    if len(str(d)) >= 7:
                        r['신규오픈월'] = str(d)[:7]
                    applied += 1
            if applied:
                print(f'[수동입력] 서비스일자 {applied}건 반영')
        except Exception as e:
            print(f'[수동입력] manual_dates.json 처리 오류: {e}')

    # ── 편집/삭제 내역 반영(대시보드에서 내보낸 overrides.json) ──
    if os.path.exists(OVERRIDES_PATH):
        try:
            with open(OVERRIDES_PATH, encoding='utf-8') as f:
                ov = json.load(f)
            edits = ov.get('edits', {}) or {}
            deletes = set(ov.get('deletes', []) or [])
            EDITABLE = ('과정명', '학점', '시간', '주제', '서비스일자', '서비스상태')
            ed = 0
            for r in state:
                e = edits.get(r['_key'])
                if e:
                    for k in EDITABLE:
                        if k in e:
                            r[k] = e[k]
                    if e.get('서비스일자') and len(str(e['서비스일자'])) >= 7:
                        r['신규오픈월'] = str(e['서비스일자'])[:7]
                    if e.get('서비스상태') == '서비스중':   # 종료 해제 시 미노출/종료확인일 초기화
                        r['미노출횟수'] = 0; r['종료확인일'] = ''
                    ed += 1
            before = len(state)
            state = [r for r in state if r['_key'] not in deletes]
            if ed or (before - len(state)):
                print(f'[수정반영] 편집 {ed}건 / 삭제 {before - len(state)}건')
        except Exception as e:
            print(f'[수정반영] overrides.json 처리 오류: {e}')

    save(state)
    print(f'{"[백필] " if seeding else ""}신규 {total_new}건 / 총 {len(state)}건 저장')

if __name__ == '__main__':
    main()
