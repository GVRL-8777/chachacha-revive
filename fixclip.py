# -*- coding: utf-8 -*-
"""드라이버 목록 패널의 클리핑을 조정해 9~12번 카드가 그려지게 한다.

증상: 카드 9~12번(y <= -1160)이 스크롤은 되지만 **배경/초상화가 통째로 안 그려진다**.
검증: 같은 카드를 원본 영역(y=-290)으로 옮기면 배경·초상화가 완벽히 렌더링된다.
      -> 데이터는 정상이고 **패널 클리핑 범위 밖**이라 잘려 나가는 것이다.

UIPanel(144바이트) 레이아웃 실측:
  @104 mAlpha(float)  @112 mClipping(int, 1=SoftClip)
  @116 mClipRange(x,y,z=w,w=h)  @136 mClipSoftness(x,y)

mClipRange 가 (0,0,0,0) 이면 NGUI 는 "폭/높이 0" 을 무한대가 아니라
**패널 자체 크기**로 해석하는 경로를 타는데, 이 프리팹에서는 4행 기준으로 잘린다.
클리핑을 0(None)으로 끄면 목록 전체가 그려진다.
"""
import io
import struct
import sys

from sfparse import parse
from sfwrite import ALIGN
from UnityPy.files.SerializedFile import SerializedFile
from UnityPy.streams import EndianBinaryReader

SRC, OUT = sys.argv[1], sys.argv[2]
PANEL_PID = int(sys.argv[3]) if len(sys.argv) > 3 else 428
CLIPPING_OFF = 112


def main():
    meta = parse(SRC)
    raw = io.open(SRC, 'rb').read()
    sf = SerializedFile(EndianBinaryReader(raw), None)
    d = bytearray(sf.objects[PANEL_PID].get_raw_data())

    before = struct.unpack_from('<i', d, CLIPPING_OFF)[0]
    struct.pack_into('<i', d, CLIPPING_OFF, 0)      # 0 = None (클리핑 없음)
    print("UIPanel pathID=%d  mClipping %d -> 0 (클리핑 해제)" % (PANEL_PID, before))

    patched = {PANEL_PID: bytes(d)}
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
    for name in meta['externals']:
        m += b'\x00' + b'\x00' * 16 + struct.pack('<i', 0) + name.encode('utf-8') + b'\x00'
    m += b'\x00'
    data_offset = max(meta['data_offset'], ALIGN(20 + len(m) + 64))
    head = struct.pack('>IIII', len(m), data_offset + len(data), 9, data_offset)
    head += bytes([1 if meta['endian'] == '>' else 0, 0, 0, 0])
    ob2 = bytearray(head + m)
    while len(ob2) < data_offset:
        ob2 += b'\x00'
    ob2 += data
    io.open(OUT, 'wb').write(bytes(ob2))
    print("출력: %s (%d B)" % (OUT, len(ob2)))


if __name__ == '__main__':
    main()
