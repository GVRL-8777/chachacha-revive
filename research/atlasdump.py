# -*- coding: utf-8 -*-
"""APK 나 작업 트리 안의 NGUI 아틀라스를 통째로 뜯어 표로 적는다.

조각 이름 · 텍스처 안 좌표 · 크기 · 안쪽 여백까지 뽑는다. 어떤 UI 조각이
어디에 들어 있는지 알아야 남의 판에서 골라 올 수 있다.

    python research/atlasdump.py <APK 또는 폴더> [출력.txt]

같은 폴더의 Texture2D 도 함께 적어 둔다 — 어느 아틀라스가 어느 그림을
쓰는지 이름으로 짐작할 수 있게.
"""
from _here import ROOT  # noqa: F401  (tools/ 를 import 경로에 올린다)

import io
import os
import sys
import zipfile

import UnityPy
import uiatlas


def blobs(path):
    """(자리이름, 바이트) 를 하나씩 내놓는다. APK 든 폴더든 받는다."""
    if os.path.isdir(path):
        for name in sorted(os.listdir(path)):
            p = os.path.join(path, name)
            if os.path.isfile(p) and os.path.getsize(p) >= 1024:
                yield name, io.open(p, 'rb').read()
        return
    z = zipfile.ZipFile(path)
    for n in z.namelist():
        if n.startswith('assets/bin/Data/'):
            b = z.read(n)
            if len(b) >= 1024:
                yield n.split('/')[-1], b


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else None
    lines = []

    def say(s=''):
        lines.append(s)
        print(s)

    say('아틀라스 뜯기: %s' % src)
    say('=' * 72)

    atlases = 0
    sprites = 0
    for where, raw in blobs(src):
        try:
            env = UnityPy.load(io.BytesIO(raw))
        except Exception:
            continue

        tex = []
        found = []
        for o in env.objects:
            if o.type.name == 'Texture2D':
                try:
                    d = o.read()
                    tex.append('%s %dx%d' % (getattr(d, 'm_Name', '?'),
                                             getattr(d, 'm_Width', 0),
                                             getattr(d, 'm_Height', 0)))
                except Exception:
                    pass
            elif o.type.name == 'MonoBehaviour':
                try:
                    blob = bytes(o.get_raw_data())
                except Exception:
                    continue
                if len(blob) < 200:
                    continue
                size = uiatlas.layout(blob)
                if size is None:
                    continue
                recs = uiatlas.records(blob, size)
                if len(recs) < 3:
                    continue
                found.append((o.path_id, size, blob, recs))

        for path_id, size, blob, recs in found:
            atlases += 1
            sprites += len(recs)
            say()
            say('■ %s  pathID=%s  조각 %d개  (레코드 %d바이트)'
                % (where[:24], path_id, len(recs), size))
            if tex:
                say('   같은 파일의 그림: %s' % ' · '.join(tex[:4]))
            say('   %-34s %6s %6s %6s %6s   안쪽여백' % ('이름', 'x', 'y', '너비', '높이'))
            say('   ' + '-' * 68)
            for name, _no, p in recs:
                o_, i_, v_ = uiatlas.payload(blob, p, size)
                x, y, w, h = (int(round(t)) for t in o_)
                ix, iy, iw, ih = (int(round(t)) for t in i_)
                pad = ''
                if (ix, iy, iw, ih) != (x, y, w, h):
                    pad = ' inner=%d,%d %dx%d' % (ix, iy, iw, ih)
                # 옛 NGUI(48바이트)는 꼬리 4칸이 **실수 여백**이다.
                if size == 48:
                    import struct as _s
                    v = _s.unpack_from('<4f', blob, p + 32)
                    tail = '여백 %.3f/%.3f/%.3f/%.3f' % v
                else:
                    tail = str(list(v_))
                say('   %-34s %6d %6d %6d %6d  %s%s'
                    % (name[:34], x, y, w, h, tail, pad))

    say()
    say('=' * 72)
    say('아틀라스 %d개 · 조각 %d개' % (atlases, sprites))

    if out:
        io.open(out, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')
        print()
        print('적어 둠: %s' % out)


if __name__ == '__main__':
    main()
