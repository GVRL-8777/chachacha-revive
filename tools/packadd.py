# -*- coding: utf-8 -*-
"""이미 구운 번들에 자산 파일 하나를 **덧붙인다.**

왜 필요한가. `mkpack.py` 는 `packspec.txt` 를 처음부터 다시 합쳐 번들을
굽는다. 그런데 그 목록이 가리키는 공여판 트리(맵 29개 · 보이스 220개)는
저장소에 없다 — 남의 APK 를 통째로 담아 둘 수 없어 걷어냈기 때문이다.
그래서 지금은 `bundles/pack.unity3d` 자신이 그 자산들의 **유일한 사본**이고,
다시 구우려 들면 249개가 사라진다.

이 도구는 다시 굽지 않는다. 이미 있는 `pack.dat`(번들 알맹이) 위에
자산 파일 하나를 얹고 매니페스트에 이름만 더한다.

  · 기존 오브젝트의 자리(offset/size)는 **하나도 건드리지 않는다.**
  · 새 오브젝트는 뒤에 붙이고, pathID 는 안 쓰는 번호부터 준다.
  · 외부 파일 목록도 **뒤에만** 더한다. 앞을 건드리면 기존 참조가 어긋난다.
  · 매니페스트(pathID 1)는 길어지므로 파일 맨 뒤에 다시 놓고 표만 고친다.

    python tools/packadd.py <자산파일> <스펙…>

스펙은 `packspec.txt` 와 같은 꼴에서 파일 이름만 뺀 것이다.

    <번들안이름>:<루트pathID>[:keepscript][:also=…][:mbptr=…]
"""
import io
import os
import struct
import sys

CODE = os.path.dirname(os.path.abspath(__file__))
HERE = os.path.dirname(CODE)
sys.path.insert(0, CODE)

DAT = os.path.join(HERE, 'pack.dat')
OUT = os.path.join(HERE, 'bundles', 'pack.unity3d')
CAB = 'CAB-pack.dat'


def _sf(raw):
    from UnityPy.streams import EndianBinaryReader
    from UnityPy.files.SerializedFile import SerializedFile
    return SerializedFile(EndianBinaryReader(raw), None)


def parse_spec(args):
    """스펙 줄들을 (이름, pathID) 목록과 mbptr 목록으로 가른다."""
    names, mbptr, keepscript = [], [], False
    for sp in args:
        parts = sp.split(':')
        names.append((parts[0], int(parts[1])))
        for o in parts[2:]:
            if o == 'keepscript':
                keepscript = True
            elif o.startswith('also='):
                nm, _, pid = o[5:].rpartition('@')
                names.append((nm, int(pid)))
            elif o.startswith('mbptr='):
                pid, _, off = o[6:].rpartition('@')
                mbptr.append((int(pid), int(off)))
    return names, mbptr, keepscript


def add(src, specs, say=print):
    from sfparse import parse
    from sfmerge import walk_pptr

    names, mbptr, keepscript = parse_spec(specs)
    base_meta = parse(DAT)
    base_raw = io.open(DAT, 'rb').read()
    base_ext = [os.path.basename(e) for e in base_meta['externals']]
    base_objs = list(base_meta['objects'])
    doff = base_meta['data_offset']

    add_meta = parse(src)
    add_raw = io.open(src, 'rb').read()
    add_sf = _sf(add_raw)
    add_ext = [os.path.basename(e) for e in add_meta['externals']]

    # 외부 목록은 뒤에만 더한다.
    ext = list(base_ext)
    for e in add_ext:
        if e not in ext:
            ext.append(e)
    ext_map = dict((i + 1, ext.index(e) + 1) for i, e in enumerate(add_ext))

    nxt = max(o['path_id'] for o in base_objs) + 1
    pmap = dict((p, nxt + i) for i, p in enumerate(sorted(add_sf.objects)))
    say('  새 pathID %d..%d (기존 %d개)'
        % (min(pmap.values()), max(pmap.values()), len(base_objs)))

    # --- 데이터 구역: 기존을 그대로 두고 뒤에 붙인다 ---
    data = bytearray(base_raw[doff:])
    while len(data) % 16:
        data.append(0)
    start = len(data)
    blk = max(o['start'] + o['size'] for o in add_meta['objects'])
    data += add_raw[add_meta['data_offset']:add_meta['data_offset'] + blk]

    recs = dict((o['path_id'], o) for o in add_meta['objects'])
    new_objs = []
    ptrs = 0

    def fix(p):
        if p['m_FileID'] == 0:
            if p['m_PathID'] in pmap:
                p['m_PathID'] = pmap[p['m_PathID']]
        else:
            p['m_FileID'] = ext_map[p['m_FileID']]
        return 1

    for pid in sorted(add_sf.objects):
        o = add_sf.objects[pid]
        rec = recs[pid]
        at = start + rec['start']
        if o.type.name == 'MonoBehaviour':
            # 타입트리가 없다. m_GameObject · m_Script · 알려 준 자리만 고친다.
            gf, gp = struct.unpack_from('<ii', data, at)
            if gf == 0 and gp in pmap:
                struct.pack_into('<ii', data, at, 0, pmap[gp])
            sf0, sp0 = struct.unpack_from('<ii', data, at + 12)
            if sf0:
                struct.pack_into('<ii', data, at + 12,
                                 ext_map[sf0] if keepscript else 0,
                                 sp0 if keepscript else 0)
            for mpid, moff in mbptr:
                if mpid != pid:
                    continue
                # 타입트리 있는 오브젝트와 **같은 규칙**으로 옮긴다.
                f2, p2 = struct.unpack_from('<ii', data, at + moff)
                if f2 or p2:
                    q = {'m_FileID': f2, 'm_PathID': p2}
                    fix(q)
                    struct.pack_into('<ii', data, at + moff,
                                     q['m_FileID'], q['m_PathID'])
        else:
            t = o.read_typetree()
            ptrs += walk_pptr(t, fix)
            blob = bytes(o.save_typetree(t))
            if len(blob) != rec['size']:
                raise SystemExit('길이가 달라졌습니다: pathID %d (%d -> %d)'
                                 % (pid, rec['size'], len(blob)))
            data[at:at + len(blob)] = blob
        new_objs.append({'path_id': pmap[pid], 'start': at,
                         'size': rec['size'], 'type_id': int(o.class_id),
                         'class_id': int(o.class_id), 'destroyed': 0})
    say('  PPtr %d개 재배선 · 자산 %d개' % (ptrs, len(new_objs)))

    # --- 매니페스트에 이름만 더한다 ---
    base_sf = _sf(base_raw)
    man = [o for o in base_sf.objects.values()
           if o.type.name == 'AssetBundle'][0]
    tree = man.read_typetree()
    have = set(k for k, _v in tree['m_Container'])
    added = 0
    for nm, pid in names:
        if nm in have:
            continue
        tree['m_PreloadTable'].append({'m_FileID': 0, 'm_PathID': pmap[pid]})
        tree['m_Container'].append((nm, {
            'preloadIndex': len(tree['m_PreloadTable']) - 1, 'preloadSize': 1,
            'asset': {'m_FileID': 0, 'm_PathID': pmap[pid]}}))
        added += 1
    say('  매니페스트 %d -> %d개' % (len(have), len(tree['m_Container'])))
    blob = bytes(man.save_typetree(tree))

    while len(data) % 8:
        data.append(0)
    man_at = len(data)
    data += blob

    objs = []
    for o in base_objs:
        o = dict(o)
        if o['path_id'] == man.path_id:
            o['start'], o['size'] = man_at, len(blob)
        objs.append(o)
    objs += new_objs

    meta = base_meta['unity'].encode('utf-8') + b'\x00'
    meta += struct.pack('<i', base_meta['platform'])
    meta += struct.pack('<i', 0)
    meta += struct.pack('<i', base_meta['big_id'])
    meta += struct.pack('<i', len(objs))
    for o in objs:
        meta += struct.pack('<iIIiHh', o['path_id'], o['start'], o['size'],
                            o['type_id'], o['class_id'], o['destroyed'])
    meta += struct.pack('<i', len(ext))
    for nm in ext:
        meta += (b'\x00' + b'\x00' * 16 + struct.pack('<i', 0)
                 + nm.encode('utf-8') + b'\x00')
    meta += b'\x00'

    # 오브젝트 표가 237칸 늘어 머리가 길어진다. 그래서 데이터 구역이
    # 뒤로 밀리는데, 표의 `start` 는 **데이터 구역 안에서 센 자리**라
    # 값은 하나도 안 바뀐다. 머리에 적는 시작 자리만 새로 쓰면 된다.
    new_doff = max(doff, (20 + len(meta) + 64 + 15) & ~15)
    if new_doff != doff:
        say('  머리가 길어져 데이터 시작 자리를 %d -> %d 로 옮깁니다'
            % (doff, new_doff))
    head = struct.pack('>IIII', len(meta), new_doff + len(data), 9, new_doff)
    head += bytes([1 if base_meta['endian'] == '>' else 0, 0, 0, 0])
    out = bytearray(head + meta)
    while len(out) < new_doff:
        out += b'\x00'
    out += data
    io.open(DAT, 'wb').write(bytes(out))
    say('  pack.dat %d -> %d 바이트' % (len(base_raw), len(out)))
    return added


def replace(dat, blobs, say=print):
    """번들 알맹이 안의 오브젝트 몇 개를 **새 바이트로 갈아 끼운다.**

    길이가 달라지므로 데이터 구역을 다시 짠다. 오브젝트 표의 순서와 pathID
    는 그대로 두고 자리(start/size)만 새로 적는다. 머리 길이가 안 변하므로
    데이터 시작 자리도 그대로다.

        blobs: {pathID: 새 바이트}
    """
    from sfparse import parse

    meta = parse(dat)
    raw = io.open(dat, 'rb').read()
    doff = meta['data_offset']
    data = bytearray()
    objs = []
    for o in sorted(meta['objects'], key=lambda x: x['start']):
        while len(data) % 8:
            data.append(0)
        blob = blobs.get(o['path_id'])
        if blob is None:
            blob = raw[doff + o['start']:doff + o['start'] + o['size']]
        objs.append(dict(o, start=len(data), size=len(blob)))
        data += blob
    objs.sort(key=lambda x: [q['path_id'] for q in meta['objects']]
              .index(x['path_id']))

    m = meta['unity'].encode('utf-8') + b'\x00'
    m += struct.pack('<i', meta['platform'])
    m += struct.pack('<i', 0)
    m += struct.pack('<i', meta['big_id'])
    m += struct.pack('<i', len(objs))
    for o in objs:
        m += struct.pack('<iIIiHh', o['path_id'], o['start'], o['size'],
                         o['type_id'], o['class_id'], o['destroyed'])
    ext = [os.path.basename(e) for e in meta['externals']]
    m += struct.pack('<i', len(ext))
    for nm in ext:
        m += (b'\x00' + b'\x00' * 16 + struct.pack('<i', 0)
              + nm.encode('utf-8') + b'\x00')
    m += b'\x00'

    ndoff = max(doff, (20 + len(m) + 64 + 15) & ~15)
    head = struct.pack('>IIII', len(m), ndoff + len(data), 9, ndoff)
    head += bytes([1 if meta['endian'] == '>' else 0, 0, 0, 0])
    out = bytearray(head + m)
    while len(out) < ndoff:
        out += b'\x00'
    out += data
    io.open(dat, 'wb').write(bytes(out))
    say('  %s 오브젝트 %d개 중 %d개 교체 · %d → %d바이트'
        % (os.path.basename(dat), len(objs), len(blobs), len(raw), len(out)))
    return len(out)


def wrap(say=print, out=None, dat=None):
    import subprocess
    out, dat = out or OUT, dat or DAT
    r = subprocess.run([sys.executable, os.path.join(CODE, 'mkbundle.py'),
                        out, dat, CAB], cwd=HERE, capture_output=True,
                       text=True, encoding='utf-8', errors='replace',
                       env=dict(os.environ, PYTHONIOENCODING='utf-8'))
    if r.returncode != 0:
        print((r.stdout or '') + (r.stderr or ''))
        raise SystemExit('번들 씌우기에 실패했습니다')
    say('  %s %.1f MB' % (os.path.basename(out),
                          os.path.getsize(out) / 1048576.0))
    return os.path.getsize(out)


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    add(sys.argv[1], sys.argv[2:])
    wrap()
    return 0


if __name__ == '__main__':
    sys.exit(main())
