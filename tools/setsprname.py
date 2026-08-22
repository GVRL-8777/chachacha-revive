# -*- coding: utf-8 -*-
"""UISprite 의 스프라이트 이름을 pathID 로 지목해 바꾼다(길이 달라도 됨).

사용법: python setsprname.py <입력자산> <출력자산> <컴포넌트pathID>=<새이름> ...
UISprite 레이아웃(실측): @64 아틀라스 PPtr, @72 스프라이트 이름(길이+문자열, 4정렬)
"""
import io, struct, sys
from sfparse import parse
from sfwrite import ALIGN

SRC, OUT = sys.argv[1], sys.argv[2]
JOBS = dict((a.split('=')[0], a.split('=', 1)[1]) for a in sys.argv[3:])
NAME_OFF = 72


def main():
    meta = parse(SRC)
    raw = io.open(SRC, 'rb').read()
    off = meta['data_offset']
    patched = {}
    for ob in meta['objects']:
        key = str(ob['path_id'])
        if key not in JOBS:
            continue
        d = raw[off + ob['start']: off + ob['start'] + ob['size']]
        ln = struct.unpack_from('<i', d, NAME_OFF)[0]
        old = d[NAME_OFF + 4:NAME_OFF + 4 + ln].decode('utf-8', 'replace')
        nb = JOBS[key].encode('utf-8')
        field = struct.pack('<i', len(nb)) + nb
        while len(field) % 4:
            field += b'\x00'
        tail = d[NAME_OFF + 4 + ((ln + 3) & ~3):]
        patched[ob['path_id']] = d[:NAME_OFF] + field + tail
        print("  pathID %s : '%s' -> '%s'" % (key, old, JOBS[key]))

    objs = sorted(meta['objects'], key=lambda x: x['start'])
    data = bytearray()
    newobjs = []
    for ob in objs:
        while len(data) % 8:
            data.append(0)
        st = len(data)
        b = patched.get(ob['path_id']) or raw[off + ob['start']: off + ob['start'] + ob['size']]
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
    print("출력: %s (%d B) / %d개 수정" % (OUT, len(ob2), len(patched)))


if __name__ == '__main__':
    main()
