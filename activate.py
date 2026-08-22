# -*- coding: utf-8 -*-
"""프리팹 안의 특정 GameObject 를 활성 상태로 켠다.

중국판 DriverUnit 프리팹에는 드라이버 카드가 **8장 다** 들어 있는데
Pig / Garu / Angry / Mental 넷이 m_IsActive=0 으로 꺼져 있다.
m_IsActive 는 1바이트라 제자리 수정이 가능하다(파일 크기 불변).

사용법: python activate.py <입력파일> <출력파일> <켤이름> ...
"""
import io, sys
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile
from sfparse import parse

src, dst = sys.argv[1], sys.argv[2]
want = set(sys.argv[3:])

meta = parse(src)
blob = bytearray(io.open(src, 'rb').read())
sf = SerializedFile(EndianBinaryReader(bytes(blob)), None)
starts = dict((o['path_id'], (o['start'], o['size'])) for o in meta['objects'])

done = []
for pid, o in sorted(sf.objects.items()):
    if o.type.name != 'GameObject':
        continue
    t = o.read_typetree()
    if t['m_Name'] not in want or t['m_IsActive']:
        continue
    t['m_IsActive'] = 1
    new = bytes(o.save_typetree(t))
    st, sz = starts[pid]
    if len(new) != sz:
        raise SystemExit("길이가 달라졌다: %s (%d -> %d)" % (t['m_Name'], sz, len(new)))
    off = meta['data_offset'] + st
    blob[off:off + sz] = new
    done.append(t['m_Name'])

io.open(dst, 'wb').write(bytes(blob))
print("켠 오브젝트 %d개: %s" % (len(done), ', '.join(done)))
missed = want - set(done)
if missed:
    print("이미 켜져 있거나 없음: %s" % ', '.join(sorted(missed)))
print("출력: %s (%d B, 원본 %d B)" % (dst, len(blob), len(io.open(src, 'rb').read())))
