# -*- coding: utf-8 -*-
# 폴더 안 자산을 전부 훑어 이름에 걸리는 오브젝트를 찾는다.
import sys, os, UnityPy, collections
folder=sys.argv[1]; pats=[s.lower() for s in sys.argv[2:]]
hits=collections.defaultdict(list)
for root,_,fs in os.walk(folder):
    for f in fs:
        try: env=UnityPy.load(os.path.join(root,f))
        except Exception: continue
        for r in env.objects:
            if r.type.name not in ("GameObject","Mesh","Texture2D","Material"): continue
            try:
                nm=r.read().m_Name or ""
            except Exception: continue
            l=nm.lower()
            if any(p in l for p in pats):
                hits[(nm, r.type.name)].append(f)
for (nm,t) in sorted(hits):
    print("  %-32s %-10s %d건  예:%s" % (nm, t, len(hits[(nm,t)]), hits[(nm,t)][0][:20]))
if not hits: print("  (없음)")
