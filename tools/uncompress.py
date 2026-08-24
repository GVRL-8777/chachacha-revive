# -*- coding: utf-8 -*-
"""**DXT 텍스처**를 다른 형식으로 다시 굽는다.

주의 — **이 도구로 고칠 문제는 (지금까지 아는 한) 없다.** Mali 기기에서 3D 가
검게 나오던 문제는 텍스처 형식과 무관했고, `tools/dexegl.py` 의 깊이 버퍼
수정으로 해결됐다. docs/GPU.md 를 보라.

그래도 남겨 둔다. 형식을 바꿔 가며 실기에서 확인해야 할 일이 또 생길 수 있고,
길이가 달라지는 텍스처를 안전하게 갈아 끼우는 방법이 여기 들어 있다.

    python tools/uncompress.py --survey        형식별로 몇 장인지
    python tools/uncompress.py --small --all   16비트로 (RGB565 · RGBA4444)
    python tools/uncompress.py --all           32비트로 (RGB24 · 트리 +41MB)
    python tools/uncompress.py --etc --all     ETC1 로 (크기 그대로)
    python tools/uncompress.py --like aveo     이름으로 골라서
    python tools/uncompress.py --restore       backup/dxt 에서 되돌리기

실기 확인 결과: A35(Mali)에서 DXT1 · ETC1 · RGB565 · RGB24 · 밉맵 포함 —
**전부 똑같이 나왔다.** 형식은 갈림길이 아니었다.

레코드 길이가 달라지므로 sfedit 로 파일을 다시 짠다. 원본은 backup/dxt 에 남긴다.
16비트 포장은 게임이 원래 쓰던 RGBA4444 텍스처와 바이트가 그대로 맞는 것을
확인했다.
"""
import argparse
import collections
import io
import os
import shutil
import sys

CODE = os.path.dirname(os.path.abspath(__file__))
HERE = os.path.dirname(CODE)
sys.path.insert(0, CODE)

DATA = os.path.join('assets', 'bin', 'Data')
BAK = os.path.join(HERE, 'backup', 'dxt')

# 압축이라 이 기기에서 안 올라가는 것들
# 이 도구가 다루는 압축 형식들. ETC1(34) 은 건드리지 않는다.
PACKED = {10: 'DXT1', 12: 'DXT5',
          30: 'PVRTC_RGB2', 31: 'PVRTC_RGBA2',
          32: 'PVRTC_RGB4', 33: 'PVRTC_RGBA4'}
NAMES_EXTRA = {34: 'ETC_RGB4'}
NAMES = {1: 'Alpha8', 3: 'RGB24', 4: 'RGBA32', 5: 'ARGB32', 7: 'RGB565',
         13: 'RGBA4444'}
NAMES.update(PACKED)
NAMES.update(NAMES_EXTRA)


def _files(tree):
    root = os.path.join(tree, DATA)
    for name in sorted(os.listdir(root)):
        if '.' in name:            # 곁다리 파일은 건드리지 않는다
            continue
        p = os.path.join(root, name)
        if os.path.isfile(p) and os.path.getsize(p) >= 512:
            yield name, p


def survey(tree):
    import UnityPy
    n = collections.Counter()
    px = collections.Counter()
    for _name, p in _files(tree):
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
            f = int(t.get('m_TextureFormat', -1))
            n[f] += 1
            px[f] += int(t.get('m_Width', 0)) * int(t.get('m_Height', 0))
    print('  %-12s %6s %10s %12s' % ('형식', '장수', '픽셀(백만)', '압축없이 하면'))
    for f, c in n.most_common():
        mb = px[f] * (4 if f in (12, 4, 5) else 3) / 2 ** 20
        mark = '   <- 이 도구가 바꿀 수 있음' if f in PACKED else ''
        print('  %-12s %6d %10.1f %10.1fMB%s'
              % (NAMES.get(f, str(f)), c, px[f] / 1e6, mb, mark))
    return 0


def convert(tree, like=None, everything=False, limit=None, etc=False,
            small=False):
    import UnityPy
    from PIL import Image
    from UnityPy.enums import TextureFormat
    from UnityPy.export import Texture2DConverter as TC
    from sfedit import replace_object

    os.makedirs(BAK, exist_ok=True)
    done = 0
    grew = 0
    for name, p in _files(tree):
        try:
            env = UnityPy.load(p)
        except Exception:
            continue
        todo = []
        for o in env.objects:
            if o.type.name != 'Texture2D':
                continue
            try:
                t = o.read_typetree()
            except Exception:
                continue
            if int(t.get('m_TextureFormat', -1)) not in PACKED:
                continue
            nm = t.get('m_Name') or ''
            if like and like.lower() not in nm.lower():
                continue
            if not (like or everything):
                continue
            todo.append((o, t, nm))
        for o, t, nm in todo:
            img = o.read().image
            has_a = img.mode in ('RGBA', 'LA') and img.getextrema()[3][0] < 255
            if small:
                import numpy as np
                flat = img.transpose(Image.FLIP_TOP_BOTTOM)
                if has_a:
                    a = np.asarray(flat.convert('RGBA'), dtype=np.uint16)
                    v = (((a[..., 0] >> 4) << 12) | ((a[..., 1] >> 4) << 8)
                         | ((a[..., 2] >> 4) << 4) | (a[..., 3] >> 4))
                    fmt = TextureFormat.RGBA4444
                else:
                    a = np.asarray(flat.convert('RGB'), dtype=np.uint16)
                    v = (((a[..., 0] >> 3) << 11) | ((a[..., 1] >> 2) << 5)
                         | (a[..., 2] >> 3))
                    fmt = TextureFormat.RGB565
                blob = v.astype('<u2').tobytes()
            elif etc and not has_a:
                # ETC1 은 알파가 없다. 알파가 없는 것만 여기로 보낸다.
                fmt = TextureFormat.ETC_RGB4
                blob, _got = TC.image_to_texture2d(img.convert('RGBA'), fmt)
            else:
                img = img.convert('RGBA' if has_a else 'RGB')
                # 유니티는 아래에서 위로 담는다
                flat = img.transpose(Image.FLIP_TOP_BOTTOM)
                blob = flat.tobytes()
                fmt = TextureFormat.RGBA32 if has_a else TextureFormat.RGB24
            bak = os.path.join(BAK, name)
            if not os.path.exists(bak):
                shutil.copy2(p, bak)
            t.update({'m_TextureFormat': int(fmt),
                      'm_CompleteImageSize': len(blob),
                      'm_MipMap': False,
                      'image data': blob})
            old, new, fold, fnew = replace_object(p, o.path_id,
                                                  bytes(o.save_typetree(t)))
            grew += fnew - fold
            done += 1
            if done <= 12 or done % 50 == 0:
                print('  %-4d %-18s %-8s %sx%s  +%.0fKB'
                      % (done, nm[:18], fmt.name,
                         t.get('m_Width'), t.get('m_Height'),
                         (fnew - fold) / 1024.0))
            if limit and done >= limit:
                print('바꾼 텍스처 %d장 · 트리 %.1fMB 늘어남' % (done, grew / 2 ** 20))
                return 0
    print('바꾼 텍스처 %d장 · 트리 %.1fMB 늘어남' % (done, grew / 2 ** 20))
    return 0


def restore(tree):
    root = os.path.join(tree, DATA)
    if not os.path.isdir(BAK):
        raise SystemExit('남겨 둔 원본이 없습니다: %s' % BAK)
    n = 0
    for name in sorted(os.listdir(BAK)):
        shutil.copy2(os.path.join(BAK, name), os.path.join(root, name))
        n += 1
    print('되돌린 파일 %d개' % n)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tree', default=os.path.join(HERE, 'x77'))
    ap.add_argument('--survey', action='store_true')
    ap.add_argument('--like')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--limit', type=int)
    ap.add_argument('--small', action='store_true',
                    help='16비트로 (RGB565 · RGBA4444)')
    ap.add_argument('--etc', action='store_true',
                    help='ETC1 로 굽는다 (용량이 안 늘어난다)')
    ap.add_argument('--restore', action='store_true')
    a = ap.parse_args()
    if a.survey:
        return survey(a.tree)
    if a.restore:
        return restore(a.tree)
    if not (a.like or a.all):
        ap.error('--like 또는 --all 을 주세요')
    return convert(a.tree, a.like, a.all, a.limit, a.etc, a.small)


if __name__ == '__main__':
    sys.exit(main())
