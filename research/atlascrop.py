# -*- coding: utf-8 -*-
"""아틀라스에서 조각을 하나하나 PNG 로 잘라 낸다.

`atlasdump.py` 가 좌표를 알려 준다면 이쪽은 실제 그림을 꺼낸다.
남의 판에서 UI 조각을 골라 오려면 눈으로 봐야 하기 때문이다.

    python research/atlascrop.py <APK 또는 폴더> <내보낼 폴더> [이름조각 ...]

이름조각을 주면 그 이름이 든 것만 뽑는다. 안 주면 전부 뽑는다.
아틀라스와 그림을 짝지을 때는 **좌표가 그림 안에 들어맞는지**로 고른다.
"""
from _here import ROOT  # noqa: F401

import io
import os
import sys
import zipfile

import UnityPy
import uiatlas


def blobs(path):
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
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    src, outdir = sys.argv[1], sys.argv[2]
    want = [w.lower() for w in sys.argv[3:]]
    os.makedirs(outdir, exist_ok=True)

    # 1) 그림을 모두 모은다 (이름 -> PIL 이미지)
    pics = {}
    atlases = []
    for where, raw in blobs(src):
        try:
            env = UnityPy.load(io.BytesIO(raw))
        except Exception:
            continue
        for o in env.objects:
            if o.type.name == 'Texture2D':
                try:
                    d = o.read()
                    im = d.image
                    if im:
                        pics.setdefault((getattr(d, 'm_Name', '?'), im.size), im)
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
                if len(recs) >= 3:
                    atlases.append((where, o.path_id, size, blob, recs))

    print('그림 %d장 · 아틀라스 %d개' % (len(pics), len(atlases)))

    made = 0
    for where, path_id, size, blob, recs in atlases:
        # 이 아틀라스의 조각들이 다 들어맞는 그림을 고른다
        need_w = max(int(uiatlas.payload(blob, p, size)[0][0]
                         + uiatlas.payload(blob, p, size)[0][2]) for _n, _o, p in recs)
        need_h = max(int(uiatlas.payload(blob, p, size)[0][1]
                         + uiatlas.payload(blob, p, size)[0][3]) for _n, _o, p in recs)
        best = None
        for (nm, (w, h)), im in pics.items():
            if w >= need_w and h >= need_h:
                if best is None or (w * h) < (best[1].size[0] * best[1].size[1]):
                    best = (nm, im)
        if best is None:
            print('  %s pathID=%s — 맞는 그림을 못 찾음 (%dx%d 필요)'
                  % (where[:20], path_id, need_w, need_h))
            continue
        texname, im = best
        print('  %s pathID=%s -> 그림 %s %s · 조각 %d개'
              % (where[:20], path_id, texname, im.size, len(recs)))
        for name, _no, p in recs:
            if want and not any(w in name.lower() for w in want):
                continue
            o_, _i, _v = uiatlas.payload(blob, p, size)
            x, y, w, h = (int(round(t)) for t in o_)
            if w <= 0 or h <= 0:
                continue
            box = (x, y, min(x + w, im.width), min(y + h, im.height))
            safe = ''.join(c if c.isalnum() or c in '-_' else '_' for c in name)
            path = os.path.join(outdir, '%s__%s.png' % (texname, safe))
            im.crop(box).save(path)
            made += 1

    print('잘라 낸 조각 %d장 -> %s' % (made, outdir))


if __name__ == '__main__':
    main()
