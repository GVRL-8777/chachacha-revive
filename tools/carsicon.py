# -*- coding: utf-8 -*-
"""아크엔젤 · W3 · 블리츠의 **아이콘**을 5.1.0 아틀라스에서 옮겨 온다.

`addcars5.py` 가 차 여덟 대를 넣었지만 아이콘은 셋이 빈다. 중국판 7.7 의
`Atlas_SpecialCarIcon` 에는 이 셋이 아예 없기 때문이다(자원째 빠져 있었다).
5.1.0 판에는 여섯 칸(S · R 두 급씩)이 그대로 있다.

## 왜 통째로 못 바꾸나

두 아틀라스는 **판 짜임이 다르다.** 겹치는 아이콘 42개 중 좌표가 같은 것은
다섯뿐이다. 5.1.0 판을 통째로 쓰면 나머지 37개의 좌표를 다 새로 적어야 하고,
우리가 넣어 둔 트로이 아이콘도 갈 곳을 잃는다. 그래서 `troyicon.py` 와 같은
길을 간다 — **그림 조각만 오려 빈 자리에 붙이고** 스프라이트 표에 여섯 줄을
더한다.

## 어떻게 붙이나

DXT5 는 4x4 칸끼리 서로를 모른다. 그래서 우리 그림이 덮는 칸만 따로 눌러
원본 바이트 사이에 끼운다. 나머지 42개 아이콘은 바이트 하나 안 바뀐다
(판을 다시 압축하면 이미 든 것들이 손실 압축을 한 번 더 먹는다).

유니티 텍스처는 **아래에서 위로** 담기는데 아틀라스 좌표는 왼쪽 **위**가
원점이다. 줄 번호를 뒤집어야 그림이 제자리에 떨어진다.

## 차례

`troyicon.py` 와 같은 자리(`backup/atlas`)를 밑바탕으로 쓴다. 이 도구가
**먼저**고, 결과를 `backup/atlas5` 에 남긴다. `troyicon.py` 는 그 자리가
있으면 거기서 시작하므로 두 도구가 서로를 지우지 않는다.

    python tools/carsicon.py --scan     무엇이 빠져 있나
    python tools/carsicon.py            넣는다
    python tools/carsicon.py --restore  backup/atlas 로 되돌린다
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

import uiatlas                                          # noqa: E402

XD = os.path.join(HERE, 'x77', 'assets', 'bin', 'Data')
SRC = os.path.join(HERE, '_scratch', 'v5', 'v510', 'assets', 'bin', 'Data')
BAK = os.path.join(HERE, 'backup', 'atlas')
BAK5 = os.path.join(HERE, 'backup', 'atlas5')

ATLAS = 'e319f1a9aae42d44abe80babf4113fcf'      # UIAtlas(MonoBehaviour) pathID 3
ATLAS_PID = 3
TEXTURE = '75abec148c765894abb1c2e7bd6b6154'    # Texture2D:Atlas_SpecialCarIcon

WANT = ('Archangel_S', 'Archangel_R', 'W3_S', 'W3_R', 'Blitz_S', 'Blitz_R')

# 빈 네모 (224,0)-(512,288) 안에서 고른 자리. (224,0) 은 트로이 몫이라 비운다.
# 4의 배수여야 한다 — DXT 칸 경계다.
SPOT = {'Archangel_S': (224, 56), 'Archangel_R': (224, 112),
        'W3_S': (224, 168), 'W3_R': (304, 0),
        'Blitz_S': (304, 56), 'Blitz_R': (304, 112)}


def _blob(tree):
    from UnityPy.streams import EndianBinaryReader
    from UnityPy.files.SerializedFile import SerializedFile
    p = os.path.join(tree, ATLAS)
    sf = SerializedFile(EndianBinaryReader(io.open(p, 'rb').read()), None)
    return p, bytearray(sf.objects[ATLAS_PID].get_raw_data())


def _record(name, x, y, w, h, size):
    b = struct.pack('<i', len(name)) + name.encode('utf-8')
    b += b'\0' * ((-len(b)) % 4)
    b += struct.pack('<4f', x, y, w, h)          # outer
    b += struct.pack('<4f', x, y, w, h)          # inner
    b += struct.pack('<%di' % ((size - 32) // 4), *([0] * ((size - 32) // 4)))
    return b


def _image(tree):
    import UnityPy
    env = UnityPy.load(os.path.join(tree, TEXTURE))
    o = [q for q in env.objects if q.type.name == 'Texture2D'][0]
    return o, o.read().image


def cuts():
    """{이름: (PIL 조각, 원래 너비, 높이)} — 5.1.0 판에서 오려 낸다."""
    from PIL import Image
    _o, im = _image(SRC)
    _p, d = _blob(SRC)
    t = uiatlas.table(bytes(d))
    out = {}
    for k in WANT:
        _sz, outer, _inner, _pad = t[k]
        x, y, w, h = (int(round(v)) for v in outer)
        crop = im.crop((x, y, x + w, y + h))
        # DXT 칸에 맞춰 4의 배수로 키운다. 늘어난 자리는 투명이라 안 보인다.
        bw, bh = (w + 3) & ~3, (h + 3) & ~3
        box = Image.new('RGBA', (bw, bh), (0, 0, 0, 0))
        box.paste(crop, (0, 0))
        out[k] = (box, w, h)
    return out


def _baseline(say):
    """늘 같은 자리에서 시작한다. 없으면 지금 것을 밑바탕으로 남긴다."""
    os.makedirs(BAK, exist_ok=True)
    fresh = True
    for fn in (ATLAS, TEXTURE):
        b = os.path.join(BAK, fn)
        if os.path.exists(b):
            shutil.copy2(b, os.path.join(XD, fn))
            fresh = False
        else:
            shutil.copy2(os.path.join(XD, fn), b)
    say('아틀라스 원본을 %s' % ('backup/atlas 에 남겼습니다' if fresh
                            else 'backup/atlas 에서 되살렸습니다'))


def scan(say=print):
    if not os.path.isdir(SRC):
        say('5.1.0 트리가 없습니다: %s' % SRC)
        return 1
    _p, d = _blob(XD)
    have = uiatlas.table(bytes(d))
    say('우리 아틀라스 스프라이트 %d개' % len(have))
    for k in WANT:
        say('  %-12s %s' % (k, '있음' if k in have else '**없음**'))
    for k, (im, w, h) in sorted(cuts().items()):
        x, y = SPOT[k]
        say('  %-12s 5.1.0 에서 %dx%d 를 오려 (%d,%d) 에 붙입니다'
            % (k, w, h, x, y))
    import numpy as np
    _o, im = _image(XD)
    a = np.array(im)
    for k in WANT:
        x, y = SPOT[k]
        bw, bh = cuts()[k][0].size
        empty = bool((a[y:y + bh, x:x + bw, 3] == 0).all())
        if not empty:
            say('  **(%d,%d) 자리에 뭔가 있습니다** — %s' % (x, y, k))
    return 0


def install(say=print):
    import UnityPy
    from UnityPy.enums import TextureFormat
    from UnityPy.export import Texture2DConverter as T2C
    from sfparse import parse
    from sfedit import replace_object

    if not os.path.isdir(SRC):
        raise SystemExit('5.1.0 트리가 없습니다: %s' % SRC)
    _baseline(say)
    piece = cuts()

    # --- 텍스처: 덮는 칸만 갈아 끼운다 ---
    tp = os.path.join(XD, TEXTURE)
    env = UnityPy.load(tp)
    o = [q for q in env.objects if q.type.name == 'Texture2D'][0]
    t = dict(o.read_typetree())
    if int(t['m_TextureFormat']) != int(TextureFormat.DXT5):
        raise SystemExit('DXT5 판만 다룹니다 (지금 %s)' % t['m_TextureFormat'])
    data = bytearray(t['image data'])
    per_row = t['m_Width'] // 4
    blocks = 0
    for k in WANT:
        im, _w, _h = piece[k]
        x, y = SPOT[k]
        enc, _fmt = T2C.image_to_texture2d(im, TextureFormat.DXT5)
        bw, bh = im.width // 4, im.height // 4
        top = (t['m_Height'] - y - im.height) // 4      # 아래에서 위로 담긴다
        for r in range(bh):
            dst = ((top + r) * per_row + x // 4) * 16
            data[dst:dst + bw * 16] = enc[r * bw * 16:(r + 1) * bw * 16]
        blocks += bw * bh
    say('  DXT5 칸 %d개만 갈아 끼웠습니다 (판 전체 %d개)'
        % (blocks, per_row * (t['m_Height'] // 4)))
    t['image data'] = bytes(data)
    new = bytes(o.save_typetree(t))
    meta = parse(tp)
    rec = [q for q in meta['objects'] if q['path_id'] == o.path_id][0]
    if len(new) != rec['size']:
        raise SystemExit('텍스처 길이가 달라졌습니다 (%d -> %d)'
                         % (rec['size'], len(new)))
    raw = bytearray(io.open(tp, 'rb').read())
    st = meta['data_offset'] + rec['start']
    raw[st:st + len(new)] = new
    io.open(tp, 'wb').write(bytes(raw))
    say('텍스처를 제자리에서 고쳤습니다 (%d바이트 그대로)' % len(new))

    # --- 스프라이트 표 ---
    p, d = _blob(XD)
    size = uiatlas.layout(bytes(d))
    if size is None:
        raise SystemExit('아틀라스 레코드 길이를 못 읽었습니다')
    have = set(uiatlas.table(bytes(d)))
    add = [k for k in WANT if k not in have]
    if add:
        extra = b''.join(
            _record(k, SPOT[k][0], SPOT[k][1], piece[k][1], piece[k][2], size)
            for k in add)
        n = struct.unpack_from('<i', d, uiatlas.HDR_COUNT)[0]
        end = len(d) - uiatlas.TAIL      # 배열 뒤 꼬리 16바이트 **앞**에 넣는다
        d = d[:end] + extra + d[end:]
        struct.pack_into('<i', d, uiatlas.HDR_COUNT, n + len(add))
        replace_object(p, ATLAS_PID, bytes(d))
        say('스프라이트 %d개 추가: %s' % (len(add), ' · '.join(add)))
        say('아틀라스 %d -> %d개' % (n, n + len(add)))
    else:
        say('스프라이트가 이미 다 있습니다')

    os.makedirs(BAK5, exist_ok=True)
    for fn in (ATLAS, TEXTURE):
        shutil.copy2(os.path.join(XD, fn), os.path.join(BAK5, fn))
    say('결과를 backup/atlas5 에 남겼습니다 (troyicon 이 여기서 이어 갑니다)')
    return 0


def restore(say=print):
    if not os.path.isdir(BAK):
        raise SystemExit('남겨 둔 원본이 없습니다: %s' % BAK)
    for fn in (ATLAS, TEXTURE):
        shutil.copy2(os.path.join(BAK, fn), os.path.join(XD, fn))
    if os.path.isdir(BAK5):
        shutil.rmtree(BAK5)
    say('아틀라스를 되돌렸습니다')
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scan', action='store_true')
    ap.add_argument('--restore', action='store_true')
    a = ap.parse_args()
    if a.scan:
        return scan()
    if a.restore:
        return restore()
    return install()


if __name__ == '__main__':
    sys.exit(main())
