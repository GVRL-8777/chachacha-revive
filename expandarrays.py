# -*- coding: utf-8 -*-
"""DriverUnit MonoBehaviour 의 배열 3개를 8칸 -> 12칸으로 늘린다.

DriverUnit 은 카드 UI 를 배열로 들고 있다:
    drivers     GameObject[8]
    driverCheck UICheckbox[8]
    costInfo    GameObject[8]
`SetDriverState` 는 driverCheck.Length 가 인덱스보다 작으면
"Not Ready DriverCheckUI" 를 찍고 **루프를 중단**한다. 그래서 슬롯 상한(12)만
올려서는 9번째 카드가 안 보인다.

복제한 카드 4장에서 대응하는 오브젝트를 찾아 각 배열 뒤에 이어 붙인다.
MonoBehaviour 라 타입트리가 없으므로 바이트 수준으로 다룬다.
"""
import io, struct, sys
from collections import defaultdict
from sfparse import parse
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile
from sfwrite import ALIGN

SRC, OUT = sys.argv[1], sys.argv[2]
NEW_CARDS = sys.argv[3:]      # 새 카드 루트 GameObject 이름 4개


def main():
    meta = parse(SRC)
    raw = io.open(SRC, 'rb').read()
    sf = SerializedFile(EndianBinaryReader(raw), None)

    # 스크립트 이름 -> pathID (중국판 sharedassets0)
    names = {}
    s0 = SerializedFile(EndianBinaryReader(io.open(
        'survey/5577.com.cjenm.chachachacn/assets/bin/Data/sharedassets0.assets', 'rb').read()), None)
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

    # 프리팹 구조
    gname, tr, comps = {}, {}, defaultdict(list)
    for p, o in sf.objects.items():
        if o.type.name == 'GameObject':
            t = o.read_typetree()
            gname[p] = t['m_Name']
            for c in t['m_Component']:
                v = c.get('component', c) if isinstance(c, dict) else c
                if isinstance(v, dict) and v.get('m_PathID'):
                    comps[p].append(v['m_PathID'])
        elif o.type.name == 'Transform':
            tr[p] = o.read_typetree()
    go_of = {p: t['m_GameObject']['m_PathID'] for p, t in tr.items()}
    t_of = {g: p for p, g in go_of.items()}

    # DriverUnit 컴포넌트 찾기
    du_pid = None
    for pid, o in sf.objects.items():
        if o.type.name != 'MonoBehaviour':
            continue
        d = o.get_raw_data()
        if names.get(struct.unpack_from('<i', d, 16)[0]) == 'DriverUnit':
            du_pid = pid
            break
    d = bytearray(sf.objects[du_pid].get_raw_data())
    print("DriverUnit pathID=%d (%d바이트)" % (du_pid, len(d)))

    # 새 카드에서 필요한 오브젝트 수집
    def find_child(root_go, pred):
        """루트 GameObject 서브트리에서 조건에 맞는 첫 GameObject/컴포넌트 반환"""
        out = []
        def walk(tp):
            g = go_of[tp]
            out.append(g)
            for c in tr[tp].get('m_Children', []):
                walk(c['m_PathID'])
        walk(t_of[root_go])
        return [g for g in out if pred(g)]

    add_drivers, add_check, add_cost = [], [], []
    for nm in NEW_CARDS:
        root = [p for p, n in gname.items() if n == nm][0]
        add_drivers.append(root)
        # UICheckbox 컴포넌트를 가진 자식
        chk = None
        cost = None
        for g in find_child(root, lambda x: True):
            for c in comps.get(g, []):
                o = sf.objects[c]
                if o.type.name != 'MonoBehaviour':
                    continue
                sn = names.get(struct.unpack_from('<i', o.get_raw_data(), 16)[0])
                if sn == 'UICheckbox' and chk is None:
                    chk = c
            if gname[g].endswith('_CostInfo') and cost is None:
                cost = g
        add_check.append(chk)
        add_cost.append(cost)
        print("  %-20s GO=%-4s check=%-5s cost=%-5s" % (nm, root, chk, cost))

    if any(x is None for x in add_check):
        raise SystemExit("UICheckbox 를 못 찾았다 — 복제 구조 확인 필요")

    # 배열 3개를 12칸으로: @48(drivers), 그 뒤 driverCheck, costInfo
    # 배열 레이아웃: int count + PPtr(8B) * count
    out = bytearray()
    off = 0
    arrays_done = 0
    while off < len(d):
        if arrays_done < 3 and off + 4 <= len(d):
            cnt = struct.unpack_from('<i', d, off)[0]
            if cnt == 8 and off + 4 + 8 * 8 <= len(d):
                # 8칸 PPtr 배열로 보이는지 검증 (fileID 는 전부 0)
                ok = all(struct.unpack_from('<i', d, off + 4 + i * 8)[0] == 0 for i in range(8))
                if ok:
                    extra = [add_drivers, add_check, add_cost][arrays_done]
                    out += struct.pack('<i', 8 + len(extra))
                    out += d[off + 4: off + 4 + 64]
                    for e in extra:
                        out += struct.pack('<ii', 0, e)
                    print("  배열%d: 8 -> %d칸" % (arrays_done + 1, 8 + len(extra)))
                    off += 4 + 64
                    arrays_done += 1
                    continue
        out.append(d[off])
        off += 1
    print("DriverUnit %d -> %d 바이트 (배열 %d개 확장)" % (len(d), len(out), arrays_done))

    # 파일 재조립
    objs = sorted(meta['objects'], key=lambda o: o['start'])
    data = bytearray()
    newobjs = []
    for o in objs:
        while len(data) % 8:
            data.append(0)
        st = len(data)
        blob = bytes(out) if o['path_id'] == du_pid else \
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
    print("출력: %s (%d B)" % (OUT, len(ob)))


if __name__ == '__main__':
    main()
