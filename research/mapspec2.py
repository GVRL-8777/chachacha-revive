# -*- coding: utf-8 -*-
"""이식할 맵 테마와 터널의 sfmerge 스펙, 그리고 루트 파일 목록을 만든다.

중국판에 없는 테마와 터널은 gogogoracer 1.4.3 에 있다(유니티 4.1.5f1 로 같다).
카탈로그 경로가 두 가지 꼴이라 둘 다 훑는다.
  테마 : map/<그룹>/<테마>/<테마><NN>          (예: map/greece/gbeach/gbeach01)
  터널 : map/<그룹>/<터널><NN>/<터널><NN>      (예: map/big/btunnel01/btunnel01)

컨테이너 키는 게임이 ResourceByOption::Load 에 넘기는 문자열 그대로다.
"""
import io, os, re, UnityPy

D = 'survey/gogogoracer-1-4-3/assets/bin/Data'
THEMES = ['gbeach', 'gaqua', 'gbridge', 'gcity', 'gcliff',
          'bbeach', 'bbridge', 'bcity', 'bfield', 'bsand', 'aqua']
TUNNELS = ['gtunnel01', 'gtunnel02', 'gtunnel03',
           'btunnel01', 'btunnel02', 'btunnel03']

env = UnityPy.load(os.path.join(D, 'mainData'))
rm = [r for r in env.objects if r.type.name == 'ResourceManager'][0].read()
af = env.objects[0].assets_file

cat = {}
for p, ptr in rm.m_Container:
    if ptr.file_id:
        cat.setdefault(p, (os.path.basename(af.externals[ptr.file_id - 1].path),
                           ptr.path_id))

specs, roots, report = [], [], []

def add(path):
    fn, pid = cat[path]
    if not os.path.exists(os.path.join(D, fn)):
        return False
    key = "Background/%s" % path.split('/')[-1]
    specs.append("%s/%s:%s:%d:0:flat" % (D, fn, key, pid))
    roots.append(fn)
    return True

for th in THEMES:
    segs = sorted(p for p in cat if re.match(r'^map/[a-z]+/%s/%s\d\d$' % (th, th), p))
    ok = [p for p in segs if add(p)]
    report.append("  %-9s %d조각  %s" % (th, len(ok),
                                        ', '.join(p.split('/')[-1] for p in ok)))

for tn in TUNNELS:
    segs = sorted(p for p in cat if re.match(r'^map/[a-z]+/%s/%s$' % (tn, tn), p))
    ok = [p for p in segs if add(p)]
    report.append("  %-9s %d조각  %s" % (tn, len(ok),
                                        ', '.join(p.split('/')[-1] for p in ok)))

io.open('mapspec.txt', 'w', encoding='utf-8').write('\n'.join(specs))
io.open('maproots.txt', 'w', encoding='utf-8').write('\n'.join(roots))
print('\n'.join(report))
print("\n스펙 %d줄 -> mapspec.txt / 루트 %d개 -> maproots.txt"
      % (len(specs), len(set(roots))))
