# -*- coding: utf-8 -*-
"""중국판의 동적 폰트를 한글 지원 폰트로 갈아끼운다.

중국판 `msyhbd`(sharedassets0 pathID=625)는 Font 오브젝트의 `m_FontData` 에
TTF 를 통째로 담은 **동적 폰트**다. 그런데 중국 배포용 서브셋이라
**한글 글리프가 하나도 없다**(라틴 + 한자 29,092자만). 그래서 한국어 문자열을
넣어도 글자가 안 그려진다.

같은 계열인 맑은 고딕 볼드(malgunbd.ttf)로 TTF 바이트만 바꾼다.
글꼴 이름(m_FontNames)은 그대로 두어도 무방하다 — 렌더링은 m_FontData 로 한다.
"""
import io, os, struct, sys
from sfparse import parse
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile
from sfwrite import ALIGN

SRC = sys.argv[1] if len(sys.argv) > 1 else 'overlay/sharedassets0.assets'
TTF = sys.argv[2] if len(sys.argv) > 2 else r'C:\Windows\Fonts\malgunbd.ttf'
OUT = sys.argv[3] if len(sys.argv) > 3 else 'sa0_kr.assets'
FONT_PID = 625


def main():
    meta = parse(SRC)
    raw = io.open(SRC, 'rb').read()
    sf = SerializedFile(EndianBinaryReader(raw), None)

    o = sf.objects[FONT_PID]
    t = o.read_typetree()
    old = bytes(t['m_FontData'])
    new = io.open(TTF, 'rb').read()
    print("폰트 %s: %d -> %d 바이트 (%s)" % (t.get('m_Name'), len(old), len(new),
                                          os.path.basename(TTF)))
    t['m_FontData'] = list(new)
    blob = bytes(o.save_typetree(t))

    objs = sorted(meta['objects'], key=lambda x: x['start'])
    data = bytearray()
    newobjs = []
    for ob in objs:
        while len(data) % 8:
            data.append(0)
        st = len(data)
        b = blob if ob['path_id'] == FONT_PID else \
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
    print("출력: %s (%d B, 원본 %d B)" % (OUT, len(ob2), len(raw)))


if __name__ == '__main__':
    main()
