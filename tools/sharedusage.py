# -*- coding: utf-8 -*-
"""이식 대상이 공여판 sharedassets 의 무엇을 실제로 쓰는지 센다."""
import io, os, sys
from collections import defaultdict
import UnityPy
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile
from sfparse import parse

D = 'survey/gogogoracer-1-4-3/assets/bin/Data'

roots = [l.strip() for l in io.open('maproots.txt', encoding='utf-8').read().splitlines() if l.strip()]

# 의존 닫힘 (GUID 파일만)
seen, todo = set(), list(roots)
while todo:
    f = todo.pop()
    if f in seen:
        continue
    seen.add(f)
    p = os.path.join(D, f)
    if not os.path.exists(p):
        continue
    todo += [e for e in parse(p)['externals'] if len(e) == 32]

def walk(node, fn):
    if isinstance(node, dict):
        if set(node.keys()) == {'m_FileID', 'm_PathID'}:
            fn(node); return
        for v in node.values():
            walk(v, fn)
    elif isinstance(node, (list, tuple)):
        for v in node:
            walk(v, fn)

want = defaultdict(set)          # 대상파일 -> {pathID}
for f in sorted(seen):
    p = os.path.join(D, f)
    if not os.path.exists(p):
        continue
    meta = parse(p)
    ext = meta['externals']
    sf = SerializedFile(EndianBinaryReader(io.open(p, 'rb').read()), None)
    for pid, o in sf.objects.items():
        try:
            tree = o.read_typetree()
        except Exception:
            continue
        def hit(pp, ext=ext):
            fid = pp['m_FileID']
            if fid and pp['m_PathID'] and fid <= len(ext):
                want[os.path.basename(ext[fid - 1])].add(pp['m_PathID'])
        walk(tree, hit)

print("이식 닫힘: %d개 파일" % len(seen))
for tgt in sorted(want):
    n = len(want[tgt])
    if not tgt.startswith('sharedassets'):
        continue
    print("  %-24s 직접 참조하는 오브젝트 %d개" % (tgt, n))
    src = os.path.join(D, tgt)
    if not os.path.exists(src):
        print("       (공여판에 파일 없음)")
        continue
    meta = parse(src)
    tot = sum(o['size'] for o in meta['objects'])
    sel = sum(o['size'] for o in meta['objects'] if o['path_id'] in want[tgt])
    print("       파일 전체 오브젝트 %d개 %.1fMB / 그중 %d개 %.2fMB"
          % (len(meta['objects']), tot / 1048576.0, n, sel / 1048576.0))
