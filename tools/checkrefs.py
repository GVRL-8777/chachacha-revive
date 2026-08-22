# -*- coding: utf-8 -*-
"""번들 안 맵 조각들의 **외부 참조가 실제로 해석되는지** 검사한다.

증상: 주행 중 한 테마 구간이 통째로 하얗게 비어 보인다.
가설: `deps.py` 가 "중국판에 같은 이름 파일이 있으면 건너뛴다" 규칙을 쓰는데,
같은 이름(자산 GUID)이라도 판본이 다르면 **내부 pathID 가 다를 수 있다.**
그러면 텍스처/재질 참조가 빈 곳을 가리켜 흰색으로 그려진다.

번들(UnityRaw, mkbundle.py 가 만든 것)에서 직렬화 파일을 꺼내
모든 PPtr 의 (fileID, pathID) 를 모으고, fileID 가 가리키는 외부 파일에서
그 pathID 가 실제로 존재하는지 확인한다.
"""
import io
import os
import struct
import sys
from collections import defaultdict

from sfparse import parse

CN = 'survey/5577.com.cjenm.chachachacn/assets/bin/Data'
OVERLAY = 'overlay'


def read_bundle(path):
    """UnityRaw 번들에서 (내부이름, 바이트) 목록을 꺼낸다."""
    d = io.open(path, 'rb').read()
    p = d.index(b'UnityRaw\x00') + 9
    p += 4                                   # version
    for _ in range(2):                       # version_player, version_engine
        e = d.index(b'\x00', p)
        p = e + 1
    p += 4 * 3                               # minimumStreamedBytes, headerSize, numLevels
    header_size = struct.unpack_from('>I', d, p - 8)[0]
    p = header_size
    n = struct.unpack_from('>i', d, p)[0]
    p += 4
    out = []
    for _ in range(n):
        e = d.index(b'\x00', p)
        name = d[p:e].decode('utf-8')
        p = e + 1
        off, size = struct.unpack_from('>II', d, p)
        p += 8
        out.append((name, d[header_size + off: header_size + off + size]))
    return out


def path_ids(path):
    try:
        m = parse(path)
    except Exception:
        return None
    return set(o['path_id'] for o in m['objects'])


def main():
    bundle = sys.argv[1] if len(sys.argv) > 1 else 'bundles/pack.unity3d'
    cache = {}

    def ids_of(name):
        if name in cache:
            return cache[name]
        base = os.path.basename(name)
        for d in (OVERLAY, CN):
            p = os.path.join(d, base)
            if os.path.exists(p):
                cache[name] = (path_ids(p), p)
                return cache[name]
        cache[name] = (None, None)
        return cache[name]

    for name, blob in read_bundle(bundle):
        tmp = 'bundle_part.tmp'
        io.open(tmp, 'wb').write(blob)
        meta = parse(tmp)
        ext = meta['externals']
        inside = set(o['path_id'] for o in meta['objects'])
        off = meta['data_offset']
        raw = blob
        bad = defaultdict(set)
        seen = defaultdict(set)
        for ob in meta['objects']:
            d = raw[off + ob['start']: off + ob['start'] + ob['size']]
            for k in range(0, max(0, len(d) - 8), 4):
                fid, pid = struct.unpack_from('<ii', d, k)
                if pid <= 0 or pid > 200000:
                    continue
                if fid == 0:
                    continue
                if fid > len(ext):
                    continue
                seen[fid].add(pid)
        print("=== %s : 오브젝트 %d개, 외부참조 %d개 ===" % (name, len(meta['objects']), len(ext)))
        for fid in sorted(seen):
            nm = ext[fid - 1]
            ids, where = ids_of(nm)
            if ids is None:
                print("   [파일 없음] fileID=%d %s  (참조 %d건)" % (fid, nm, len(seen[fid])))
                continue
            miss = [p for p in seen[fid] if p not in ids]
            tag = 'overlay' if where and where.startswith(OVERLAY) else '중국판'
            if miss:
                print("   [pathID 불일치] fileID=%d %s (%s): 참조 %d건 중 %d건이 없음  예: %s"
                      % (fid, os.path.basename(nm)[:34], tag, len(seen[fid]), len(miss), sorted(miss)[:6]))
        os.remove(tmp)


if __name__ == '__main__':
    main()
