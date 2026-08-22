# -*- coding: utf-8 -*-
"""타이틀 로고를 한국판 것으로 바꾼다. (一起车车车 -> 다함께 차차차)

중국판 `Atlas_TItle` 은 1024x2048 DXT5 이고 y 0~965 가 통째로 비어 있다.
한국판(CCC_fK_v7.7.0) 아틀라스에서 Together/Cha01/Cha02/Cha03 네 조각만
잘라 그 빈 자리에 붙이고, 스프라이트 표의 좌표를 새 자리로 고친다.

텍스처 전체를 다시 압축하면 손대지 않은 그림까지 재압축 손실이 생기므로,
**바뀐 자리의 DXT5 블록만** 갈아 끼운다. 그래서 파일 크기가 그대로다
(오브젝트 길이가 안 변하니 애셋 파일을 다시 쓸 필요도 없다).

  python krtitle.py [작업트리]
"""
import io
import os
import struct
import sys

from PIL import Image
from UnityPy.enums import TextureFormat
from UnityPy.export import Texture2DConverter as T2C
from UnityPy.files.SerializedFile import SerializedFile
from UnityPy.streams import EndianBinaryReader

import uiatlas
from sfparse import parse

TREE = sys.argv[1] if len(sys.argv) > 1 else 'x77'
CN_PARTS = 'assets/bin/Data/sharedassets0.assets'
KR = 'kr/assets/bin/Data/sharedassets0.assets'

CN_TEX, CN_ATLAS = 29, 646
KR_TEX, KR_ATLAS = 35, 834

# 옮겨올 조각과 중국판에서 놓을 자리(빈 영역 y 0~965). 4의 배수로 둔다.
MOVE = [('Together', 0, 0), ('Cha01', 192, 0), ('Cha02', 344, 0),
        ('Cha03', 480, 0)]


def read_parts(base):
    """splitN 을 이어 붙여 통째로 읽는다. (바이트, 조각크기목록)"""
    sizes = []
    buf = bytearray()
    i = 0
    while True:
        p = '%s.split%d' % (base, i)
        if not os.path.exists(p):
            break
        b = io.open(p, 'rb').read()
        sizes.append(len(b))
        buf += b
        i += 1
    if not sizes:
        raise SystemExit('조각 파일이 없다: ' + base)
    return bytearray(buf), sizes


def write_parts(base, data, sizes):
    off = 0
    for i, n in enumerate(sizes):
        io.open('%s.split%d' % (base, i), 'wb').write(bytes(data[off:off + n]))
        off += n
    assert off == len(data), (off, len(data))
    if os.path.exists(base):                 # 통짜 파일도 있으면 같이 맞춘다
        io.open(base, 'wb').write(bytes(data))


def obj_span(meta, pid):
    for o in meta['objects']:
        if o['path_id'] == pid:
            return meta['data_offset'] + o['start'], o['size']
    raise SystemExit('오브젝트를 못 찾았다: %d' % pid)


def main():
    base = os.path.join(TREE, CN_PARTS)
    data, sizes = read_parts(base)
    meta = parse_bytes(bytes(data))

    tex_off, tex_size = obj_span(meta, CN_TEX)
    atl_off, atl_size = obj_span(meta, CN_ATLAS)

    # --- 텍스처 -----------------------------------------------------------
    sf = SerializedFile(EndianBinaryReader(bytes(data)), None)
    cn_img = sf.objects[CN_TEX].read().image.convert('RGBA')
    W, H = cn_img.size
    npix = W * H                                   # DXT5 는 픽셀당 1바이트
    img_at = tex_off + tex_size - npix
    assert struct.unpack_from('<i', data, img_at - 4)[0] == npix, '이미지 자리 확인 실패'
    orig_blocks = bytes(data[img_at:img_at + npix])

    kr_sf = SerializedFile(EndianBinaryReader(io.open(KR, 'rb').read()), None)
    kr_img = kr_sf.objects[KR_TEX].read().image.convert('RGBA')
    kr_tab = uiatlas.table(bytearray(kr_sf.objects[KR_ATLAS].get_raw_data()))

    new_img = cn_img.copy()
    dirty = []
    placed = {}
    for name, dx, dy in MOVE:
        _p, o, _i, _v = kr_tab[name]
        sx, sy, sw, sh = (int(round(v)) for v in o)
        piece = kr_img.crop((sx, sy, sx + sw, sy + sh))
        new_img.paste(piece, (dx, dy))
        placed[name] = (dx, dy, sw, sh)
        dirty.append((dx, dy, sw, sh))
        print('  %-10s 한국판(%d,%d,%dx%d) -> 중국판(%d,%d)'
              % (name, sx, sy, sw, sh, dx, dy))

    enc, fmt = T2C.image_to_texture2d(new_img, TextureFormat.DXT5)
    assert fmt == TextureFormat.DXT5 and len(enc) == npix, (fmt, len(enc), npix)

    # 바뀐 자리의 블록만 옮긴다. flip=True 로 압축하므로 블록 줄은 아래에서 위로 센다.
    bw = W // 4
    merged = bytearray(orig_blocks)
    moved = 0
    for dx, dy, w, h in dirty:
        for y in range(dy, dy + h):
            br = (H - 1 - y) // 4
            for bx in range(dx // 4, (dx + w + 3) // 4):
                k = (br * bw + bx) * 16
                if merged[k:k + 16] != enc[k:k + 16]:
                    merged[k:k + 16] = enc[k:k + 16]
                    moved += 1
    data[img_at:img_at + npix] = merged
    print('  DXT5 블록 %d개 교체' % moved)

    # --- 스프라이트 표 -----------------------------------------------------
    blob = bytearray(data[atl_off:atl_off + atl_size])
    tab = uiatlas.table(blob)
    for name, (dx, dy, w, h) in placed.items():
        p, _o, _i, v = tab[name]
        uiatlas.set_payload(blob, p, (dx, dy, w, h), (dx, dy, w, h), v)
        print('  %-10s 좌표 -> (%d, %d, %d, %d)' % (name, dx, dy, w, h))
    data[atl_off:atl_off + atl_size] = blob

    write_parts(base, data, sizes)
    print('%s 다시 씀 (%d바이트, 조각 %d개)' % (base, len(data), len(sizes)))


def parse_bytes(b):
    """sfparse.parse 는 경로를 받으므로 임시로 떨군다."""
    tmp = '_krtitle_tmp.assets'
    io.open(tmp, 'wb').write(b)
    try:
        return parse(tmp)
    finally:
        os.remove(tmp)


if __name__ == '__main__':
    main()
