# -*- coding: utf-8 -*-
"""배포판의 맵 세그먼트 메시 바운드를 한 줄씩 찍는다."""
import os, sys, UnityPy
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile

D = sys.argv[1]
pref = sys.argv[2:]
env = UnityPy.load(os.path.join(D, 'mainData'))
rm = [r for r in env.objects if r.type.name == 'ResourceManager'][0].read()
af = env.objects[0].assets_file
idx = {}
for p, ptr in rm.m_Container:
    fid = getattr(ptr, 'file_id', None)
    if fid:
        idx.setdefault(p, os.path.basename(af.externals[fid - 1].path))

for p in sorted(idx):
    if not any(p.startswith(x) for x in pref):
        continue
    fn = os.path.join(D, idx[p])
    if not os.path.exists(fn):
        continue
    try:
        sf = SerializedFile(EndianBinaryReader(open(fn, 'rb').read()), None)
    except Exception as e:
        continue
    for pid, o in sorted(sf.objects.items()):
        if o.type.name != 'Mesh':
            continue
        try:
            t = o.read_typetree()
        except Exception:
            continue
        a = t.get('m_LocalAABB')
        if not a:
            continue
        c, e = a['m_Center'], a['m_Extent']
        print("%-36s 중심x=%7.1f  폭x=%6.1f  길이y=%6.1f" % (p, c['x'], e['x'] * 2, e['y'] * 2))
