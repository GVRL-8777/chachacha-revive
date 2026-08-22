# -*- coding: utf-8 -*-
"""sfmerge.py 에 helly 자산을 담기 위한 두 가지를 더 얹는다.

  · MonoBehaviour 는 스크립트 타입트리가 플레이어 빌드에 없어 왕복이 안 된다.
    앞머리(게임오브젝트 PPtr, 스크립트 PPtr)만 손으로 고치고 나머지는 그대로 옮긴다.
  · 한 번들에 같이 들어가는 것끼리의 참조는 바깥 참조가 아니라 내부 참조여야 한다.
    그런 대상은 바깥 목록에서도 빼야 엔진이 없는 파일을 찾지 않는다.
"""
import ast
import io

p = 'sfmerge.py'
s = io.open(p, encoding='utf-8').read()

if 'import os' not in s.split('\n\n')[0]:
    s = s.replace('import struct, io, sys', 'import struct, io, os, sys', 1)

old = """    data = bytearray()
    objs = []"""
new = """    by_name = dict((os.path.basename(s0['path']), s0) for s0 in srcs)
    ext_order = [e for e in ext_order if os.path.basename(e) not in by_name]

    data = bytearray()
    objs = []"""
assert old in s
s = s.replace(old, new, 1)

old = """        ext_map = dict((i + 1, ext_order.index(e) + 1)
                       for i, e in enumerate(meta['externals']))"""
new = """        ext_map = dict((i + 1, ext_order.index(e) + 1)
                       for i, e in enumerate(meta['externals'])
                       if e in ext_order)"""
assert old in s
s = s.replace(old, new, 1)

old = """        def fix(p):
            if p['m_FileID'] == 0:
                if p['m_PathID'] in pmap:
                    p['m_PathID'] = pmap[p['m_PathID']]
                    return 1
                return 0
            p['m_FileID'] = ext_map[p['m_FileID']]
            return 1"""
new = """        def fix(p):
            if p['m_FileID'] == 0:
                if p['m_PathID'] in pmap:
                    p['m_PathID'] = pmap[p['m_PathID']]
                    return 1
                return 0
            nm = os.path.basename(meta['externals'][p['m_FileID'] - 1])
            tgt = by_name.get(nm)
            if tgt is not None and p['m_PathID'] in tgt['map']:
                p['m_FileID'] = 0
                p['m_PathID'] = tgt['map'][p['m_PathID']]
                return 1
            p['m_FileID'] = ext_map[p['m_FileID']]
            return 1"""
assert old in s
s = s.replace(old, new, 1)

old = """        for pid in sorted(sf.objects.keys()):
            o = sf.objects[pid]
            tree = o.read_typetree()"""
new = """        for pid in sorted(sf.objects.keys()):
            o = sf.objects[pid]
            if o.type.name == 'MonoBehaviour':
                #   0..7  m_GameObject(fileID,pathID)  8 m_Enabled  12..19 m_Script
                rec = orig[pid]
                st0 = base + rec['start']
                gf, gp = struct.unpack_from('<ii', data, st0)
                if gf == 0 and gp in pmap:
                    struct.pack_into('<ii', data, st0, 0, pmap[gp])
                elif gf:
                    nm0 = os.path.basename(meta['externals'][gf - 1])
                    t0 = by_name.get(nm0)
                    if t0 is not None and gp in t0['map']:
                        struct.pack_into('<ii', data, st0, 0, t0['map'][gp])
                    elif gf in ext_map:
                        struct.pack_into('<ii', data, st0, ext_map[gf], gp)
                struct.pack_into('<ii', data, st0 + 12, 0, 0)   # 스크립트는 비운다
                objs.append({'path_id': pmap[pid], 'start': st0, 'size': rec['size'],
                             'type_id': int(o.class_id), 'class_id': int(o.class_id),
                             'destroyed': 0})
                continue
            tree = o.read_typetree()"""
assert old in s
s = s.replace(old, new, 1)

io.open(p, 'w', encoding='utf-8').write(s)
ast.parse(s)
print('sfmerge 에 MonoBehaviour 처리 + 내부참조 전환 (구문 OK)')
