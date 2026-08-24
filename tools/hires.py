# -*- coding: utf-8 -*-
"""주행 화면 UI 를 **2배 해상도**로 올린다. 그림은 한국 초기판 것을 쓴다.

지금 빌드(중국판 7.7)의 주행 HUD 는 `Atlas_InGame` 한 장(512x512)에 조각
81개가 들어 있습니다. 2013년 폰 기준이라 요즘 1080p 화면에서는 눈에 띄게
뭉갭니다. 한국 초기판(`8.apk`)에는 **같은 이름의 조각이 정확히 두 배
크기로** 들어 있습니다 — 그때는 2048x2048 판을 썼습니다.

    우리 CheckPoint   347x18     초기판 694x36
    우리 GaugeBar     209x134    초기판 418x268
    우리 HUDEco0       20x12     초기판  40x23

81개 중 **66개**가 초기판에 있습니다. 나머지 15개(중국판이 나중에 더한
것들)는 우리 것을 2배로 늘려 채웁니다 — 더 선명해지진 않지만 나빠지지도
않고, 판 전체가 한 축척으로 유지됩니다.

## 자리를 다시 짜지 않는다

512 판의 조각 자리를 **그냥 두 배** 한 자리에 놓습니다. 겹치지 않던 것이
두 배가 되어도 겹치지 않으므로 새로 포장할 까닭이 없고, 조각 사이 여백도
같은 비율로 늘어나 번짐이 더 나빠지지 않습니다.

## NGUI 쪽 셈

  · 이 아틀라스를 쓰는 위젯 **113개가 전부 `Simple`** 입니다(실측).
    Simple 은 위젯의 스케일에 UV 를 그대로 입히므로, 조각이 커져도
    화면에서 커지지 않습니다. **더 촘촘해질 뿐입니다.**
  · 그래도 `UIAtlas.mPixelSize` 를 **0.5** 로 둡니다. `MakePixelPerfect` ·
    `SlicedFill` · `TiledFill` · `get_border` 가 이 값을 곱하므로, 나중에
    누가 그 길로 들어와도 크기가 그대로입니다.
  · 이 아틀라스를 쓰는 `UIFont` 는 없습니다(확인). `TxtFont0..9` 같은
    숫자도 글꼴이 아니라 낱장 `UISprite` 입니다.

## `.splitN` 함정

**엔진은 `sharedassets1.assets` 통짜가 아니라 `.split0` `.split1` 조각을
읽습니다.** 통짜만 고치면 아무 일도 안 일어납니다. 그래서 이 도구는 고친
뒤 조각을 **다시 만듭니다**(1MiB 씩). 통짜도 같이 남겨 두 쪽이 어긋나지
않게 합니다.

    python tools/hires.py --scan     무엇을 몇 개나 키울 수 있나
    python tools/hires.py --png      새 판을 PNG 로만 뽑아 본다
    python tools/hires.py            바꾼다
    python tools/hires.py --restore  backup/hires 에서 되돌린다
"""
import argparse
import io
import os
import shutil
import struct
import sys

CODE = os.path.dirname(os.path.abspath(__file__))
HERE = os.path.dirname(CODE)
sys.path.insert(0, CODE)

import uiatlas                                                  # noqa: E402

XD = os.path.join(HERE, 'x77', 'assets', 'bin', 'Data')
KR8 = os.path.join(HERE, '_scratch', 'kr8', 'assets', 'bin', 'Data')
BAK = os.path.join(HERE, 'backup', 'hires')
CHUNK = 1024 * 1024                 # 유니티 안드로이드 조각 크기

# 키울 아틀라스. 파일 -> [(UIAtlas pathID, 텍스처 pathID, 이름), ...]
# 파일마다 조각 다시 만들기는 한 번씩이면 된다.
#
# 안 키우는 것과 그 까닭:
#   Atlas_GameTutorial   8/9 가 있지만 도움말 팝업은 `notutorial` 이 꺼 뒀다
#   Atlas_LobbySkillIcon · Atlas_SpecialCarIcon · Atlas_EventPop
#                        초기판에 같은 이름이 하나도 없다
TARGETS = {
    'sharedassets1.assets': [(102, 11, 'Atlas_InGame'),
                             (100, 14, 'Atlas_Cutin')],
    # 83개 중 30개만 초기판에 있다. 나머지는 우리 것을 늘려 채우므로
    # 지금보다 나빠지진 않지만, 같은 차의 A/B/S 는 또렷하고 R 은 아닌
    # 식으로 **선명도가 섞인다.** 초기판에 R 등급이 아예 없어서다.
    'sharedassets2.assets': [(129, 5, 'Atlas_CarIcon')],
}
SCALE = 2


# ------------------------------------------------------------------ 읽기
def _raw(p, pid):
    from UnityPy.streams import EndianBinaryReader
    from UnityPy.files.SerializedFile import SerializedFile
    sf = SerializedFile(EndianBinaryReader(io.open(p, 'rb').read()), None)
    return bytearray(sf.objects[pid].get_raw_data())


def kr8_sprites(say=lambda *a: None):
    """초기판의 모든 아틀라스 조각. 이름 -> (그림, outer(x,y,w,h), 판이름)"""
    import UnityPy
    from sfparse import parse
    files = {}

    def load(fn):
        if fn not in files:
            q = os.path.join(KR8, fn)
            try:
                files[fn] = (UnityPy.load(q),
                             [os.path.basename(e) for e in parse(q)['externals']])
            except Exception:
                files[fn] = (None, [])
        return files[fn]

    out, sheets = {}, {}
    for fn in sorted(os.listdir(KR8)):
        q = os.path.join(KR8, fn)
        if not os.path.isfile(q) or os.path.getsize(q) < 1024:
            continue
        env, ext = load(fn)
        if env is None:
            continue
        for o in env.objects:
            if o.type.name != 'MonoBehaviour':
                continue
            try:
                b = bytes(o.get_raw_data())
            except Exception:
                continue
            if len(b) < 200:
                continue
            tb = uiatlas.table(b)
            if len(tb) < 2:
                continue
            mf, mp = struct.unpack_from('<ii', b, 24)      # material PPtr
            try:
                menv, mext = (env, ext) if mf == 0 else load(ext[mf - 1])
                mt = [x for x in menv.objects if x.path_id == mp][0].read_typetree()
                tp = mt['m_SavedProperties']['m_TexEnvs'][0][1]['m_Texture']
                tenv, _ = ((menv, None) if tp['m_FileID'] == 0
                           else load(mext[tp['m_FileID'] - 1]))
                to = [x for x in tenv.objects if x.path_id == tp['m_PathID']][0]
                key = to.read_typetree()['m_Name']
                if key not in sheets:
                    sheets[key] = to.read().image.convert('RGBA')
                    say('  초기판 판 %s %s' % (key, sheets[key].size))
            except Exception:
                continue
            for nm, (_off, outer, _inner, _ints) in tb.items():
                out[nm] = (sheets[key], outer, key)
    return out


def base_file(fn):
    """손대기 전 파일. 한 번 바꾼 뒤에도 늘 원본에서 다시 짓는다."""
    b = os.path.join(BAK, fn)
    return b if os.path.exists(b) else os.path.join(XD, fn)


def ours(fn, atlas_pid, tex_pid):
    """우리 아틀라스 blob · 조각표 · 판 그림. 늘 **손대기 전** 것을 읽는다."""
    import UnityPy
    p = base_file(fn)
    blob = _raw(p, atlas_pid)
    env = UnityPy.load(p)
    tex = [o for o in env.objects if o.path_id == tex_pid][0]
    return p, blob, uiatlas.table(bytes(blob)), tex.read().image.convert('RGBA')


# ------------------------------------------------------------------ 그림
def resample(im, tw, th):
    """알파를 곱해 두고 넓이 평균으로 크기를 맞춘다.

    그냥 늘리거나 줄이면 실루엣 바깥의 (0,0,0,0)이 색 계산에 끼어들어
    둘레에 검은 테가 생긴다. 알파를 미리 곱해 두면 그 일이 없다.
    (트로이 아이콘을 만들 때 같은 데 두 번 걸렸다 — `troyicon.py` 참고)"""
    import numpy as np
    from PIL import Image
    if (im.width, im.height) == (tw, th):
        return im
    up = tw >= im.width
    how = Image.LANCZOS if up else Image.BOX
    a = np.array(im).astype(np.float32)
    al = a[..., 3] / 255.0
    ch = [a[..., i] * al for i in range(3)] + [al]
    small = [np.array(Image.fromarray(c, 'F').resize((tw, th), how)) for c in ch]
    sa = small[3]
    rgb = np.stack([np.clip(small[i] / np.maximum(sa, 1e-4), 0, 255)
                    for i in range(3)], axis=2)
    out = np.concatenate([rgb, (sa * 255.0)[..., None]], axis=2)
    return Image.fromarray(np.clip(out, 0, 255).astype('uint8'))


def build_sheet(fn, atlas_pid, tex_pid, kr, say=print):
    """새 판 그림과 '초기판에서 온 조각' 목록을 만든다."""
    from PIL import Image
    _p, _blob, table, sheet = ours(fn, atlas_pid, tex_pid)
    W, H = sheet.width * SCALE, sheet.height * SCALE
    out = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    took, grew = [], []
    for nm, (_off, outer, _inner, _ints) in sorted(table.items()):
        x, y, w, h = (int(round(v)) for v in outer)
        if w <= 0 or h <= 0:
            continue
        tw, th = w * SCALE, h * SCALE
        if nm in kr:
            ksheet, kouter, _where = kr[nm]
            kx, ky, kw, kh = (int(round(v)) for v in kouter)
            piece = ksheet.crop((kx, ky, kx + kw, ky + kh))
            took.append(nm)
        else:
            piece = sheet.crop((x, y, x + w, y + h))
            grew.append(nm)
        out.alpha_composite(resample(piece, tw, th), (x * SCALE, y * SCALE))
    say('  초기판 그림 %d개 · 우리 것 2배로 늘린 것 %d개' % (len(took), len(grew)))
    return out, took, grew


# ------------------------------------------------------------------ 쓰기
def resplit(path, say=print):
    """엔진이 읽는 `.splitN` 조각을 다시 만든다.

    **이게 이 작업의 고비다.** 통짜 파일만 고치면 엔진은 옛 조각을 읽어
    아무 일도 일어나지 않는다. 조각 수가 늘 수 있으므로 남는 옛 조각은
    지운다(안 지우면 뒤에 쓰레기가 붙는다)."""
    d, base = os.path.dirname(path), os.path.basename(path)
    data = io.open(path, 'rb').read()
    old = [f for f in os.listdir(d) if f.startswith(base + '.split')]
    n = 0
    for i in range(0, len(data), CHUNK):
        io.open(os.path.join(d, '%s.split%d' % (base, n)), 'wb').write(
            data[i:i + CHUNK])
        n += 1
    for f in old:
        if int(f.rsplit('split', 1)[1]) >= n:
            os.remove(os.path.join(d, f))
            say('  남는 조각 %s 를 지웠습니다' % f)
    say('  %s %d바이트 → 조각 %d개' % (base, len(data), n))
    return n


def baseline(fn, say):
    """이 파일을 손대기 전 모습으로 돌린다(없으면 지금 것을 남겨 둔다)."""
    if os.path.exists(os.path.join(BAK, fn)):
        for f in os.listdir(XD):
            if f.startswith(fn + '.split'):
                os.remove(os.path.join(XD, f))
        for f in os.listdir(BAK):
            if f == fn or f.startswith(fn + '.split'):
                shutil.copy2(os.path.join(BAK, f), os.path.join(XD, f))
        say('  원본을 backup/hires 에서 되살렸습니다')
    else:
        keep = [fn] + [f for f in os.listdir(XD) if f.startswith(fn + '.split')]
        for f in keep:
            shutil.copy2(os.path.join(XD, f), os.path.join(BAK, f))
        say('  원본을 backup/hires 에 남겼습니다 (%d개)' % len(keep))


def install(say=print):
    import UnityPy
    from UnityPy.enums import TextureFormat
    from UnityPy.export import Texture2DConverter as T2C
    from sfparse import parse
    from sfedit import replace_object

    os.makedirs(BAK, exist_ok=True)
    kr = kr8_sprites(say)
    total = 0
    for fn, targets in sorted(TARGETS.items()):
        say(fn)
        baseline(fn, say)
        p = os.path.join(XD, fn)
        for atlas_pid, tex_pid, label in targets:
            sheet, took, _grew = build_sheet(fn, atlas_pid, tex_pid, kr, say)

            # --- 텍스처 ---
            env = UnityPy.load(p)
            o = [q for q in env.objects if q.path_id == tex_pid][0]
            t = dict(o.read_typetree())
            fmt = TextureFormat(int(t['m_TextureFormat']))
            blob, _f = T2C.image_to_texture2d(sheet, fmt)
            t.update({'m_Width': sheet.width, 'm_Height': sheet.height,
                      'm_CompleteImageSize': len(blob), 'image data': bytes(blob)})
            old_size = [q for q in parse(p)['objects']
                        if q['path_id'] == tex_pid][0]['size']
            new = bytes(o.save_typetree(t))
            replace_object(p, tex_pid, new)
            say('  %s 텍스처 %dx%d %s · 레코드 %d → %d바이트'
                % (label, sheet.width, sheet.height, fmt.name, old_size, len(new)))

            # --- 조각표: 좌표를 두 배로, pixelSize 를 절반으로 ---
            d = _raw(p, atlas_pid)
            size = uiatlas.layout(bytes(d))
            n = 0
            for _nm, _no, off in uiatlas.records(bytes(d), size):
                outer, inner, ints = uiatlas.payload(bytes(d), off, size)
                uiatlas.set_payload(d, off, [v * SCALE for v in outer],
                                    [v * SCALE for v in inner], ints)
                n += 1
            tail = len(d) - uiatlas.TAIL
            px = struct.unpack_from('<f', d, tail + 4)[0]
            struct.pack_into('<f', d, tail + 4, px / float(SCALE))
            replace_object(p, atlas_pid, bytes(d))
            say('  %s 조각 %d개 좌표를 %d배로 · pixelSize %.2f → %.2f'
                % (label, n, SCALE, px, px / float(SCALE)))
            total += len(took)
        resplit(p, say)

    say('')
    say('UI 를 2배 해상도로 올렸습니다 (초기판 그림 %d개).' % total)
    say('이제 APK 를 다시 만드세요.')
    return 0


def restore(say=print):
    if not os.path.isdir(BAK):
        raise SystemExit('남겨 둔 원본이 없습니다: %s' % BAK)
    for fn in TARGETS:
        for f in os.listdir(XD):
            if f.startswith(fn + '.split'):
                os.remove(os.path.join(XD, f))
    k = 0
    for f in sorted(os.listdir(BAK)):
        shutil.copy2(os.path.join(BAK, f), os.path.join(XD, f))
        k += 1
    say('되돌린 파일 %d개' % k)
    return 0


def scan(say=print):
    import collections
    kr = kr8_sprites()
    for fn, targets in sorted(TARGETS.items()):
        for atlas_pid, tex_pid, label in targets:
            _p, _blob, table, sheet = ours(fn, atlas_pid, tex_pid)
            have = [k for k in table if k in kr]
            say('%-20s %dx%d → %dx%d · 조각 %d (초기판 %d · 늘릴 것 %d)'
                % (label, sheet.width, sheet.height, sheet.width * SCALE,
                   sheet.height * SCALE, len(table), len(have),
                   len(table) - len(have)))
            say('   출처: %s'
                % collections.Counter(kr[k][2] for k in have).most_common())
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scan', action='store_true')
    ap.add_argument('--restore', action='store_true')
    ap.add_argument('--png', help='새 판을 PNG 로만 뽑는다')
    a = ap.parse_args()
    if a.scan:
        return scan()
    if a.restore:
        return restore()
    if a.png:
        kr = kr8_sprites()
        for fn, targets in sorted(TARGETS.items()):
            for atlas_pid, tex_pid, label in targets:
                sheet, took, grew = build_sheet(fn, atlas_pid, tex_pid, kr)
                out = '%s.%s.png' % (a.png, label)
                sheet.save(out)
                print('%s (%dx%d) · 초기판 %d · 늘림 %d'
                      % (out, sheet.width, sheet.height, len(took), len(grew)))
        return 0
    return install()


if __name__ == '__main__':
    sys.exit(main())
