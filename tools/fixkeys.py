# -*- coding: utf-8 -*-
"""복제 카드의 UILocalize 키를 복구하고 9~12번용으로 바꾼다.

`clonecard.py` 의 바이트 수준 PPtr 치환이 **문자열 길이 필드까지 pathID 로 착각**해
덮어썼다(예: 길이 5 -> 456). 문자열 본문은 그대로 남아 있으므로 길이만 되돌리면 된다.

UILocalize 레이아웃(36바이트 고정):
    @0  m_GameObject PPtr(8)
    @8  m_Enabled(4)
    @12 m_Script PPtr(8)
    @24 key 길이(int)
    @28 key 바이트(4정렬)

키 이름도 카드에 맞게 교체한다(Char8/Char8Exp -> Char9~12 / Char9Exp~12Exp).
같은 길이면 제자리, 길이가 다르면 파일을 재조립한다.
"""
import io
import struct
import sys
from collections import defaultdict

from sfparse import parse
from sfwrite import ALIGN
from UnityPy.files.SerializedFile import SerializedFile
from UnityPy.streams import EndianBinaryReader

SRC, OUT = sys.argv[1], sys.argv[2]
# 카드이름 -> (이름키, 설명키)
JOBS = {
    '8_Driver_Jeongbi': ('Char9', 'Char9Exp'),
    '9_Driver_Byul': ('Char10', 'Char10Exp'),
    '10_Driver_Samba': ('Char11', 'Char11Exp'),
    '11_Driver_Handol': ('Char12', 'Char12Exp'),
}
CN_SA0 = 'survey/5577.com.cjenm.chachachacn/assets/bin/Data/sharedassets0.assets'
KEYOFF = 24


def make(d, newkey):
    """UILocalize 블롭의 키를 newkey 로 바꾼 새 바이트를 만든다."""
    head = bytes(d[:KEYOFF])
    nb = newkey.encode('utf-8')
    field = struct.pack('<i', len(nb)) + nb
    while len(field) % 4:
        field += b'\x00'
    return head + field


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
    for card, (namekey, expkey) in JOBS.items():
        root = [p for p, n in gname.items() if n == card][0]
        for g in sub(root):
            for c in comps.get(g, []):
                o = sf.objects[c]
                if o.type.name != 'MonoBehaviour':
                    continue
                if names.get(struct.unpack_from('<i', o.get_raw_data(), 16)[0]) != 'UILocalize':
                    continue
                nm = gname[g]
                if nm.endswith('_Name_Label'):
                    k = namekey
                elif nm.endswith('_Info_Label'):
                    k = expkey
                elif nm.endswith('_Driver_Label'):
                    k = 'CharEuip'
                else:
                    continue
                patched[c] = make(o.get_raw_data(), k)
                print("  %-20s %-16s -> %s" % (card, nm, k))

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
    print("출력: %s (%d B) / UILocalize %d개 수정" % (OUT, len(ob2), len(patched)))


if __name__ == '__main__':
    main()
