# -*- coding: utf-8 -*-
"""카드의 초상화 UISprite 이름을 임의로 바꾼다(길이 달라도 됨).

사용법: python setpc.py <입력> <출력> <카드GO이름>=<새스프라이트이름> ...
"""
import io, struct, sys
from collections import defaultdict
from sfparse import parse
from sfwrite import ALIGN
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile

SRC, OUT = sys.argv[1], sys.argv[2]
MAP = dict(a.split('=') for a in sys.argv[3:])
CN_SA0 = 'survey/5577.com.cjenm.chachachacn/assets/bin/Data/sharedassets0.assets'
NAME_OFF = 72          # UISprite 의 mSpriteName 필드 위치(실측)


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

    def sub(root):
        out = []

        def w(tp):
            out.append(go_of[tp])
            for c in tr[tp].get('m_Children', []):
                w(c['m_PathID'])
        w(t_of[root])
        return out

    patched = {}
    for card, newname in MAP.items():
        root = [p for p, n in gname.items() if n == card][0]
        for g in sub(root):
            if not gname[g].startswith('PTDriverPc'):
                continue
            for c in comps.get(g, []):
                o = sf.objects[c]
                if o.type.name != 'MonoBehaviour':
                    continue
                if names.get(struct.unpack_from('<i', o.get_raw_data(), 16)[0]) != 'UISprite':
                    continue
                d = o.get_raw_data()
                ln = struct.unpack_from('<i', d, NAME_OFF)[0]
                old = d[NAME_OFF + 4:NAME_OFF + 4 + ln].decode()
                tail = d[NAME_OFF + 4 + ((ln + 3) & ~3):]
                nb = newname.encode()
                field = struct.pack('<i', len(nb)) + nb
                while len(field) % 4:
                    field += b'\x00'
                patched[c] = bytes(d[:NAME_OFF]) + field + tail
                print("  %-22s %s -> %s" % (card, old, newname))

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
    print("출력: %s (%d B) / %d개 수정" % (OUT, len(ob2), len(patched)))


if __name__ == '__main__':
    main()
