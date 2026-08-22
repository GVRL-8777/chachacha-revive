# -*- coding: utf-8 -*-
"""이식 자산의 바깥 참조가 실제로 무엇에 닿는지 전수 확인한다.

공여판에서 가리키던 것(형식·이름)과, 최종 배치(중국판 + ov)에서 닿는 것을
비교해 어긋난 참조를 모두 찾아낸다.
"""
import io, json, os, sys
from collections import defaultdict
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile
from sfparse import parse

D  = 'survey/gogogoracer-1-4-3/assets/bin/Data'
CN = 'survey/5577.com.cjenm.chachachacn/assets/bin/Data'
OV = 'ov'
REN = json.load(io.open('rename_ov.json', encoding='utf-8')) if os.path.exists('rename_ov.json') else {}

roots = [l.strip() for l in io.open('maproots.txt', encoding='utf-8').read().splitlines() if l.strip()]
seen, todo = set(), list(roots)
while todo:
    f = todo.pop()
    if f in seen: continue
    seen.add(f)
    p = os.path.join(D, f)
    if os.path.exists(p):
        todo += [e for e in parse(p)['externals'] if len(e) == 32]

_cache = {}
def ident(d, name, pid):
    """(형식, 이름) 또는 None"""
    key = (d, name)
    if key not in _cache:
        p = os.path.join(d, name)
        if not os.path.exists(p):
            _cache[key] = None
        else:
            try:
                _cache[key] = SerializedFile(EndianBinaryReader(io.open(p, 'rb').read()), None)
            except Exception:
                _cache[key] = None
    sf = _cache[key]
    if sf is None:
        return None
    o = sf.objects.get(pid)
    if o is None:
        return ('<없음>', '')
    nm = ''
    try:
        nm = getattr(o.read(), 'm_Name', '') or ''
    except Exception:
        pass
    return (o.type.name, nm)

def final_dir(name):
    """최종 배치에서 그 이름의 파일이 어디서 오는지."""
    if os.path.exists(os.path.join(OV, name)):
        return OV
    return CN

def walk(node, fn):
    if isinstance(node, dict):
        if set(node.keys()) == {'m_FileID', 'm_PathID'}:
            fn(node); return
        for v in node.values(): walk(v, fn)
    elif isinstance(node, (list, tuple)):
        for v in node: walk(v, fn)

bad = defaultdict(list)
nref = 0
for f in sorted(seen):
    # 이미 손본 것이 있으면 그쪽을 본다(최종 배치 기준으로 확인해야 한다)
    p = os.path.join(OV, REN.get(f, f))
    if not os.path.exists(p):
        p = os.path.join(D, f)
    if not os.path.exists(p): continue
    ext = parse(p)['externals']
    sf = SerializedFile(EndianBinaryReader(io.open(p, 'rb').read()), None)
    for pid, o in sf.objects.items():
        try: tree = o.read_typetree()
        except Exception: continue
        def hit(pp, ext=ext, f=f, pid=pid, o=o):
            global nref
            fid, tp = pp['m_FileID'], pp['m_PathID']
            if not fid or not tp or fid > len(ext): return
            nref += 1
            src = os.path.basename(ext[fid - 1])
            want = ident(D, src, tp)
            if want is None: return                    # 공여판에도 없는 대상
            dst = REN.get(src, src)
            got = ident(final_dir(dst), dst, tp)
            if got is None:
                bad[(src, tp)].append((f, pid, o.type.name, want, '<파일없음>'))
            elif got != want:
                bad[(src, tp)].append((f, pid, o.type.name, want, got))
        walk(tree, hit)

print("이식 닫힘 %d개 파일 / 바깥 참조 %d개 / 어긋난 참조 %d종" % (len(seen), nref, len(bad)))
for (src, tp), us in sorted(bad.items()):
    print("  %s:%d  공여판=%s -> 최종=%s   (참조자 %d)"
          % (src[:16], tp, us[0][3], us[0][4], len(us)))
    for u in us[:3]:
        print("      <- %s:%d %s" % (u[0][:12], u[1], u[2]))
