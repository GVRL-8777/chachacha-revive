# -*- coding: utf-8 -*-
"""프리팹 안 GameObject 의 Transform 로컬 위치를 옮긴다.

중국판 DriverUnit 프리팹은 드라이버 카드 8장을 2x2 자리 4곳에 **2장씩 포개** 두고
뒤쪽 4장을 꺼 놨다. 켜기만 하면 겹쳐 그려지므로 2x4 로 펼쳐야 한다.
m_LocalPosition 은 float 3개라 제자리 수정이 된다(파일 크기 불변).

사용법: python moveobj.py <입력> <출력> <이름>=<x>,<y> ...
"""
import io, sys
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile
from sfparse import parse

src, dst = sys.argv[1], sys.argv[2]
want = {}
for a in sys.argv[3:]:
    n, v = a.split('=')
    x, y = v.split(',')
    want[n] = (float(x), float(y))

meta = parse(src)
blob = bytearray(io.open(src, 'rb').read())
sf = SerializedFile(EndianBinaryReader(bytes(blob)), None)
starts = dict((o['path_id'], (o['start'], o['size'])) for o in meta['objects'])

# GameObject pathID -> 이름
gname = {}
for pid, o in sf.objects.items():
    if o.type.name == 'GameObject':
        gname[pid] = o.read_typetree()['m_Name']

done = []
for pid, o in sorted(sf.objects.items()):
    if o.type.name != 'Transform':
        continue
    t = o.read_typetree()
    n = gname.get(t['m_GameObject']['m_PathID'])
    if n not in want:
        continue
    x, y = want[n]
    old = (round(t['m_LocalPosition']['x'], 1), round(t['m_LocalPosition']['y'], 1))
    t['m_LocalPosition']['x'] = x
    t['m_LocalPosition']['y'] = y
    new = bytes(o.save_typetree(t))
    st, sz = starts[pid]
    if len(new) != sz:
        raise SystemExit("길이가 달라졌다: %s (%d -> %d)" % (n, sz, len(new)))
    off = meta['data_offset'] + st
    blob[off:off + sz] = new
    done.append("%s %s -> (%.1f, %.1f)" % (n, old, x, y))

io.open(dst, 'wb').write(bytes(blob))
for d in done:
    print("  " + d)
print("옮긴 오브젝트 %d개 -> %s" % (len(done), dst))
