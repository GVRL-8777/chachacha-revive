# -*- coding: utf-8 -*-
"""라벨 배치표(labels.json)와 문자열 폭을 결합해 '고칠 목록'을 만든다."""
import io
import json
import re

from scanwidth import Meter, load, NLTOK

cn, _ = load('st_cn.txt')
kr, _ = load('st_merged_kr.txt')
m = Meter('C:/Windows/Fonts/malgunbd.ttf')
rows = json.load(io.open('labels.json', encoding='utf-8'))

risk = []
for r in rows:
    k = r['key']
    if not k or k not in cn or k not in kr:
        continue
    cv, kv = cn[k], kr[k]
    if cv == kv:
        continue
    wc, wk = m.width(cv), m.width(kv)
    if wc <= 0:
        continue
    grow = wk - wc
    if r['wrap'] == 0:
        # 줄바꿈이 없으면 늘어난 폭이 그대로 화면 밖으로 나간다
        risk.append((grow, wk / wc, r, cv, kv, '가로넘침'))
    else:
        # 줄바꿈이 있으면 줄 수가 늘어 세로로 넘친다
        lc = len(cv.split(NLTOK)); lk = len(kv.split(NLTOK))
        if wk / wc > 1.3 or lk > lc:
            risk.append((grow * 0.3, wk / wc, r, cv, kv, '세로늘어남'))

risk.sort(key=lambda x: -x[0])
seen = set()
out = []
print("%-28s %-22s %5s %5s %-9s %s" % ('키', '오브젝트', '크기', '배율', '유형', '한국어'))
n = 0
for grow, ratio, r, cv, kv, kind in risk:
    sig = (r['key'], r['go'])
    if sig in seen:
        continue
    seen.add(sig)
    out.append((r['key'], r['go'], r['file'], r['size'], r['wrap'], round(ratio, 2), kind, cv, kv))
    if n < 30:
        print("%-28s %-22s %5s %4.1f배 %-9s %s"
              % (r['key'][:28], r['go'][:22], r['size'], ratio, kind,
                 kv.replace(NLTOK, ' ')[:34]))
    n += 1
print("\n위험 라벨 %d개 (고유 키+오브젝트 조합)" % len(out))

baked = [r for r in rows if not r['key']
         and any('\u4e00' <= c <= '\u9fff' for c in r['text'])]
print("\n=== 번역 안 되는 박힌 중국어 라벨 %d개 ===" % len(baked))
for r in baked[:25]:
    print("  %-30s %-24s %s" % (r['file'][:30], r['go'][:24], r['text'][:26].replace('\n', ' ')))

io.open('fix_list.txt', 'wb').write(('\n'.join(
    "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s" % (o[6], o[0], o[1], o[2], o[3], o[4], o[5], o[8].replace(NLTOK, ' '))
    for o in out) + '\n\n=== 박힌 중국어 ===\n' + '\n'.join(
    "%s\t%s\t%s" % (r['file'], r['go'], r['text'].replace('\n', ' ')) for r in baked)
    ).encode('utf-8'))
print("\n전체 -> fix_list.txt")
