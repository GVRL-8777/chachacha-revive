# -*- coding: utf-8 -*-
import os, re, hashlib, sys
import sfx

CUR = 'x77/assets/bin/Data'
CN  = 'survey/5577.com.cjenm.chachachacn/assets/bin/Data'
DON = {
    'gogo': 'survey/gogogoracer-1-4-3/assets/bin/Data',
    'kkao': 'survey/racechachachaforkakao/assets/bin/Data',
}

def hashes(d):
    h = {}
    for n in os.listdir(d):
        if not re.fullmatch(r'[0-9a-f]{32}', n):
            continue
        p = os.path.join(d, n)
        if os.path.isfile(p):
            h[n] = hashlib.md5(open(p, 'rb').read()).hexdigest()
    return h

cur, cn = hashes(CUR), hashes(CN)
don = {k: hashes(v) for k, v in DON.items()}

new  = sorted(set(cur) - set(cn))
over = sorted(n for n in set(cur) & set(cn) if cur[n] != cn[n])
print("현재 %d / 중국판 %d" % (len(cur), len(cn)))
print("새로 추가된 자산 : %d" % len(new))
print("중국판을 덮어쓴 자산 : %d" % len(over))

def origin(n, h):
    src = []
    for k, dh in don.items():
        if dh.get(n) == h:
            src.append(k)
    return ",".join(src) if src else "?"

from collections import Counter
print("\n[추가분 출처]", Counter(origin(n, cur[n]) for n in new))
print("[덮어쓴 것 출처]", Counter(origin(n, cur[n]) for n in over))
print("\n덮어쓴 자산 목록(중국판 원본이 있던 자리):")
for n in over:
    print("   %s  출처=%-6s 현재=%d 중국판=%d"
          % (n, origin(n, cur[n]),
             os.path.getsize(os.path.join(CUR, n)),
             os.path.getsize(os.path.join(CN, n))))
