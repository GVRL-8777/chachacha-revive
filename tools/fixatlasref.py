# -*- coding: utf-8 -*-
"""복제 카드에서 망가진 아틀라스 참조(fileID)를 되돌린다.

`clonecard.py` 의 바이트 수준 PPtr 치환이 UISprite 의 아틀라스 PPtr 중
**fileID 자리**(pathID 가 아니라)를 복제 원본 pathID 로 덮어썼다.
그 결과 `PTDriver0`(카드 배경판) 위젯의 아틀라스가 null 이 되어
9~12번 카드의 배경이 통째로 안 그려졌다.

정상값은 fileID=5 (= sharedassets0.assets), pathID=644.
"""
import io, struct, sys
from sfparse import parse
from sfwrite import ALIGN
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile

SRC, OUT = sys.argv[1], sys.argv[2]
GOOD_FILEID = 5
ATLAS_OFF = 64
CN_SA0 = 'survey/5577.com.cjenm.chachachacn/assets/bin/Data/sharedassets0.assets'


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

    patched = {}
    for p, o in sf.objects.items():
        if o.type.name != 'MonoBehaviour':
            continue
        d = bytearray(o.get_raw_data())
        if names.get(struct.unpack_from('<i', d, 16)[0]) not in \
                ('UISprite', 'UISlicedSprite', 'UITiledSprite', 'UIFilledSprite'):
            continue
        fid, pid = struct.unpack_from('<ii', d, ATLAS_OFF)
        if fid == GOOD_FILEID:
            continue
        struct.pack_into('<i', d, ATLAS_OFF, GOOD_FILEID)
        patched[p] = bytes(d)
        print("  위젯 %d: 아틀라스 fileID %d -> %d (pathID %d 유지)" % (p, fid, GOOD_FILEID, pid))

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
    print("출력: %s (%d B) / 위젯 %d개 복구" % (OUT, len(ob2), len(patched)))


if __name__ == '__main__':
    main()
