# -*- coding: utf-8 -*-
"""배포판별 맵 '테마'를 센다.

세그먼트 경로는 <테마이름>01 / <테마이름>02 꼴이다.
_low(저품질 복제), completemap(라이트맵 텍스처), materials/(재질) 는 테마가 아니다.
"""
import os, re, sys, UnityPy
from collections import defaultdict

def themes(data_dir, label):
    env = UnityPy.load(os.path.join(data_dir, 'mainData'))
    rm = [r for r in env.objects if r.type.name == 'ResourceManager'][0].read()
    ps = sorted(set(p for p, _ in rm.m_Container))
    groups = defaultdict(set)
    for p in ps:
        if '/materials/' in p or p.endswith('_low') or 'completemap' in p:
            continue
        m = re.match(r'^(?:background|map)/(?:(\w+)/)?(?:(\w+)/)?([a-z]+?)(\d\d)$', p)
        if not m:
            continue
        a, b, name, num = m.groups()
        if name.startswith('data_') or p.split('/')[-1].startswith('data_'):
            continue
        grp = a if a and b else '(기본)'
        groups[grp].add(name)
    print("=== %s" % label)
    total = 0
    for g in sorted(groups):
        names = sorted(groups[g])
        print("  %-10s %2d종: %s" % (g, len(names), ', '.join(names)))
        total += len(names)
    print("  합계 %d종" % total)
    return groups

themes('survey/5577.com.cjenm.chachachacn/assets/bin/Data', '중국판 1.2.1 (현재 기반)')
themes('survey/gogogoracer-1-4-3/assets/bin/Data', 'gogogoracer 1.4.3')
themes('survey/racechachachaforkakao/assets/bin/Data', '카카오판')
