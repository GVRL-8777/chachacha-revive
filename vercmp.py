# -*- coding: utf-8 -*-
"""배포판별 빌드 시점과 콘텐츠(차량/맵/캐릭터) 보유 현황을 비교한다."""
import os, zipfile, re, io, collections

import chapaths

# 있는 것만 견줍니다. 손에 없는 배포판은 조용히 건너뜁니다.
_WANT = [('8.apk (v1.3.1)', 'v131'), ('CN (중국판)', 'cn'),
         ('Kakao(ID)', 'kakao'), ('7.7.0 (한국)', 'kr'),
         ('gogogoracer 1.4.3', 'gogo')]
APKS = dict((label, chapaths.apk(key, need=False)) for label, key in _WANT)
APKS = dict((k, v) for k, v in APKS.items() if v)

RES = {
    '8.apk (v1.3.1)': 'res8.txt',
    'CN (중국판)': 'survey/5577.com.cjenm.chachachacn.txt',
    'Kakao(ID)': 'survey/racechachachaforkakao.txt',
    '7.7.0 (한국)': 'res77.txt',
}

print("=== 빌드 시점 (APK 안 파일 타임스탬프) ===")
for name, p in APKS.items():
    if not os.path.exists(p):
        print("  %-20s (없음)" % name); continue
    try:
        z = zipfile.ZipFile(p)
    except Exception as e:
        print("  %-20s ZIP 아님" % name); continue
    dates = [i.date_time for i in z.infolist()]
    if not dates:
        continue
    mx = max(dates); mn = min(dates)
    # 매니페스트에서 버전 문자열 흔적
    ver = ''
    try:
        mf = z.read('AndroidManifest.xml')
        txt = mf.decode('utf-16-le', 'ignore')
        m = re.findall(r'\d+\.\d+\.\d+', txt)
        ver = ','.join(sorted(set(m))[:3])
    except Exception:
        pass
    print("  %-20s 최신 %04d-%02d-%02d  (범위 %04d-%02d ~ %04d-%02d)  버전흔적: %s"
          % (name, mx[0], mx[1], mx[2], mn[0], mn[1], mx[0], mx[1], ver))

print()
print("=== 콘텐츠 보유 (Resources 인덱스 기준) ===")
cars = {}
for name, f in RES.items():
    if not os.path.exists(f):
        print("  %-20s (목록 없음)" % name); continue
    paths = io.open(f, encoding='utf-8').read().split('\n')
    c = sorted(set(p.split('/')[1] for p in paths
                   if p.startswith('car/') and p.count('/') >= 2))
    players = sorted(set(p.split('/')[1] for p in paths if '/player_' in p))
    themes = sorted(set(re.sub(r'\d+$', '', p.split('/')[1])
                        for p in paths
                        if p.startswith('background/') and 'completemap' in p.lower()))
    cars[name] = set(players)
    print("  %-20s 전체경로 %4d | car폴더 %2d | **player 프리팹 보유 차량 %2d** | 맵테마 %d종"
          % (name, len(paths), len(c), len(players), len(themes)))
    print("       player 차량: %s" % (', '.join(players) if players else '(없음)'))

print()
print("=== 차량 교집합/차집합 ===")
names = [n for n in cars if cars[n]]
for n in names:
    others = set().union(*[cars[m] for m in names if m != n]) if len(names) > 1 else set()
    only = sorted(cars[n] - others)
    print("  %-20s 단독 보유: %s" % (n, ', '.join(only) if only else '없음'))
