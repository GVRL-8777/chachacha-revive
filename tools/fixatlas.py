# -*- coding: utf-8 -*-
"""UI 아틀라스의 스프라이트 표를 **올바른 레코드 구조로** 다시 쓴다.

`atlasadd.py` 가 처음에 payload 를 64바이트로 잘못 잡아(실제 52바이트)
새로 넣은 PTDriverPc8~11 레코드가 통째로 어긋나 있었다. 그 결과 드라이버
9~12번 카드에서 **초상화만** 안 그려졌다(이름표·설명·버튼은 기존 스프라이트라 정상).

실측 구조:
    @32  스프라이트 개수(int)
    @36  배열 시작
    레코드 = int nameLen + name(4정렬) + payload 52바이트
             payload = outer 4f(16) + inner 4f(16) + int 5개(20)
    배열 뒤 꼬리 16바이트

원본 blob 을 기준으로 삼아 꼬리 앞에 레코드를 붙이고 개수를 늘린다.
"""
import io, struct, sys
from sfparse import parse
from sfwrite import ALIGN
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile

SRC = 'overlay/sharedassets0.assets'          # 텍스처 합성이 끝난 파일
ORIG = 'survey/5577.com.cjenm.chachachacn/assets/bin/Data/sharedassets0.assets'
OUT = 'overlay/sharedassets0.assets'
PID = 645
COUNT_OFF, ARRAY_OFF, PAYLOAD, TAIL = 32, 36, 52, 16

ADDS = [('PTDriverPc8', 632.0, 0.0, 59.0, 60.0),
        ('PTDriverPc9', 692.0, 0.0, 59.0, 60.0),
        ('PTDriverPc10', 752.0, 0.0, 59.0, 60.0),
        ('PTDriverPc11', 812.0, 0.0, 59.0, 60.0)]


def record(name, x, y, w, h):
    b = struct.pack('<i', len(name)) + name.encode('utf-8')
    while len(b) % 4:
        b += b'\x00'
    b += struct.pack('<4f', x, y, w, h)
    b += struct.pack('<4f', x, y, w, h)
    b += struct.pack('<5i', 0, 0, 0, 0, 0)
    return b


def verify(blob, label):
    """배열이 정확히 꼬리 앞에서 끝나는지 확인한다."""
    cnt = struct.unpack_from('<i', blob, COUNT_OFF)[0]
    p = ARRAY_OFF
    names = []
    for _ in range(cnt):
        n = struct.unpack_from('<i', blob, p)[0]
        names.append(blob[p + 4:p + 4 + n].decode('ascii'))
        p += 4 + ((n + 3) // 4) * 4 + PAYLOAD
    rest = len(blob) - p
    print("  %s: %d개 파싱, 끝 %d, 남은 꼬리 %d바이트 %s"
          % (label, cnt, p, rest, "OK" if rest == TAIL else "<<< 불일치!"))
    return names


def main():
    orig = SerializedFile(EndianBinaryReader(io.open(ORIG, 'rb').read()), None)
    base = bytearray(orig.objects[PID].get_raw_data())
    print("원본 아틀라스 %d바이트" % len(base))
    verify(base, "원본")

    extra = b''
    for name, x, y, w, h in ADDS:
        extra += record(name, x, y, w, h)
        print("  추가 %-14s (%g,%g) %gx%g" % (name, x, y, w, h))
    cnt = struct.unpack_from('<i', base, COUNT_OFF)[0]
    struct.pack_into('<i', base, COUNT_OFF, cnt + len(ADDS))
    newblob = bytes(base[:len(base) - TAIL]) + extra + bytes(base[len(base) - TAIL:])
    names = verify(newblob, "수정본")
    for n, _, _, _, _ in ADDS:
        assert n in names, n
    print("아틀라스 %d -> %d바이트, 스프라이트 %d -> %d개"
          % (len(base), len(newblob), cnt, cnt + len(ADDS)))

    meta = parse(SRC)
    raw = io.open(SRC, 'rb').read()
    objs = sorted(meta['objects'], key=lambda o: o['start'])
    data = bytearray()
    newobjs = []
    for o in objs:
        while len(data) % 8:
            data.append(0)
        st = len(data)
        b = newblob if o['path_id'] == PID else \
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
