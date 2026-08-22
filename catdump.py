# -*- coding: utf-8 -*-
"""공여판 mainData 의 ResourceManager 카탈로그에서 맵 항목을 나열한다."""
import os, re, sys, UnityPy

D = sys.argv[1] if len(sys.argv) > 1 else 'survey/gogogoracer-1-4-3/assets/bin/Data'
pat = sys.argv[2] if len(sys.argv) > 2 else 'tunnel'

env = UnityPy.load(os.path.join(D, 'mainData'))
rm = [r for r in env.objects if r.type.name == 'ResourceManager'][0].read()
af = env.objects[0].assets_file
cat = {}
for p, ptr in rm.m_Container:
    if ptr.file_id:
        cat.setdefault(p, (os.path.basename(af.externals[ptr.file_id - 1].path), ptr.path_id))
hit = sorted(p for p in cat if re.search(pat, p))
print("%s : 항목 %d개 (전체 %d)" % (pat, len(hit), len(cat)))
for p in hit:
    print("   %-40s %s  pathID=%d" % (p, cat[p][0], cat[p][1]))
