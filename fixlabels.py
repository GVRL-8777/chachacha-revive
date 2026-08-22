# -*- coding: utf-8 -*-
"""복제 카드 UILabel 의 꼬리 손상을 복구한다.

`clonecard.py` 의 바이트 수준 pathID 치환이 값이 우연히 같았던 필드까지 덮어썼다.
UILabel 꼬리(텍스트 뒤 64바이트)에서 다음이 당했다.
    [4]  mEncoding    1 -> 452/514/576/638
    [20] mEffectStyle 2 -> 453/515/577/639   (외곽선. 정의되지 않은 값이라 렌더가 깨진다)
    [60] (예약)       1 -> 452/514/576/638
같은 크기라 제자리에서 되돌린다.
"""
import io
import struct
import sys
from collections import defaultdict

from sfparse import parse
from sfwrite import ALIGN
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile

SRC, OUT = sys.argv[1], sys.argv[2]
CN_SA0 = 'survey/5577.com.cjenm.chachachacn/assets/bin/Data/sharedassets0.assets'
TEXT_OFF = 72
GOOD = {4: 1, 20: 2, 60: 1}


def main():
    meta = parse(SRC)
    raw = io.open(SRC, 'rb').read()
    sf = SerializedFile(EndianBinaryReader(raw), None)
    names = {}
    s0 = SerializedFile(EndianBinaryReader(io.open(CN_SA0, 'rb').read()), None)
    for pid, o in s0.objects.items():
        if o.type.name != 'MonoScript':
            continue
        d = o.get_raw_data()
        n = struct.unpack_from('<i', d, 0)[0]
        if 0 < n < 200:
            try:
                names[pid] = d[4:4 + n].decode('utf-8')
            except UnicodeDecodeError:
                pass
    gname = {}
    for q, o in sf.objects.items():
        if o.type.name == 'GameObject':
            gname[q] = o.read_typetree()['m_Name']

    patched = {}
    for q, o in sf.objects.items():
        if o.type.name != 'MonoBehaviour':
            continue
        d = bytearray(o.get_raw_data())
        if names.get(struct.unpack_from('<i', d, 16)[0]) != 'UILabel':
            continue
        n = struct.unpack_from('<i', d, TEXT_OFF)[0]
        t = TEXT_OFF + 4 + ((n + 3) // 4) * 4
        fixes = []
        for off, good in GOOD.items():
            cur = struct.unpack_from('<i', d, t + off)[0]
            if cur != good:
                struct.pack_into('<i', d, t + off, good)
                fixes.append('[%d] %d->%d' % (off, cur, good))
        if fixes:
            patched[q] = bytes(d)
            print("  %-22s %s" % (gname.get(struct.unpack_from('<i', d, 4)[0], '?'),
                                  ', '.join(fixes)))

    objs = sorted(meta['objects'], key=lambda x: x['start'])
    data = bytearray()
    newobjs = []
    for ob in objs:
        while len(data) % 8:
            data.append(0)
        st = len(data)
        b = patched.get(ob['path_id']) or \
            raw[meta['data_offset'] + ob['start']: meta['data_offset'] + ob['start'] + ob['size']]
        data += b
        newobjs.append(dict(ob, start=st, size=len(b)))
    m = meta['unity'].encode('utf-8') + b'\x00'
    m += struct.pack('<i', meta['platform'])
    m += struct.pack('<i', 0)
    m += struct.pack('<i', meta['big_id'])
    m += struct.pack('<i', len(newobjs))
    for ob in sorted(newobjs, key=lambda x: x['path_id']):
        m += struct.pack('<iIIiHh', ob['path_id'], ob['start'], ob['size'],
                         ob['type_id'], ob['class_id'], ob['destroyed'])
    m += struct.pack('<i', len(meta['externals']))
    for nm in meta['externals']:
        m += b'\x00' + b'\x00' * 16 + struct.pack('<i', 0) + nm.encode('utf-8') + b'\x00'
    m += b'\x00'
    data_offset = max(meta['data_offset'], ALIGN(20 + len(m) + 64))
    head = struct.pack('>IIII', len(m), data_offset + len(data), 9, data_offset)
    head += bytes([1 if meta['endian'] == '>' else 0, 0, 0, 0])
    ob2 = bytearray(head + m)
    while len(ob2) < data_offset:
        ob2 += b'\x00'
    ob2 += data
    io.open(OUT, 'wb').write(bytes(ob2))
    print("출력: %s / 라벨 %d개 복구" % (OUT, len(patched)))


if __name__ == '__main__':
    main()
