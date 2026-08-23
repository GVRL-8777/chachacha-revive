# -*- coding: utf-8 -*-
"""압축 텍스처를 **압축 없는 형식**으로 바꾼다.

왜 필요한가. 갤럭시 A35(Mali · 안드로이드 16)에서는 이 게임의 3D 가 새까맣게
나온다. 실기로 하나씩 좁힌 결과, 압축 텍스처(DXT1 · DXT5 · ETC1)가 GPU 에
올라가지 않는다. 셰이더도 메시도 UV 도 멀쩡하고 `texture2D` 만 검게 나온다.
같은 텍스처를 RGB24 로 바꿔 구우면 그 자리가 제대로 그려진다.

    python tools/uncompress.py --survey        무엇이 얼마나 압축되어 있나
    python tools/uncompress.py --like aveo     이름으로 골라서
    python tools/uncompress.py --all           전부 (APK 가 커진다)
    python tools/uncompress.py --restore       backup/dxt 에서 되돌리기

알파가 없으면 RGB24, 있으면 RGBA32 로 간다. 레코드가 커지므로 sfedit 로
파일을 다시 짠다. 원본은 backup/dxt 에 남긴다.
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
PACKED = {10: 'DXT1', 12: 'DXT5', 34: 'ETC_RGB4',
          30: 'PVRTC_RGB2', 31: 'PVRTC_RGBA2',
          32: 'PVRTC_RGB4', 33: 'PVRTC_RGBA4'}
NAMES = {1: 'Alpha8', 3: 'RGB24', 4: 'RGBA32', 5: 'ARGB32', 7: 'RGB565',
         13: 'RGBA4444'}
NAMES.update(PACKED)


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
        mark = '   <- 이 기기에서 안 올라감' if f in PACKED else ''
        print('  %-12s %6d %10.1f %10.1fMB%s'
              % (NAMES.get(f, str(f)), c, px[f] / 1e6, mb, mark))
    return 0


def convert(tree, like=None, everything=False, limit=None):
    import UnityPy
    from PIL import Image
    from UnityPy.enums import TextureFormat
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
            img = img.convert('RGBA' if has_a else 'RGB')
            flat = img.transpose(Image.FLIP_TOP_BOTTOM)   # 유니티는 아래에서 위로
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
    ap.add_argument('--restore', action='store_true')
    a = ap.parse_args()
    if a.survey:
        return survey(a.tree)
    if a.restore:
        return restore(a.tree)
    if not (a.like or a.all):
        ap.error('--like 또는 --all 을 주세요')
    return convert(a.tree, a.like, a.all, a.limit)


if __name__ == '__main__':
    sys.exit(main())
