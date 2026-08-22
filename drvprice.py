# -*- coding: utf-8 -*-
"""캐릭터(드라이버) 값을 프리팹에서 읽어 옵니다.

값이 데이터베이스에 없고 **화면 프리팹의 라벨에 박혀 있습니다.**
`DriverUnit` 이 카드 배열 셋을 들고 있는데(drivers · driverCheck · costInfo),
그중 `costInfo[i]` 가 i번 카드의 '값' 묶음입니다. 그 안의 UILabel 글자가
곧 트로피 값입니다.

카드 번호와 캐릭터 번호는 **한 칸 차이**입니다. 서버는 1부터 보내고
`HTTP_GetCharacterList::characterNo` 게터가 1을 빼기 때문입니다.
즉 costInfo[i] 는 characterNo i+1 입니다.

  python drvprice.py            값을 찍어 봅니다
  python drvprice.py --json     carfix 에 넣기 좋은 형태로
"""
import io
import json
import os
import struct
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sfparse import parse
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.join(HERE, 'x77')
D = os.path.join(TREE, 'assets', 'bin', 'Data')
LABEL_TEXT_OFF = 72          # UILabel 의 mText 가 시작하는 자리


def script_names():
    """sharedassets0 의 MonoScript pathID -> 이름."""
    parts = sorted([f for f in os.listdir(D)
                    if f.startswith('sharedassets0.assets.split')],
                   key=lambda x: int(x.rsplit('split', 1)[1]))
    blob = b''.join(io.open(os.path.join(D, p), 'rb').read() for p in parts)
    sf = SerializedFile(EndianBinaryReader(blob), None)
    out = {}
    for pid, o in sf.objects.items():
        if o.type.name != 'MonoScript':
            continue
        d = o.get_raw_data()
        n = struct.unpack_from('<i', d, 0)[0]
        if 0 < n < 200:
            try:
                out[pid] = d[4:4 + n].decode('utf-8')
            except UnicodeDecodeError:
                pass
    return out


def find_prefab(names):
    """DriverUnit 이 들어 있는 파일을 찾습니다."""
    want = [p for p, n in names.items() if n == 'DriverUnit']
    for fn in sorted(os.listdir(D)):
        if '.split' in fn:
            continue
        p = os.path.join(D, fn)
        try:
            meta = parse(p)
        except Exception:
            continue
        raw = None
        for o in meta['objects']:
            if o['class_id'] != 114 or o['size'] < 24:
                continue
            if raw is None:
                raw = io.open(p, 'rb').read()
            st = meta['data_offset'] + o['start']
            if struct.unpack_from('<i', raw, st + 16)[0] in want:
                return p, o['path_id']
    return None, None


def arrays_of(d):
    """DriverUnit 의 PPtr 배열 셋을 순서대로 돌려줍니다."""
    out, off = [], 0
    while off + 4 <= len(d) and len(out) < 3:
        cnt = struct.unpack_from('<i', d, off)[0]
        if 0 < cnt <= 32 and off + 4 + cnt * 8 <= len(d):
            ok = all(struct.unpack_from('<i', d, off + 4 + i * 8)[0] == 0
                     for i in range(cnt))
            if ok and cnt >= 8:
                out.append([struct.unpack_from('<i', d, off + 8 + i * 8)[0]
                            for i in range(cnt)])
                off += 4 + cnt * 8
                continue
        off += 1
    return out


def main():
    names = script_names()
    p, du = find_prefab(names)
    if p is None:
        raise SystemExit('DriverUnit 을 못 찾았습니다')
    sf = SerializedFile(EndianBinaryReader(io.open(p, 'rb').read()), None)
    arrs = arrays_of(sf.objects[du].get_raw_data())
    if len(arrs) < 3:
        raise SystemExit('카드 배열 셋을 못 찾았습니다 (찾은 것 %d개)' % len(arrs))
    cost = arrs[2]

    # 프리팹 구조 (부모->자식)
    tr, go_of = {}, {}
    comps = defaultdict(list)
    for pid, o in sf.objects.items():
        if o.type.name == 'Transform':
            t = o.read_typetree()
            tr[pid] = t
            go_of[pid] = t['m_GameObject']['m_PathID']
        elif o.type.name == 'GameObject':
            t = o.read_typetree()
            for c in t['m_Component']:
                v = c.get('component', c) if isinstance(c, dict) else c
                if isinstance(v, dict) and v.get('m_PathID'):
                    comps[pid].append(v['m_PathID'])
    t_of = dict((g, p) for p, g in go_of.items())
    label_ids = [k for k, v in names.items() if v == 'UILabel']

    def texts_under(go):
        found = []

        def walk(tp):
            g = go_of[tp]
            for c in comps.get(g, []):
                o = sf.objects.get(c)
                if o is None or o.type.name != 'MonoBehaviour':
                    continue
                d = o.get_raw_data()
                if struct.unpack_from('<i', d, 16)[0] not in label_ids:
                    continue
                if len(d) < LABEL_TEXT_OFF + 4:
                    continue
                n = struct.unpack_from('<i', d, LABEL_TEXT_OFF)[0]
                if 0 < n < 64:
                    try:
                        found.append(d[LABEL_TEXT_OFF + 4:
                                       LABEL_TEXT_OFF + 4 + n].decode('utf-8'))
                    except UnicodeDecodeError:
                        pass
            for ch in tr[tp].get('m_Children', []):
                walk(ch['m_PathID'])
        if go in t_of:
            walk(t_of[go])
        return found

    price = {}
    for i, go in enumerate(cost):
        no = i + 1
        digits = [t for t in texts_under(go) if t.strip().isdigit()]
        price[no] = int(digits[0]) if digits else None
    if '--json' in sys.argv:
        print(json.dumps(price, ensure_ascii=False))
        return 0
    print('%s 안의 캐릭터 값 (트로피)' % os.path.basename(p))
    for no in sorted(price):
        print('  %2d번  %s' % (no, price[no] if price[no] is not None else '(없음)'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
