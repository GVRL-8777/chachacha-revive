# -*- coding: utf-8 -*-
"""이식 자산이 가리키는 의존 자산 중, 중국판 것이 자리를 차지해 버린 것을 찾는다."""
import os, re, hashlib
import sfx

CUR = 'x77/assets/bin/Data'
CN  = 'survey/5577.com.cjenm.chachachacn/assets/bin/Data'
DON = {
    'gogo': 'survey/gogogoracer-1-4-3/assets/bin/Data',
    'kkao': 'survey/racechachachaforkakao/assets/bin/Data',
}

def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()

def hashes(d):
    return {n: md5(os.path.join(d, n)) for n in os.listdir(d)
            if re.fullmatch(r'[0-9a-f]{32}', n)
            and os.path.isfile(os.path.join(d, n))}

cur, cn = hashes(CUR), hashes(CN)
don = {k: hashes(v) for k, v in DON.items()}
refs_cur = {n: v[2] for n, v in sfx.scan(CUR).items()}
refs_don = {k: {n: v[2] for n, v in sfx.scan(p).items()} for k, p in DON.items()}

# 어느 공여판에서 온 자산인지
src_of = {}
for n, h in cur.items():
    for k, dh in don.items():
        if dh.get(n) == h:
            src_of[n] = k
            break

print("공여판에서 그대로 온 자산: %d개" % len(src_of))

conflicts = {}          # 의존 GUID -> {공여판: set(그것을 참조하는 이식자산)}
for n, k in sorted(src_of.items()):
    for r in refs_don[k].get(n, []):
        dh = don[k].get(r)
        if dh is None:
            continue                      # 공여판에도 없음 (엔진 기본자산 등)
        if cur.get(r) != dh:              # 자리에 다른 내용이 들어 있다
            conflicts.setdefault(r, {}).setdefault(k, set()).add(n)

print("충돌하는 의존 자산: %d개\n" % len(conflicts))
for r, m in sorted(conflicts.items()):
    for k, users in sorted(m.items()):
        inCN = 'CN에도 있음' if r in cn else '중국판엔 없음'
        cursz = os.path.getsize(os.path.join(CUR, r)) if r in cur else -1
        donsz = os.path.getsize(os.path.join(DON[k], r))
        print("  %s  [%s] %s  현재=%d 공여=%d  참조자 %d개"
              % (r, k, inCN, cursz, donsz, len(users)))
