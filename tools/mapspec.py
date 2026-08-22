# -*- coding: utf-8 -*-
"""이식할 맵 테마의 sfmerge 스펙과 의존 파일 목록을 만든다.

중국판에 없는 테마 10종은 전부 gogogoracer 1.4.3 에 있다(유니티 판본도 4.1.5 로 같다).
  greece : gaqua, gbridge, gcity, gcliff   (gbeach 는 이미 이식함)
  big    : bbeach, bbridge, bcity, bfield, bsand
  normal : aqua

컨테이너 키는 게임이 ResourceByOption::Load 에 넘기는 문자열 그대로 쓴다:
  "Background/<테마><NN>"   (예: "Background/gaqua01")
"""
import io, os, re, sys, UnityPy

D = 'survey/gogogoracer-1-4-3/assets/bin/Data'
CN = 'survey/5577.com.cjenm.chachachacn/assets/bin/Data'
THEMES = ['gaqua', 'gbridge', 'gcity', 'gcliff',
          'bbeach', 'bbridge', 'bcity', 'bfield', 'bsand',
          'aqua']

env = UnityPy.load(os.path.join(D, 'mainData'))
rm = [r for r in env.objects if r.type.name == 'ResourceManager'][0].read()
af = env.objects[0].assets_file

# 경로 -> (파일, pathID)
cat = {}
for p, ptr in rm.m_Container:
    if ptr.file_id:
        cat.setdefault(p, (os.path.basename(af.externals[ptr.file_id - 1].path), ptr.path_id))

specs, roots, report = [], [], []
for th in THEMES:
    # map/<그룹>/<테마>/<테마><NN>  꼴을 찾는다
    segs = sorted(p for p in cat
                  if re.match(r'^map/[a-z]+/%s/%s\d\d$' % (th, th), p))
    if not segs:
        report.append("  %-9s 세그먼트 없음" % th)
        continue
    for p in segs:
        fn, pid = cat[p]
        if not os.path.exists(os.path.join(D, fn)):
            report.append("  %-9s 파일 없음 %s" % (th, p))
            continue
        key = "Background/%s" % p.split('/')[-1]
        specs.append("%s/%s:%s:%d:0:flat" % (D, fn, key, pid))
        roots.append(fn)
    report.append("  %-9s %d조각: %s" % (th, len(segs),
                                        ', '.join(s.split('/')[-1] for s in segs)))

io.open('mapspec.txt', 'w', encoding='utf-8').write('\n'.join(specs))
io.open('maproots.txt', 'w', encoding='utf-8').write('\n'.join(roots))
print('\n'.join(report))
print("세그먼트 %d개 -> mapspec.txt / 루트파일 %d개 -> maproots.txt"
      % (len(specs), len(roots)))
