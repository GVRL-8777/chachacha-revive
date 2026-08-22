# -*- coding: utf-8 -*-
import io, os
from collections import defaultdict
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile
from sfparse import parse

D = 'survey/gogogoracer-1-4-3/assets/bin/Data'
CN = 'survey/5577.com.cjenm.chachachacn/assets/bin/Data'
roots = [l.strip() for l in io.open('maproots.txt', encoding='utf-8').read().splitlines() if l.strip()]
seen, todo = set(), list(roots)
while todo:
    f = todo.pop()
    if f in seen: continue
    seen.add(f)
    p = os.path.join(D, f)
    if os.path.exists(p):
        todo += [e for e in parse(p)['externals'] if len(e) == 32]

def walk(node, fn):
    if isinstance(node, dict):
        if set(node.keys()) == {'m_FileID', 'm_PathID'}:
            fn(node); return
        for v in node.values(): walk(v, fn)
    elif isinstance(node, (list, tuple)):
        for v in node: walk(v, fn)

users = defaultdict(list)
for f in sorted(seen):
    p = os.path.join(D, f)
    if not os.path.exists(p): continue
    ext = parse(p)['externals']
    sf = SerializedFile(EndianBinaryReader(io.open(p, 'rb').read()), None)
    for pid, o in sf.objects.items():
        try: tree = o.read_typetree()
        except Exception: continue
        def hit(pp, ext=ext, f=f, pid=pid, o=o):
            fid = pp['m_FileID']
            if fid and pp['m_PathID'] and fid <= len(ext) \
               and os.path.basename(ext[fid-1]).startswith('sharedassets'):
                users[(os.path.basename(ext[fid-1]), pp['m_PathID'])].append((f, pid, o.type.name))
        walk(tree, hit)

for (tgt, pid), us in sorted(users.items()):
    print("대상 %s pathID=%d  (참조자 %d개)" % (tgt, pid, len(us)))
    for u in us[:6]:
        print("    <- %s pathID=%d %s" % (u[0][:12], u[1], u[2]))
    for d, tag in ((D, '공여판'), (CN, '중국판')):
        p = os.path.join(d, tgt)
        if not os.path.exists(p):
            print("    %s: 파일 없음" % tag); continue
        sf = SerializedFile(EndianBinaryReader(io.open(p, 'rb').read()), None)
        o = sf.objects.get(pid)
        if o is None:
            print("    %s: 그 pathID 없음  <<< 어긋남" % tag); continue
        nm = ''
        try: nm = getattr(o.read(), 'm_Name', '') or ''
        except Exception: pass
        print("    %s: %s %r" % (tag, o.type.name, nm))
