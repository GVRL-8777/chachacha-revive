# -*- coding: utf-8 -*-
"""복제한 카드 서브트리의 오브젝트 이름 접두 번호를 바꾼다.

`LocalizePool` 은 GameObject 이름으로 라벨을 찾는다("8_Driver_Label" 등).
카드를 복제하면 내부 오브젝트가 전부 원본 번호(7_...)를 그대로 갖고 있어
`SetLabelActive("8_Driver_Label")` 이 "Not find" 로 실패한다.

GameObject 이름은 타입트리로 안전하게 읽고 쓸 수 있다(길이가 바뀌므로 재조립).

사용법: python renamecard.py <입력> <출력> <카드루트이름>=<옛번호>:<새번호> ...
"""
import io, re, struct, sys
from sfparse import parse
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile
from sfwrite import ALIGN

SRC, OUT = sys.argv[1], sys.argv[2]
JOBS = []
for a in sys.argv[3:]:
    card, nums = a.split('=')
    old, new = nums.split(':')
    JOBS.append((card, old, new))


def main():
    meta = parse(SRC)
    raw = io.open(SRC, 'rb').read()
    sf = SerializedFile(EndianBinaryReader(raw), None)

    gname, tr = {}, {}
    for p, o in sf.objects.items():
        if o.type.name == 'GameObject':
            gname[p] = o.read_typetree()['m_Name']
        elif o.type.name == 'Transform':
            tr[p] = o.read_typetree()
    go_of = {p: t['m_GameObject']['m_PathID'] for p, t in tr.items()}
    t_of = {g: p for p, g in go_of.items()}

    patched = {}
    for card, old, new in JOBS:
        root = [p for p, n in gname.items() if n == card][0]
        subs = []

        def walk(tp):
            subs.append(go_of[tp])
            for c in tr[tp].get('m_Children', []):
                walk(c['m_PathID'])
        walk(t_of[root])
        cnt = 0
        for g in subs:
            if g == root:
                continue          # 루트 이름은 이미 새 이름
            n = gname[g]
            m = re.match(r'^%s_(.*)$' % re.escape(old), n)
            if not m:
                continue
            newn = '%s_%s' % (new, m.group(1))
            o = sf.objects[g]
            t = o.read_typetree()
            t['m_Name'] = newn
            patched[g] = bytes(o.save_typetree(t))
            cnt += 1
        print("  %-20s %s_* -> %s_*  (%d개)" % (card, old, new, cnt))

    # 재조립
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
    print("출력: %s (%d B) / 이름 %d개 변경" % (OUT, len(ob), len(patched)))


if __name__ == '__main__':
    main()
