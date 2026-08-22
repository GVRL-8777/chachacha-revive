# -*- coding: utf-8 -*-
# 잃어버린 sfmerge.py 를 되살리던 중간본. 완성본은 tools/sfmerge.py.
"""여러 직렬화 파일을 **하나의** 번들용 직렬화 파일로 합친다.

sfwrite3.py 의 일반화판. 앞으로 맵뿐 아니라 드라이버/차량 자산도 한 번들에
여러 개 담아야 하므로 N개 입력을 받는다.

지켜야 하는 것 (실기에서 확인):
  · AssetBundle 매니페스트는 반드시 pathID 1 이어야 엔진이 읽는다.
  · PPtr 재번호는 바이트 검색이 아니라 타입트리 왕복으로 해야 데이터가 안 깨진다.
  · 각 원본의 데이터 배치(오프셋/정렬)는 그대로 두고 블록째 옮긴다.

사용법:
  python sfmerge.py <출력> <번들이름> <파일>:<자산이름>:<루트pathID>[:<dx>[:flat]] ...
      dx  : 그 원본의 자식 Transform x 좌표에 더한다(좌우 보정).\n
"""
import json, struct, io, os, sys
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


def merge(out_path, bundle_name, specs):
    srcs = []
    ext_order = []          # 합친 외부 파일 목록 (이름 순서가 곧 fileID-1)
    for sp in specs:
        parts = sp.split(':')
        path, name, mainpid = parts[0], parts[1], int(parts[2])
        dx = float(parts[3]) if len(parts) > 3 else 0.0
        flat = len(parts) > 4 and parts[4] == 'flat'
        meta = parse(path)
        sf = SerializedFile(EndianBinaryReader(io.open(path, 'rb').read()), None)
        for e in meta['externals']:
            if e not in ext_order:
                ext_order.append(e)
        srcs.append(dict(path=path, name=name, mainpid=mainpid, dx=dx,
                         meta=meta, sf=sf))

    # 새 pathID 배정 (1 번은 매니페스트 몫)
    nxt = 2
    for s in srcs:
        s['map'] = {}
        for pid in sorted(s['sf'].objects.keys()):
            s['map'][pid] = nxt
            nxt += 1

    # 한 번들에 같이 들어가는 것끼리의 참조는 바깥 참조가 아니라 내부 참조여야 한다.
    # 그런 대상은 바깥 목록에서도 빼야 엔진이 없는 파일을 찾지 않는다.
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

        # 이 원본에서 sharedassets0 을 가리키는 외부 색인(스크립트가 거기 있다)
        script_ext_ids = set(i + 1 for i, e in enumerate(meta['externals'])
                             if 'sharedassets0' in e)
        for pid in sorted(sf.objects.keys()):
            o = sf.objects[pid]
            try:
                tree = o.read_typetree()
            except Exception:
                # MonoBehaviour 등 타입트리가 없는 오브젝트: 바이트째 옮긴다
                blob, nf = fix_raw_pptrs(o.get_raw_data(), pmap, ext_map, script_ext_ids)
                total_ptr += nf
                st, sz = orig[pid]['start'], orig[pid]['size']
                if len(blob) != sz:
                    raise SystemExit("원시 길이가 달라졌다: %s pathID %d" % (s['path'], pid))
                data[base + st:base + st + sz] = blob
                objs.append({'path_id': pmap[pid], 'start': base + st, 'size': sz,
                             'type_id': int(o.class_id), 'class_id': int(o.class_id),
                             'destroyed': 0})
                continue
            tree = tree
            if s['dx'] and o.type.name == 'Transform' \
                    and tree['m_Father']['m_PathID'] == 0:
                tree['m_LocalPosition']['x'] += s['dx']
                print("  %s 루트 Transform x %+.1f -> %.1f"
                      % (s['name'], s['dx'], tree['m_LocalPosition']['x']))
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

    manifest = make_manifest(bundle_name,
                             [(s['name'], s['map'][s['mainpid']]) for s in srcs],
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
    # 이름을 갈라낸 의존 자산이 있으면 그 새 이름으로 적는다.
    import json, os.path
    ren = {}
    if os.path.exists('rename_ov.json'):
        ren = json.load(io.open('rename_ov.json', encoding='utf-8'))
    ext_order = [ren.get(os.path.basename(e), e) for e in ext_order]
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

    sf2 = SerializedFile(EndianBinaryReader(io.open(out_path, 'rb').read()), None)
    ab = [o for p, o in sf2.objects.items() if o.type.name == 'AssetBundle'][0].read_typetree()
    print("  매니페스트 항목: %s"
          % [(c[0], c[1]['asset']['m_PathID']) for c in ab['m_Container']])


if __name__ == '__main__':
    specs = []
    for a in sys.argv[3:]:
        if a.startswith('@'):
            # 한 줄에 스펙 하나. 키에 공백이 있어 셸 인자로는 넘기기 어렵다.
            for ln in io.open(a[1:], encoding='utf-8').read().split('\\n'):
                if ln.strip():
                    specs.append(ln.strip())
        else:
            specs.append(a)
    merge(sys.argv[1], sys.argv[2], specs)
