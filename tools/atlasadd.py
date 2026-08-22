# -*- coding: utf-8 -*-
"""NGUI UIAtlas(MonoBehaviour)에 스프라이트 정의를 추가한다.

실측한 구조 (중국판 sharedassets0.assets pathID=645):
  헤더 …  @32 = 스프라이트 개수(int)  …  @40 부터 배열 시작
  레코드(가변, 이름 길이에 따라):
      int   nameLen
      byte  name[nameLen]          (4바이트 정렬 패딩)
      float outer.x, outer.y, outer.w, outer.h
      float inner.x, inner.y, inner.w, inner.h
      int   paddingLeft, Right, Top, Bottom
      int   예약 4개 (전부 0으로 관측)

MonoBehaviour 는 타입트리가 없어 UnityPy 로 못 쓰므로, **자산 파일 전체를 다시 조립**한다
(오브젝트 데이터 길이가 늘어나므로 오프셋 재계산이 필요하다).
"""
import io, os, struct, sys
from sfparse import parse
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile
from sfwrite import ALIGN

COUNT_OFF = 32          # 스프라이트 개수 필드 위치
ARRAY_OFF = 40          # 배열 시작


def make_record(name, x, y, w, h):
    b = struct.pack('<i', len(name)) + name.encode('utf-8')
    while len(b) % 4:
        b += b'\x00'
    b += struct.pack('<4f', x, y, w, h)      # outer
    b += struct.pack('<4f', x, y, w, h)      # inner (동일)
    b += struct.pack('<4i', 0, 0, 0, 0)      # padding
    b += struct.pack('<4i', 0, 0, 0, 0)      # 예약
    return b


def main():
    src, pathid, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    adds = []
    for spec in sys.argv[4:]:
        n, x, y, w, h = spec.split(',')
        adds.append((n, float(x), float(y), float(w), float(h)))

    meta = parse(src)
    raw = io.open(src, 'rb').read()
    sf = SerializedFile(EndianBinaryReader(raw), None)
    obj = sf.objects[pathid]
    d = bytearray(obj.get_raw_data())

    cnt = struct.unpack_from('<i', d, COUNT_OFF)[0]
    print("기존 스프라이트 %d개" % cnt)
    extra = b''
    for n, x, y, w, h in adds:
        extra += make_record(n, x, y, w, h)
        print("  추가: %-16s x=%s y=%s w=%s h=%s" % (n, x, y, w, h))
    struct.pack_into('<i', d, COUNT_OFF, cnt + len(adds))
    newdata = bytes(d) + extra
    print("MonoBehaviour %d -> %d 바이트" % (len(d), len(newdata)))

    # --- 자산 파일 재조립 (해당 오브젝트만 길이가 늘어난다) ---
    objs = sorted(meta['objects'], key=lambda o: o['start'])
    data = bytearray()
    newobjs = []
    for o in objs:
        while len(data) % 8:
            data.append(0)
        start = len(data)
        if o['path_id'] == pathid:
            blob = newdata
        else:
            blob = raw[meta['data_offset'] + o['start']: meta['data_offset'] + o['start'] + o['size']]
        data += blob
        newobjs.append(dict(o, start=start, size=len(blob)))

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
    outb = bytearray(head + m)
    while len(outb) < data_offset:
        outb += b'\x00'
    outb += data
    io.open(out, 'wb').write(bytes(outb))
    print("출력: %s (%d B, 원본 %d B)" % (out, len(outb), len(raw)))


if __name__ == '__main__':
    main()
