# -*- coding: utf-8 -*-
"""빌드의 언어를 텍스트 자산으로 판별합니다 (CarName_AVEO 줄을 봅니다)."""
import io, os, re, struct, sys
sys.path.insert(0,'.')
from sfparse import parse

def textassets(tree):
    d = os.path.join(tree, 'assets/bin/Data')
    out = []
    for fn in sorted(os.listdir(d)):
        if '.split' in fn: continue
        p = os.path.join(d, fn)
        try: meta = parse(p)
        except Exception: continue
        raw = None
        for o in meta['objects']:
            if o['class_id'] != 49 or o['size'] < 64: continue   # TextAsset
            if raw is None: raw = io.open(p,'rb').read()
            st = meta['data_offset'] + o['start']
            b = raw[st:st+o['size']]
            try:
                n = struct.unpack_from('<i', b, 0)[0]
                off = 4+n; off += (-off)%4
                tlen = struct.unpack_from('<i', b, off)[0]
                t = b[off+4:off+4+tlen].decode('utf-8', 'replace')
            except Exception:
                continue
            if 'CarName_AVEO' in t:
                out.append((fn, t))
    return out

for tree in sys.argv[1:]:
    print('===', tree)
    hits = textassets(tree)
    if not hits:
        print('   이름표 텍스트를 못 찾음'); continue
    fn, t = hits[0]
    for key in ('CarName_AVEO', 'CarName_Hummer', 'CarName_Mustang'):
        for ln in t.splitlines():
            if ln.startswith(key):
                print('  ', ln.strip()[:80]); break
    ko = len(re.findall(r'[가-힣]', t)); zh = len(re.findall(r'[一-鿿]', t))
    ja = len(re.findall(r'[぀-ヿ]', t))
    print('   한글 %d · 한자 %d · 가나 %d · 전체 %d자' % (ko, zh, ja, len(t)))
