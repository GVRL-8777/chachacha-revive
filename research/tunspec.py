# -*- coding: utf-8 -*-
"""터널 세트의 sfmerge 스펙과 루트 파일 목록을 만든다.

중국판은 터널 세트가 tunnel01/02/03 한 벌뿐이다. 여기에 세 벌을 더한다.
  gtunnel  (그리스)  gogogoracer 1.4.3
  btunnel  (big)     gogogoracer 1.4.3
  bftunnel (big field) 카카오판에만 있다

`Background::SetMapResources` 는 `"Background/" + tunnelMapName[i]` 를 로드하는데
**null 검사가 없다**(Instantiate 에 그대로 넘긴다). 그래서 세트의 세 조각이 모두
반드시 해석돼야 한다.
"""
import io, os, re, UnityPy

SRC = [('survey/gogogoracer-1-4-3/assets/bin/Data', ['gtunnel', 'btunnel']),
       ('survey/racechachachaforkakao/assets/bin/Data', ['bftunnel'])]

specs, roots_by_dir = [], {}
for D, sets in SRC:
    env = UnityPy.load(os.path.join(D, 'mainData'))
    rm = [r for r in env.objects if r.type.name == 'ResourceManager'][0].read()
    af = env.objects[0].assets_file
    roots = []
    for p, ptr in rm.m_Container:
        leaf = p.split('/')[-1]
        m = re.match(r'^(%s)\d\d$' % '|'.join(sets), leaf)
        if not m or '/materials/' in p or p.endswith('_low') or 'completemap' in p:
            continue
        if not ptr.file_id:
            continue
        fn = os.path.basename(af.externals[ptr.file_id - 1].path)
        if not os.path.exists(os.path.join(D, fn)):
            continue
        key = 'Background/%s' % leaf
        if any(':%s:' % key in s for s in specs):
            continue
        specs.append('%s/%s:%s:%d:0:flat' % (D, fn, key, ptr.path_id))
        roots.append(fn)
    roots_by_dir[D] = sorted(set(roots))

specs.sort()
io.open('tunspec.txt', 'w', encoding='utf-8').write('\n'.join(specs))
for D, rs in roots_by_dir.items():
    tag = 'gogo' if 'gogogoracer' in D else 'kakao'
    io.open('tunroots_%s.txt' % tag, 'w', encoding='utf-8').write('\n'.join(rs))
    print('%s 루트 %d개' % (tag, len(rs)))
print('터널 세그먼트 %d개 -> tunspec.txt' % len(specs))
for s in specs:
    print('   ' + s.split(':')[1])
