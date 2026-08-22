# -*- coding: utf-8 -*-
"""아틀라스의 기존 스프라이트 좌표를 제자리에서 바꾼다(크기 불변).

목적: 엔진이 우리가 수정한 UIAtlas 오브젝트를 실제로 읽는지 확인하는 시험.
사용법: python movesprite.py <입력assets> <출력assets> <스프라이트이름>=<x>,<y>,<w>,<h> ...
"""
import io, struct, sys
from sfparse import parse
from sfwrite import ALIGN
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile

SRC, OUT = sys.argv[1], sys.argv[2]
JOBS = {}
for a in sys.argv[3:]:
    n, v = a.split('=')
    JOBS[n] = tuple(float(x) for x in v.split(','))
PID, PAYLOAD = 645, 52


def main():
    meta = parse(SRC)
    raw = io.open(SRC, 'rb').read()
    sf = SerializedFile(EndianBinaryReader(raw), None)
    d = bytearray(sf.objects[PID].get_raw_data())
    cnt = struct.unpack_from('<i', d, 32)[0]
    p = 36
    for _ in range(cnt):
        n = struct.unpack_from('<i', d, p)[0]
        nm = d[p + 4:p + 4 + n].decode('ascii', 'replace')
        q = p + 4 + ((n + 3) // 4) * 4
        if nm in JOBS:
            x, y, w, h = JOBS[nm]
            old = struct.unpack_from('<4f', d, q)
            struct.pack_into('<4f', d, q, x, y, w, h)
            struct.pack_into('<4f', d, q + 16, x, y, w, h)
            print("  %-14s %s -> (%g,%g,%g,%g)" % (nm, ['%g' % v for v in old], x, y, w, h))
        p = q + PAYLOAD

    objs = sorted(meta['objects'], key=lambda o: o['start'])
    data = bytearray()
    newobjs = []
    for o in objs:
        while len(data) % 8:
            data.append(0)
        st = len(data)
        b = bytes(d) if o['path_id'] == PID else \
            raw[meta['data_offset'] + o['start']: meta['data_offset'] + o['start'] + o['size']]
        data += b
        newobjs.append(dict(o, start=st, size=len(b)))
    m = meta['unity'].encode('utf-8') + b'\x00'
    m += struct.pack('<i', meta['platform'])
    m += struct.pack('<i', 0)
    m += struct.pack('<i', meta['big_id'])
    m += struct.pack('<i', len(newobjs))
    for o in sorted(newobjs, key=lambda o: o['path_id']):
        m += struct.pack('<iIIiHh', o['path_id'], o['start'], o['size'],
                         o['type_id'], o['class_id'], o['destroyed'])
    m += struct.pack('<i', len(meta['externals']))
    for name in meta['externals']:
        m += b'\x00' + b'\x00' * 16 + struct.pack('<i', 0) + name.encode('utf-8') + b'\x00'
    m += b'\x00'
    data_offset = max(meta['data_offset'], ALIGN(20 + len(m) + 64))
    head = struct.pack('>IIII', len(m), data_offset + len(data), 9, data_offset)
    head += bytes([1 if meta['endian'] == '>' else 0, 0, 0, 0])
    ob = bytearray(head + m)
    while len(ob) < data_offset:
        ob += b'\x00'
    ob += data
    io.open(OUT, 'wb').write(bytes(ob))
    print("출력: %s (%d B)" % (OUT, len(ob)))


if __name__ == '__main__':
    main()
