# -*- coding: utf-8 -*-
"""텍스처의 샘플러 설정(필터 · 랩 · 이방성)을 고친다.

왜 필요한가. 차 텍스처는 전부 이렇게 구워져 있다.

    필터=Point  랩=Repeat  밉맵=False  aniso=0

`aniso=0` 은 유니티에서도 OpenGL 에서도 정상 값이 아니다(1 이상이어야 한다).
잘 나오는 UI 텍스처는 전부 `Bilinear/Trilinear + Clamp + aniso 1~4` 다.
Adreno 드라이버는 이런 값을 눈감아 주지만 Mali 는 안 봐 주는 것으로 보인다.

    python tools/texsettings.py --like aveo --filter 1 --wrap 1 --aniso 1
    python tools/texsettings.py --survey              지금 어떤 값인지 센다

레코드 길이가 안 변하므로 그 자리만 덮어쓴다.
"""
import argparse
import collections
import io
import os
import sys

CODE = os.path.dirname(os.path.abspath(__file__))
HERE = os.path.dirname(CODE)
sys.path.insert(0, CODE)

DATA = os.path.join('assets', 'bin', 'Data')
FM = {0: 'Point', 1: 'Bilinear', 2: 'Trilinear'}
WM = {0: 'Repeat', 1: 'Clamp'}


def _files(tree):
    root = os.path.join(tree, DATA)
    for name in sorted(os.listdir(root)):
        p = os.path.join(root, name)
        if os.path.isfile(p) and os.path.getsize(p) >= 512:
            yield name, p


def survey(tree, like=None):
    import UnityPy
    seen = collections.Counter()
    for _n, p in _files(tree):
        try:
            env = UnityPy.load(p)
        except Exception:
            continue
        for o in env.objects:
            if o.type.name != 'Texture2D':
                continue
            try:
                t = o.read_typetree()
            except Exception:
                continue
            nm = t.get('m_Name') or ''
            if like and like.lower() not in nm.lower():
                continue
            ts = t.get('m_TextureSettings') or {}
            seen[(ts.get('m_FilterMode'), ts.get('m_WrapMode'),
                  bool(t.get('m_MipMap')), ts.get('m_Aniso'))] += 1
    print('  %-10s %-8s %-7s %-6s %s' % ('필터', '랩', '밉맵', 'aniso', '장수'))
    for k, c in seen.most_common():
        f, w, m, a = k
        print('  %-10s %-8s %-7s %-6s %d' % (FM.get(f, f), WM.get(w, w), m, a, c))
    return 0


def fix(tree, like, filt, wrap, aniso, dry=False):
    import UnityPy
    from sfparse import parse
    done = skipped = 0
    for name, p in _files(tree):
        try:
            env = UnityPy.load(p)
        except Exception:
            continue
        edits = []
        for o in env.objects:
            if o.type.name != 'Texture2D':
                continue
            try:
                t = o.read_typetree()
            except Exception:
                continue
            nm = t.get('m_Name') or ''
            if like and like.lower() not in nm.lower():
                continue
            ts = dict(t.get('m_TextureSettings') or {})
            old = (ts.get('m_FilterMode'), ts.get('m_WrapMode'), ts.get('m_Aniso'))
            if filt is not None:
                ts['m_FilterMode'] = filt
            if wrap is not None:
                ts['m_WrapMode'] = wrap
            if aniso is not None:
                ts['m_Aniso'] = aniso
            new = (ts.get('m_FilterMode'), ts.get('m_WrapMode'), ts.get('m_Aniso'))
            if new == old:
                continue
            t['m_TextureSettings'] = ts
            edits.append((o, nm, old, new, t))
        if not edits:
            continue
        meta = parse(p)
        raw = bytearray(io.open(p, 'rb').read())
        touched = False
        for o, nm, old, new, t in edits:
            blob = bytes(o.save_typetree(t))
            rec = [x for x in meta['objects'] if x['path_id'] == o.path_id][0]
            if len(blob) != rec['size']:
                print('  건너뜀 %-18s 길이가 달라짐 (%d -> %d)'
                      % (nm, rec['size'], len(blob)))
                skipped += 1
                continue
            st = meta['data_offset'] + rec['start']
            raw[st:st + len(blob)] = blob
            touched = True
            done += 1
            print('  %-18s %s -> %s   [%s]' % (nm, old, new, name[:14]))
        if touched and not dry:
            io.open(p, 'wb').write(bytes(raw))
    print('고친 텍스처 %d장%s' % (done, ' · 건너뜀 %d장' % skipped if skipped else ''))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tree', default=os.path.join(HERE, 'x77'))
    ap.add_argument('--survey', action='store_true')
    ap.add_argument('--like', default='')
    ap.add_argument('--filter', type=int, default=None,
                    help='0=Point 1=Bilinear 2=Trilinear')
    ap.add_argument('--wrap', type=int, default=None, help='0=Repeat 1=Clamp')
    ap.add_argument('--aniso', type=int, default=None)
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()
    if a.survey:
        return survey(a.tree, a.like)
    if a.filter is None and a.wrap is None and a.aniso is None:
        ap.error('--filter / --wrap / --aniso 중 하나는 주세요')
    return fix(a.tree, a.like, a.filter, a.wrap, a.aniso, a.dry)


if __name__ == '__main__':
    sys.exit(main())
