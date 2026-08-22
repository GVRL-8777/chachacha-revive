# -*- coding: utf-8 -*-
"""프리팹 안의 서브트리(드라이버 카드)를 통째로 복제한다.

DriverUnit 프리팹의 카드 한 장은 GameObject 14개 + 그 컴포넌트들로 이뤄져 있다.
이걸 그대로 복제하되:
  · 새 pathID 를 부여하고
  · 서브트리 **내부**를 가리키는 PPtr 은 새 id 로 바꾸고
  · 서브트리 **밖**(아틀라스, 폰트, 스크립트 등)을 가리키는 PPtr 은 그대로 두고
  · 복제본의 루트 Transform 을 원본의 부모(DriverUnit 루트)에 자식으로 등록한다.

MonoBehaviour 는 타입트리가 없으므로 바이트 수준으로 PPtr 을 고친다.
같은 배포판 안에서의 복제라 **필드 구성이 동일**하므로 이 방식이 안전하다
(배포판 간 이식에서 실패했던 것과는 상황이 다르다).

사용법:
  python clonecard.py <프리팹> <출력> <원본루트GO이름> <새이름>:<x>,<y> ...
"""
import io, re, struct, sys
from collections import defaultdict
from sfparse import parse
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile
from sfwrite import ALIGN


def load(path):
    meta = parse(path)
    raw = io.open(path, 'rb').read()
    sf = SerializedFile(EndianBinaryReader(raw), None)
    return meta, raw, sf


def main():
    src, out, rootname = sys.argv[1], sys.argv[2], sys.argv[3]
    specs = []
    for s in sys.argv[4:]:
        nm, xy = s.split(':')
        x, y = xy.split(',')
        specs.append((nm, float(x), float(y)))

    meta, raw, sf = load(src)
    objs = {o['path_id']: o for o in meta['objects']}

    # --- 구조 파악 ---
    names, tr, go_comps = {}, {}, defaultdict(list)
    for p, o in sf.objects.items():
        if o.type.name == 'GameObject':
            t = o.read_typetree()
            names[p] = t['m_Name']
            for c in t['m_Component']:
                v = c.get('component', c) if isinstance(c, dict) else c
                if isinstance(v, dict) and v.get('m_PathID'):
                    go_comps[p].append(v['m_PathID'])
        elif o.type.name == 'Transform':
            tr[p] = o.read_typetree()
    go_of = {p: t['m_GameObject']['m_PathID'] for p, t in tr.items()}
    t_of = {g: p for p, g in go_of.items()}

    root_go = [p for p, n in names.items() if n == rootname][0]
    root_t = t_of[root_go]
    parent_t = tr[root_t]['m_Father']['m_PathID']
    print("원본 카드 '%s' GO=%d T=%d 부모T=%d" % (rootname, root_go, root_t, parent_t))

    # 서브트리 수집
    subtree_t = []

    def walk(tp):
        subtree_t.append(tp)
        for c in tr[tp].get('m_Children', []):
            walk(c['m_PathID'])
    walk(root_t)
    members = set()
    for tp in subtree_t:
        members.add(tp)
        g = go_of[tp]
        members.add(g)
        members.update(go_comps.get(g, []))
    print("서브트리 오브젝트 %d개 (Transform %d)" % (len(members), len(subtree_t)))

    maxid = max(sf.objects.keys())
    data = bytearray(raw[meta['data_offset']:])
    newobjs = list(meta['objects'])
    all_children_add = []

    for ci, (newname, nx, ny) in enumerate(specs):
        base = maxid + 1 + ci * (len(members) + 4)
        idmap = {}
        for i, m in enumerate(sorted(members)):
            idmap[m] = base + i
        print("  복제 %d: '%s' -> pathID %d..%d" % (ci + 1, newname, base, base + len(members) - 1))

        for m in sorted(members):
            o = sf.objects[m]
            blob = bytearray(o.get_raw_data())
            tn = o.type.name
            if tn in ('GameObject', 'Transform'):
                t = o.read_typetree()
                # 내부 PPtr 재배선
                def fix(n):
                    if isinstance(n, dict):
                        if set(n.keys()) == {'m_FileID', 'm_PathID'}:
                            if n['m_FileID'] == 0 and n['m_PathID'] in idmap:
                                n['m_PathID'] = idmap[n['m_PathID']]
                            return
                        for v in n.values():
                            fix(v)
                    elif isinstance(n, (list, tuple)):
                        for v in n:
                            fix(v)
                fix(t)
                if tn == 'GameObject':
                    t['m_Name'] = newname if m == root_go else t['m_Name']
                if tn == 'Transform' and m == root_t:
                    t['m_Father'] = {'m_FileID': 0, 'm_PathID': parent_t}
                    t['m_LocalPosition']['x'] = nx
                    t['m_LocalPosition']['y'] = ny
                blob = bytearray(o.save_typetree(t))
            else:
                # MonoBehaviour 등: 바이트 수준 PPtr 치환 (같은 판본이라 레이아웃 동일)
                for off in range(0, len(blob) - 7, 4):
                    fid = struct.unpack_from('<i', blob, off)[0]
                    pid = struct.unpack_from('<i', blob, off + 4)[0]
                    if fid == 0 and pid in idmap:
                        struct.pack_into('<i', blob, off + 4, idmap[pid])
            while len(data) % 8:
                data.append(0)
            st = len(data)
            data += bytes(blob)
            newobjs.append({'path_id': idmap[m], 'start': st, 'size': len(blob),
                            'type_id': int(o.class_id), 'class_id': int(o.class_id),
                            'destroyed': 0})
        all_children_add.append(idmap[root_t])

    # --- 부모 Transform 에 새 자식 등록 ---
    pt = sf.objects[parent_t]
    t = pt.read_typetree()
    for c in all_children_add:
        t['m_Children'].append({'m_FileID': 0, 'm_PathID': c})
    newblob = bytes(pt.save_typetree(t))
    while len(data) % 8:
        data.append(0)
    st = len(data)
    data += newblob
    for o in newobjs:
        if o['path_id'] == parent_t:
            o['start'], o['size'] = st, len(newblob)
            break
    print("부모 Transform 자식 %d개 추가 (크기 %d)" % (len(all_children_add), len(newblob)))

    # --- 파일 재조립 ---
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
    print("출력: %s (%d B, 원본 %d B, 오브젝트 %d)" % (out, len(outb), len(raw), len(newobjs)))


if __name__ == '__main__':
    main()
