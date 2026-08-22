# -*- coding: utf-8 -*-
"""한국어 문자열표를 만들어 중국판 자산에 써 넣는다.

기반: LINE 1.0.3 의 `tb_systemtext`(한국어 원본)
규칙:
  · **중국판 키 목록을 기준**으로 삼는다. 한국어표는 후기 버전이라 같은 키라도
    서식 자리표시자({0},{1}...) 구성이 다른 경우가 있는데, 그대로 넣으면
    `String.Format` 이 FormatException 으로 터진다. 구성이 같을 때만 교체한다.
  · 중국판에만 있는 키(차량 이름 37개)는 중국판 값을 살린다.
  · 한국어표에만 있는 키(드라이버 9~12번 등)는 뒤에 덧붙인다.

형식 주의: 표는 `키 = 값` + **CRLF 하나**로 끝난다.
CRLF 를 두 번 넣으면 파서가 표를 통째로 못 읽어 게임의 모든 라벨이 빈칸이 된다.
"""
import io
import os
import re
import struct

from sfparse import parse
from sfwrite import ALIGN
from UnityPy.files.SerializedFile import SerializedFile
from UnityPy.streams import EndianBinaryReader

CN_TABLE = 'st_cn.txt'
KR_TABLE = 'line_tb_systemtext.txt'
CN_DIR = 'survey/5577.com.cjenm.chachachacn/assets/bin/Data'
CN_FILE = '50295c6b20ff907439e2ef8aa05f9ea7'
OUT = 'overlay/50295c6b20ff907439e2ef8aa05f9ea7'

CRLF = chr(13) + chr(10)
LF = chr(10)
CR = chr(13)


def load(path):
    """`키 = 값` 표를 읽는다.

    파일이 CRLF 라 텍스트 모드로 열면 값 끝에 캐리지리턴이 남을 수 있다.
    바이너리로 읽어 직접 개행을 정규화한다.
    """
    raw = io.open(path, 'rb').read().decode('utf-8')
    raw = raw.replace(CRLF, LF).replace(CR, LF)
    d, order = {}, []
    for ln in raw.split(LF):
        if ' = ' not in ln:
            continue
        k, v = ln.split(' = ', 1)
        k = k.strip()
        if k not in d:
            order.append(k)
        d[k] = v
    return d, order


def slots(v):
    """서식 자리표시자 번호 집합. {0},{1} 구성이 다르면 교체하면 안 된다."""
    return set(re.findall(r'\{(\d+)', v or ''))


def main():
    cn, cn_order = load(CN_TABLE)
    kr, kr_order = load(KR_TABLE)

    merged, order = {}, []
    swapped = kept = 0
    for k in cn_order:
        cv = cn[k]
        kv = kr.get(k)
        if kv is not None and slots(kv) == slots(cv):
            merged[k] = kv
            swapped += 1
        else:
            merged[k] = cv
            kept += 1
        order.append(k)
    extra = 0
    for k in kr_order:
        if k not in merged:
            merged[k] = kr[k]
            order.append(k)
            extra += 1
    print("한국어 교체 %d / 중국판 유지 %d / 한국어 전용 추가 %d = %d개"
          % (swapped, kept, extra, len(merged)))

    text = ''.join('%s = %s%s' % (k, merged[k], CRLF) for k in order)
    io.open('st_merged_kr.txt', 'wb').write(text.encode('utf-8'))
    print("병합 문자열표 %d자 (CRLF %d개)" % (len(text), text.count(CRLF)))

    # --- 중국판 TextAsset 에 써 넣기 ---
    src = os.path.join(CN_DIR, CN_FILE)
    meta = parse(src)
    raw = io.open(src, 'rb').read()
    sf = SerializedFile(EndianBinaryReader(raw), None)
    pid = list(sf.objects.keys())[0]
    o = sf.objects[pid]
    t = o.read_typetree()
    old = t['m_Script']
    if isinstance(old, (bytes, bytearray)):
        old = old.decode('utf-8', 'replace')
    t['m_Script'] = text
    blob = bytes(o.save_typetree(t))
    print("TextAsset %d -> %d 바이트" % (len(old), len(text)))

    objs = sorted(meta['objects'], key=lambda x: x['start'])
    data = bytearray()
    newobjs = []
    for ob in objs:
        while len(data) % 8:
            data.append(0)
        st = len(data)
        b = blob if ob['path_id'] == pid else \
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
