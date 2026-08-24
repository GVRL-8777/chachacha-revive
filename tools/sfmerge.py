# -*- coding: utf-8 -*-
"""여러 직렬화 파일을 **하나의** 번들용 직렬화 파일로 합친다.

sfwrite3.py 의 일반화판. 앞으로 맵뿐 아니라 드라이버/차량 자산도 한 번들에
여러 개 담아야 하므로 N개 입력을 받는다.

지켜야 하는 것 (실기에서 확인):
  · AssetBundle 매니페스트는 반드시 pathID 1 이어야 엔진이 읽는다.
  · PPtr 재번호는 바이트 검색이 아니라 타입트리 왕복으로 해야 데이터가 안 깨진다.
  · 각 원본의 데이터 배치(오프셋/정렬)는 그대로 두고 블록째 옮긴다.

사용법:
  python sfmerge.py <출력> <번들이름> <파일>:<자산이름>:<루트pathID>[:<dx>] ...
      dx 를 주면 그 원본의 **루트 Transform** x 좌표에 더한다(도로 중심 보정).
"""
import struct, io, os, sys
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile
from sfparse import parse
from sfwrite import make_manifest, ALIGN


def walk_pptr(node, fn):
    """타입트리 dict 를 훑어 모든 PPtr 에 fn(dict) 을 적용한다."""
    n = 0
    if isinstance(node, dict):
        if set(node.keys()) == {'m_FileID', 'm_PathID'}:
            return fn(node)
        for v in node.values():
            n += walk_pptr(v, fn)
    elif isinstance(node, (list, tuple)):
        for v in node:
            n += walk_pptr(v, fn)
    return n


def merge(out_path, bundle_name, specs, nomanifest=False):
    """nomanifest 를 주면 매니페스트(pathID 1)를 만들지 않는다.

    `packadd` 로 **이미 구운 번들에 덧붙일** 때 쓴다. 그 번들엔 매니페스트가
    이미 있으므로 여기서 또 만들면 AssetBundle 오브젝트가 둘이 되어
    엔진과 `packadd` 가 어느 쪽을 볼지 알 수 없게 된다.
    (이름, pathID) 목록을 돌려주므로 그대로 `packadd` 스펙에 쓸 수 있다."""
    srcs = []
    flattened = 0
    ext_order = []          # 합친 외부 파일 목록 (이름 순서가 곧 fileID-1)
    for sp in specs:
        parts = sp.split(':')
        path, name, mainpid = parts[0], parts[1], int(parts[2])
        dx = float(parts[3]) if len(parts) > 3 else 0.0
        opts = set(parts[4:])
        flat = 'flat' in opts
        keepscript = 'keepscript' in opts
        # also=<번들이름>@<pathID> — 한 파일에서 자산을 **여러 이름**으로 낸다.
        # 차 재질은 프리팹이 직접 가리켜도 소용없고, 게임이 실행 중에
        # `car/<이름>/materials/<이름>` 로 다시 찾아 덮어쓴다(실기 확인).
        # mbptr=<pathID>@<바이트오프셋> — 타입트리 없는 MonoBehaviour 안의
        # PPtr 자리. 스크립트가 들고 있는 재질 참조가 여기 있다.
        mbptrs = []
        for o in parts[4:]:
            if o.startswith('mbptr='):
                pid3, _, off3 = o[6:].rpartition('@')
                mbptrs.append((int(pid3), int(off3)))
        extra = []
        for o in parts[4:]:
            if o.startswith('also='):
                nm2, _, pid2 = o[5:].rpartition('@')
                extra.append((nm2, int(pid2)))
        meta = parse(path)
        sf = SerializedFile(EndianBinaryReader(io.open(path, 'rb').read()), None)
        for e in meta['externals']:
            if e not in ext_order:
                ext_order.append(e)
        srcs.append(dict(path=path, name=name, mainpid=mainpid, dx=dx,
                         flat=flat, keepscript=keepscript, extra=extra, mbptrs=mbptrs,
                         meta=meta, sf=sf))

    # 루트 Transform(부모가 없는 것)을 미리 찾아 둔다. flat 보정에 쓴다.
    for s0 in srcs:
        rs = set()
        for pid, o in s0['sf'].objects.items():
            if o.type.name != 'Transform':
                continue
            try:
                if o.read_typetree()['m_Father']['m_PathID'] == 0:
                    rs.add(pid)
            except Exception:
                pass
        s0['roots'] = rs

    # 새 pathID 배정 (1 번은 매니페스트 몫)
    nxt = 2
    for s in srcs:
        s['map'] = {}
        for pid in sorted(s['sf'].objects.keys()):
            s['map'][pid] = nxt
            nxt += 1

    by_name = dict((os.path.basename(s0['path']), s0) for s0 in srcs)
    ext_order = [e for e in ext_order if os.path.basename(e) not in by_name]

    data = bytearray()
    objs = []
    total_ptr = 0
    for s in srcs:
        meta, sf, pmap = s['meta'], s['sf'], s['map']
        ext_map = dict((i + 1, ext_order.index(e) + 1)
                       for i, e in enumerate(meta['externals'])
                       if e in ext_order)
        raw = io.open(s['path'], 'rb').read()[meta['data_offset']:]
        base = len(data)
        while base % 16:
            data.append(0)
            base = len(data)
        blk_len = max(o['start'] + o['size'] for o in meta['objects'])
        data += raw[:blk_len]
        orig = dict((o['path_id'], o) for o in meta['objects'])

        def fix(p):
            if p['m_FileID'] == 0:
                if p['m_PathID'] in pmap:
                    p['m_PathID'] = pmap[p['m_PathID']]
                    return 1
                return 0
            nm = os.path.basename(meta['externals'][p['m_FileID'] - 1])
            tgt = by_name.get(nm)
            if tgt is not None and p['m_PathID'] in tgt['map']:
                p['m_FileID'] = 0
                p['m_PathID'] = tgt['map'][p['m_PathID']]
                return 1
            p['m_FileID'] = ext_map[p['m_FileID']]
            return 1

        for pid in sorted(sf.objects.keys()):
            o = sf.objects[pid]
            if o.type.name == 'MonoBehaviour':
                #   0..7  m_GameObject(fileID,pathID)  8 m_Enabled  12..19 m_Script
                rec = orig[pid]
                st0 = base + rec['start']
                gf, gp = struct.unpack_from('<ii', data, st0)
                if gf == 0 and gp in pmap:
                    struct.pack_into('<ii', data, st0, 0, pmap[gp])
                elif gf:
                    nm0 = os.path.basename(meta['externals'][gf - 1])
                    t0 = by_name.get(nm0)
                    if t0 is not None and gp in t0['map']:
                        struct.pack_into('<ii', data, st0, 0, t0['map'][gp])
                    elif gf in ext_map:
                        struct.pack_into('<ii', data, st0, ext_map[gf], gp)
                if s['keepscript']:
                    # 자동차 프리팹은 스크립트가 살아 있어야 굴러간다.
                    # 스크립트는 sharedassets0 에 있으니 외부 참조만 새 번호로 옮긴다.
                    sf0, sp0 = struct.unpack_from('<ii', data, st0 + 12)
                    if sf0 and sf0 in ext_map:
                        struct.pack_into('<ii', data, st0 + 12, ext_map[sf0], sp0)
                else:
                    struct.pack_into('<ii', data, st0 + 12, 0, 0)   # 스크립트는 비운다
                for mpid, moff in s['mbptrs']:
                    if mpid != pid:
                        continue
                    # 타입트리 있는 오브젝트와 **같은 규칙**으로 옮긴다.
                    # 안쪽이면 새 번호로, 합치는 다른 파일을 가리키면 안쪽으로
                    # 끌어들이고, 바깥이면 새 외부 목록 자리로 옮긴다.
                    f2, p2 = struct.unpack_from('<ii', data, st0 + moff)
                    if f2 or p2:
                        q = {'m_FileID': f2, 'm_PathID': p2}
                        fix(q)
                        struct.pack_into('<ii', data, st0 + moff,
                                         q['m_FileID'], q['m_PathID'])
                objs.append({'path_id': pmap[pid], 'start': st0, 'size': rec['size'],
                             'type_id': int(o.class_id), 'class_id': int(o.class_id),
                             'destroyed': 0})
                continue
            tree = o.read_typetree()
            # Background::GetNextMap 은 조각의 **루트** Transform 에
            # localPosition=(0,0,100), localRotation=Euler(270,0,0) 을 강제로 씌운다.
            # 중국판 조각은 Transform 이 루트 하나뿐이라 값이 같아 맞아떨어진다.
            # 이식해 온 조각은 루트가 항등이고 **자식**이 -90°X 를 들고 있어,
            # 엔진이 루트에 -90°X 를 또 씌우면 합이 -180°X 가 되어 맵이 뒤집혀 선다.
            # flat 을 주면 그 자식 회전을 항등으로 되돌린다. (보정도 자식에 넣는다)
            if o.type.name == 'Transform':
                pa = tree['m_Father']['m_PathID']
                if s['flat'] and pa in s['roots']:
                    r = tree['m_LocalRotation']
                    if (r['x'], r['y'], r['z'], r['w']) != (0.0, 0.0, 0.0, 1.0):
                        r['x'] = r['y'] = r['z'] = 0.0
                        r['w'] = 1.0
                        tree['m_LocalPosition']['x'] += s['dx']
                        flattened += 1
                elif s['dx'] and pa == 0 and not s['flat']:
                    tree['m_LocalPosition']['x'] += s['dx']
            total_ptr += walk_pptr(tree, fix)
            blob = bytes(o.save_typetree(tree))
            if len(blob) != orig[pid]['size']:
                raise SystemExit("길이가 달라졌다: %s pathID %d (%d -> %d)"
                                 % (s['path'], pid, orig[pid]['size'], len(blob)))
            st = base + orig[pid]['start']
            data[st:st + len(blob)] = blob
            objs.append({'path_id': pmap[pid], 'start': st, 'size': len(blob),
                         'type_id': int(o.class_id), 'class_id': int(o.class_id),
                         'destroyed': 0})

    print("  자식 회전 항등화 %d개" % flattened)
    entries = []
    for s in srcs:
        entries.append((s['name'], s['map'][s['mainpid']]))
        for nm2, pid2 in s.get('extra', []):
            entries.append((nm2, s['map'][pid2]))
    if not nomanifest:
        manifest = make_manifest(bundle_name, entries,
                                 (0, srcs[0]['map'][srcs[0]['mainpid']]))
        while len(data) % 8:
            data.append(0)
        man_start = len(data)
        data += manifest
        objs.insert(0, {'path_id': 1, 'start': man_start, 'size': len(manifest),
                        'type_id': 142, 'class_id': 142, 'destroyed': 0})

    m0 = srcs[0]['meta']
    meta = m0['unity'].encode('utf-8') + b'\x00'
    meta += struct.pack('<i', m0['platform'])
    meta += struct.pack('<i', 0)                     # type_count (플레이어 빌드)
    meta += struct.pack('<i', m0['big_id'])
    meta += struct.pack('<i', len(objs))
    for o in objs:
        meta += struct.pack('<iIIiHh', o['path_id'], o['start'], o['size'],
                            o['type_id'], o['class_id'], o['destroyed'])
    import json, os.path as _op
    _ren = {}
    if _op.exists('rename_ov.json'):
        _ren = json.load(io.open('rename_ov.json', encoding='utf-8'))
    ext_order = [_ren.get(_op.basename(e), e) for e in ext_order]
    meta += struct.pack('<i', len(ext_order))
    for name in ext_order:
        meta += b'\x00' + b'\x00' * 16 + struct.pack('<i', 0) + name.encode('utf-8') + b'\x00'
    meta += b'\x00'

    data_offset = max(m0['data_offset'], ALIGN(20 + len(meta) + 64))
    head = struct.pack('>IIII', len(meta), data_offset + len(data), 9, data_offset)
    head += bytes([1 if m0['endian'] == '>' else 0, 0, 0, 0])
    out = bytearray(head + meta)
    while len(out) < data_offset:
        out += b'\x00'
    out += data
    io.open(out_path, 'wb').write(bytes(out))
    print("생성: %s (%d B) | 오브젝트 %d개 | 외부 %d개 | PPtr %d개 재배선"
          % (out_path, len(out), len(objs), len(ext_order), total_ptr))

    if nomanifest:
        return entries
    sf2 = SerializedFile(EndianBinaryReader(io.open(out_path, 'rb').read()), None)
    ab = [o for p, o in sf2.objects.items() if o.type.name == 'AssetBundle'][0].read_typetree()
    print("  매니페스트 항목: %s"
          % [(c[0], c[1]['asset']['m_PathID']) for c in ab['m_Container']])
    return entries


if __name__ == '__main__':
    specs = []
    for a in sys.argv[3:]:
        if a.startswith('@'):
            for ln in io.open(a[1:], encoding='utf-8').read().splitlines():
                if ln.strip():
                    specs.append(ln.strip())
        else:
            specs.append(a)
    merge(sys.argv[1], sys.argv[2], specs)
