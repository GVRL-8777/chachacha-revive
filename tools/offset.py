# -*- coding: utf-8 -*-
"""이식한 세그먼트의 루트 Transform 위치를 보정한다.

중국판은 맵 조각을 z+100 고정 간격으로 놓고, 조각의 메시 중심은 x≈0 이다.
그런데 gogogoracer 의 그리스 조각은 메시 중심이 x=33.2 로 치우쳐 있어
차(x≈0)가 도로 옆을 달리게 된다. 루트 Transform 에 -33.2 를 구워 넣어 맞춘다.

사용법: python offset.py <파일> <dx> [dy] [dz]
"""
import io, sys, struct
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile
from sfparse import parse

path = sys.argv[1]
dx = float(sys.argv[2])
dy = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
dz = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0

meta = parse(path)
blob = bytearray(io.open(path, 'rb').read())
sf = SerializedFile(EndianBinaryReader(bytes(blob)), None)

starts = dict((o['path_id'], (o['start'], o['size'])) for o in meta['objects'])
done = 0
for pid, o in sorted(sf.objects.items()):
    if o.type.name != 'Transform':
        continue
    t = o.read_typetree()
    if t['m_Father']['m_PathID'] != 0:
        continue                      # 루트만 건드린다
    t['m_LocalPosition']['x'] += dx
    t['m_LocalPosition']['y'] += dy
    t['m_LocalPosition']['z'] += dz
    new = bytes(o.save_typetree(t))
    st, sz = starts[pid]
    if len(new) != sz:
        raise SystemExit("길이가 달라졌다 (%d -> %d)" % (sz, len(new)))
    off = meta['data_offset'] + st
    blob[off:off + sz] = new
    print("루트 Transform pathID=%s 위치 보정 -> %s"
          % (pid, tuple(round(v, 2) for v in t['m_LocalPosition'].values())))
    done += 1

if not done:
    raise SystemExit("루트 Transform 을 찾지 못했다")
io.open(path, 'wb').write(bytes(blob))
print("적용 완료: %s" % path)
