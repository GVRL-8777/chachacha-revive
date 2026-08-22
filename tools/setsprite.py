# -*- coding: utf-8 -*-
"""복제한 드라이버 카드의 초상화 스프라이트 이름을 바꾼다.

카드의 초상화는 `PTDriverPc ( Sprite )` GameObject 에 붙은 UISprite 컴포넌트가
`mSpriteName` 필드로 들고 있다. 복제본은 전부 원본과 같은 "PTDriverPc" 를 가리키므로
카드마다 PTDriverPc8/9/10/11 로 바꿔 줘야 한다.

MonoBehaviour 라 타입트리가 없다. 다행히 스프라이트 이름은 길이 접두 문자열이라
바이트에서 찾아 **같은 길이로 맞춘 새 이름**으로 덮어쓰면 크기가 안 변한다.
"PTDriverPc"(10자) -> "PTDriverPc8"(11자) 는 길이가 달라지므로,
파일을 재조립하며 해당 오브젝트만 길이를 늘린다.

사용법: python setsprite.py <입력> <출력> <카드GO이름>=<새스프라이트> ...
"""
import io, struct, sys
from collections import defaultdict
from sfparse import parse
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile
from sfwrite import ALIGN

SRC, OUT = sys.argv[1], sys.argv[2]
MAP = dict(a.split('=') for a in sys.argv[3:])
OLD = b'PTDriverPc'


def main():
    meta = parse(SRC)
    raw = io.open(SRC, 'rb').read()
    sf = SerializedFile(EndianBinaryReader(raw), None)

    gname, tr, comps = {}, {}, defaultdict(list)
    for p, o in sf.objects.items():
        if o.type.name == 'GameObject':
            t = o.read_typetree()
            gname[p] = t['m_Name']
            for c in t['m_Component']:
                v = c[1] if isinstance(c, (list, tuple)) and len(c) == 2 else None
                if isinstance(v, dict) and v.get('m_PathID'):
                    comps[p].append(v['m_PathID'])
        elif o.type.name == 'Transform':
            tr[p] = o.read_typetree()
    go_of = {p: t['m_GameObject']['m_PathID'] for p, t in tr.items()}
    t_of = {g: p for p, g in go_of.items()}

    patched = {}
    for card, newname in MAP.items():
        root = [p for p, n in gname.items() if n == card][0]
        # 서브트리에서 'PTDriverPc ( Sprite )' 오브젝트의 UISprite 찾기
        found = None
        def walk(tp):
            nonlocal found
            g = go_of[tp]
            if gname[g].startswith('PTDriverPc'):
                for c in comps.get(g, []):
                    o = sf.objects[c]
                    if o.type.name == 'MonoBehaviour' and OLD in o.get_raw_data():
                        found = c
                        return
            for ch in tr[tp].get('m_Children', []):
                walk(ch['m_PathID'])
        walk(t_of[root])
        if found is None:
            print("  %-20s 초상화 UISprite 못 찾음" % card)
            continue
        d = bytearray(sf.objects[found].get_raw_data())
        # 길이 접두 문자열 "PTDriverPc" 찾기
        idx = d.find(struct.pack('<i', len(OLD)) + OLD)
        if idx < 0:
            print("  %-20s 이름 필드 못 찾음" % card)
            continue
        nb = newname.encode('utf-8')
        head = d[:idx]
        tailstart = idx + 4 + ((len(OLD) + 3) & ~3)
        tail = d[tailstart:]
        newfield = struct.pack('<i', len(nb)) + nb
        while len(newfield) % 4:
            newfield += b'\x00'
        patched[found] = bytes(head + newfield + tail)
        print("  %-20s UISprite pathID=%-4s  PTDriverPc -> %s" % (card, found, newname))

    # 파일 재조립
    objs = sorted(meta['objects'], key=lambda o: o['start'])
    data = bytearray()
    newobjs = []
    for o in objs:
        while len(data) % 8:
            data.append(0)
        st = len(data)
        blob = patched.get(o['path_id']) or \
            raw[meta['data_offset'] + o['start']: meta['data_offset'] + o['start'] + o['size']]
        data += blob
        newobjs.append(dict(o, start=st, size=len(blob)))

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
    print("출력: %s (%d B) / 스프라이트 %d개 변경" % (OUT, len(ob), len(patched)))


if __name__ == '__main__':
    main()
