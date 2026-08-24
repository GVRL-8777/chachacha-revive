# -*- coding: utf-8 -*-
"""트로이의 **자동차 샵 아이콘**을 만들어 아틀라스에 넣는다.

`addtroy.py` 가 차를 되살려도 목록에서는 빈 칸으로 나온다. 아이콘은 3D
모델이 아니라 `Atlas_SpecialCarIcon`(512x512) 안에 미리 그려 둔 작은 그림을
이름으로 찾아 쓰기 때문이다. 이름 규칙은 `<차이름>_<등급>` 이다.

원판에는 트로이 그림이 없다. 그려 둘 리가 없다 — 잘려 나간 차니까.
그래서 **모델을 그대로 렌더해서** 만든다. 원판 아이콘들도 같은 모델을
찍어 만든 것이라 나란히 두어도 튀지 않는다.

  · 카메라는 거의 옆모습이다. 원판 아이콘들은 3/4 앞옆인데, 목마를 그렇게
    돌리면 72x55 에서 갈색 덩어리가 된다. 여러 각도를 뽑아 보고 골랐다.
  · 텍스처는 픽셀마다 UV 를 보간해 찍고, 면 법선으로 아주 옅은 명암만 준다.
  · 바닥에 흐린 타원 그림자. 원판 아이콘에도 있다.
  · 등급이 다섯이지만 트로이는 등급이 올라도 모양이 같다. 그래서 **그림은
    한 장만 넣고 스프라이트 다섯을 같은 자리로 가리킨다.**

아틀라스의 오른쪽 위(224,0)-(512,288)는 통째로 비어 있다(실측). 거기 쓴다.

    python tools/troyicon.py --scan     빈 자리와 지금 스프라이트를 본다
    python tools/troyicon.py            넣는다
    python tools/troyicon.py --restore  backup/atlas 에서 되돌린다
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
BAK = os.path.join(HERE, 'backup', 'atlas')
ASSETS = os.path.join(HERE, 'troy.assets')

ATLAS = 'e319f1a9aae42d44abe80babf4113fcf'      # UIAtlas(MonoBehaviour) pathID 3
ATLAS_PID = 3
TEXTURE = '75abec148c765894abb1c2e7bd6b6154'    # Texture2D:Atlas_SpecialCarIcon

NAME = 'Troy'
KLASSES = ('C', 'B', 'A', 'S', 'R')
YAW, PITCH = 265.0, 12.0        # 거의 옆모습. 목마는 옆에서 봐야 목마다.
                                # 3/4 로 돌리면 72x55 에서 갈색 덩어리가 된다.
BOX = (72, 56)                  # 원판 아이콘들과 같은 크기대.
                                # DXT5 칸이 4x4 라 가로세로 다 4의 배수여야 한다.
FREE = (224, 0, 512, 288)       # 아틀라스에서 비어 있는 네모


# ------------------------------------------------------------------ 렌더
def _skinned():
    """`troy.assets` 의 메시를 뼈까지 먹여 실제로 서는 자리로 옮긴다."""
    import numpy as np
    import UnityPy
    env = UnityPy.load(ASSETS)
    mesh = [o for o in env.objects if o.type.name == 'Mesh'][0].read_typetree()
    tex = [o for o in env.objects
           if o.type.name == 'Texture2D'
           and o.read_typetree()['m_Name'] == '%s_Tex' % NAME][0]
    vd = mesh['m_VertexData']
    n = vd['m_VertexCount']
    d = bytes(vd['m_DataSize'])
    off1 = vd['m_Streams'][1]['offset']
    v = np.array([struct.unpack_from('<3f', d, i * 12) for i in range(n)])
    uv = np.array([struct.unpack_from('<2f', d, off1 + i * 8) for i in range(n)])
    ib = bytes(mesh['m_IndexBuffer'])
    idx = np.array(struct.unpack('<%dH' % (len(ib) // 2), ib)).reshape(-1, 3)
    bone = np.array([s['boneIndex[0]'] for s in mesh['m_Skin']])

    def m4(x):
        return np.array([[x['e%d%d' % (r, c)] for c in range(4)]
                         for r in range(4)])

    bp = [m4(b) for b in mesh['m_BindPose']]

    def trs(p, q):
        x, y, z, w = q
        R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                      [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                      [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
        M = np.eye(4)
        M[:3, :3] = R
        M[:3, 3] = p
        return M

    # 뼈 계층은 이 게임의 모든 차가 똑같다 (실측).
    shadow = trs((0, 0.025, 0), (-0.5, -0.5, -0.5, 0.5))
    dummy = shadow @ trs((0, 0, -0.013), (0, 0, 0, 1))
    wheel = dummy @ trs((0, 0, 0.048), (0, 0, 0, 1))
    body = wheel @ trs((0, 0, 0.074), (0, 0, 0, 1))
    B = [body, wheel, shadow]
    w = np.array([(B[bone[i]] @ bp[bone[i]] @ np.array([v[i][0], v[i][1],
                                                        v[i][2], 1.0]))[:3]
                  for i in range(n)])
    return w, uv, idx, bone, tex.read().image.convert('RGB')


def render(size=512):
    """모델을 한 장 그린다. 알파가 있는 RGBA 로 돌려준다."""
    import numpy as np
    from PIL import Image
    W, UV, IDX, BONE, tim = _skinned()
    tex = np.array(tim).astype(np.float32)
    TH, TW, _ = tex.shape

    cy, sy = np.cos(np.radians(YAW)), np.sin(np.radians(YAW))
    cp, sp = np.cos(np.radians(PITCH)), np.sin(np.radians(PITCH))
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    P = W @ Ry.T @ Rx.T
    tris = IDX[BONE[IDX[:, 0]] != 2]            # 바닥 그림자 판은 뺀다
    pts = P[:, :2].copy()
    pts[:, 1] = -pts[:, 1]
    u = np.unique(tris)
    lo, hi = pts[u].min(0), pts[u].max(0)
    sc = (size * 0.86) / max(hi - lo)
    off = (np.array([size, size]) - (hi - lo) * sc) / 2
    Q = (pts - lo) * sc + off

    img = np.zeros((size, size, 4), np.float32)
    z = np.full((size, size), 1e9)
    light = np.array([-0.45, 0.70, 0.55])
    for t in tris:
        a, b, c = t
        nrm = np.cross(W[b] - W[a], W[c] - W[a])
        L = np.linalg.norm(nrm)
        nrm = nrm / L if L > 1e-9 else np.array([0.0, 0.0, 1.0])
        lit = 0.70 + 0.30 * max(0.0, float((Ry @ nrm) @ light))
        x0 = int(max(0, np.floor(Q[t, 0].min())))
        x1 = int(min(size - 1, np.ceil(Q[t, 0].max())))
        y0 = int(max(0, np.floor(Q[t, 1].min())))
        y1 = int(min(size - 1, np.ceil(Q[t, 1].max())))
        if x1 < x0 or y1 < y0:
            continue
        ax, ay = Q[a]
        bx, by = Q[b]
        cx, cyy = Q[c]
        den = (by - cyy) * (ax - cx) + (cx - bx) * (ay - cyy)
        if abs(den) < 1e-9:
            continue
        ys, xs = np.mgrid[y0:y1 + 1, x0:x1 + 1]
        l1 = ((by - cyy) * (xs - cx) + (cx - bx) * (ys - cyy)) / den
        l2 = ((cyy - ay) * (xs - cx) + (ax - cx) * (ys - cyy)) / den
        l3 = 1 - l1 - l2
        m = (l1 >= -0.002) & (l2 >= -0.002) & (l3 >= -0.002)
        if not m.any():
            continue
        zz = l1 * P[a, 2] + l2 * P[b, 2] + l3 * P[c, 2]
        cur = z[y0:y1 + 1, x0:x1 + 1]
        m &= zz < cur
        if not m.any():
            continue
        uu = l1 * UV[a, 0] + l2 * UV[b, 0] + l3 * UV[c, 0]
        vv = l1 * UV[a, 1] + l2 * UV[b, 1] + l3 * UV[c, 1]
        col = tex[np.clip((vv * TH).astype(int), 0, TH - 1),
                  np.clip((uu * TW).astype(int), 0, TW - 1)] * lit
        sub = img[y0:y1 + 1, x0:x1 + 1]
        sub[m, :3] = col[m]
        sub[m, 3] = 255
        cur[m] = zz[m]
    return Image.fromarray(np.clip(img, 0, 255).astype('uint8'))


def shrink(im, tw, th):
    """크게 그린 것을 아이콘 크기로 줄인다.

    두 가지를 지켜야 가장자리가 깨끗하다.

      · **알파를 곱해 두고** 줄인다. 그냥 줄이면 실루엣 바깥의 (0,0,0,0)
        이 색 계산에 끼어들어 둘레에 검거나 알록달록한 테가 생긴다.
      · **넓이 평균(BOX)** 으로 줄이고 셈은 실수로 한다. 란초스는 큰 배율로
        줄일 때 울려서 없는 색을 만들어 내고, 중간에 uint8 로 깎으면
        알파가 작은 자리에서 나눗셈이 튀어 흰 테가 생긴다."""
    import numpy as np
    from PIL import Image
    a = np.array(im).astype(np.float32)
    al = a[..., 3] / 255.0
    ch = [a[..., i] * al for i in range(3)] + [al]
    small = [np.array(Image.fromarray(c, 'F').resize((tw, th), Image.BOX))
             for c in ch]
    sa = small[3]
    safe = np.maximum(sa, 1e-4)
    rgb = np.stack([np.clip(small[i] / safe, 0, 255) for i in range(3)], axis=2)
    out = np.concatenate([rgb, (sa * 255.0)[..., None]], axis=2)
    return Image.fromarray(np.clip(out, 0, 255).astype('uint8'))


def icon():
    """아틀라스에 붙일 크기로 다듬는다 — 여백을 자르고 그림자를 깐다."""
    from PIL import Image, ImageDraw, ImageFilter
    im = render()
    im = im.crop(im.getbbox())
    w, h = BOX
    sc = min((w - 2) / float(im.width), (h - 8) / float(im.height))
    im = shrink(im, max(1, int(im.width * sc)), max(1, int(im.height * sc)))

    out = Image.new('RGBA', BOX, (0, 0, 0, 0))
    # 바닥 그림자를 먼저 깐다. 원판 아이콘들도 이런 흐린 타원을 쓴다.
    sh = Image.new('RGBA', BOX, (0, 0, 0, 0))
    d = ImageDraw.Draw(sh)
    cx, cy = w // 2, h - 6
    d.ellipse([cx - im.width * 0.42, cy - 4, cx + im.width * 0.42, cy + 4],
              fill=(0, 0, 0, 120))
    out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(2.0)))
    out.alpha_composite(im, ((w - im.width) // 2, h - 6 - im.height))
    return bleed(out)


def bleed(im, rounds=3):
    """비친 자리로 색을 번지게 한다.

    DXT5 는 4x4 칸마다 색 끝점 두 개를 잡는데, 실루엣 가장자리 칸에 **비친
    검정**이 섞이면 끝점이 검정 쪽으로 끌려가 테두리에 빨강·초록 얼룩이
    생긴다. 알파는 그대로 두고 색만 바깥으로 밀어 두면 그 일이 없어진다."""
    import numpy as np
    from PIL import Image
    a = np.array(im).astype(np.int32)
    keep = a[..., 3].copy()                 # 알파는 끝까지 그대로 둔다
    rgb = a[..., :3]
    # 색을 퍼뜨릴 밑천은 **웬만큼 불투명한 픽셀**만 친다. 거의 비친
    # 가장자리를 밑천으로 삼으면 그 색이 밖으로 번져 얼룩이 된다.
    have = keep >= 24
    for _ in range(rounds):
        acc = np.zeros_like(rgb)
        cnt = np.zeros(have.shape, np.int32)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            acc += np.roll(np.roll(rgb, dy, 0), dx, 1) \
                * np.roll(np.roll(have, dy, 0), dx, 1)[..., None]
            cnt += np.roll(np.roll(have, dy, 0), dx, 1)
        fill = (~have) & (cnt > 0)
        if not fill.any():
            break
        rgb[fill] = acc[fill] // np.maximum(cnt, 1)[fill][..., None]
        have = have | fill
    a[..., 3] = keep
    return Image.fromarray(a.astype('uint8'))


# ------------------------------------------------------------------ 넣기
def _atlas_blob():
    from UnityPy.streams import EndianBinaryReader
    from UnityPy.files.SerializedFile import SerializedFile
    p = os.path.join(XD, ATLAS)
    sf = SerializedFile(EndianBinaryReader(io.open(p, 'rb').read()), None)
    return p, bytearray(sf.objects[ATLAS_PID].get_raw_data())


def _record(name, x, y, w, h, size):
    b = struct.pack('<i', len(name)) + name.encode('utf-8')
    b += b'\0' * ((-len(b)) % 4)
    b += struct.pack('<4f', x, y, w, h)          # outer
    b += struct.pack('<4f', x, y, w, h)          # inner (원판도 같은 값)
    b += struct.pack('<%di' % ((size - 32) // 4), *([0] * ((size - 32) // 4)))
    return b


def free_spot(w, h):
    """빈 네모 안에서 4의 배수 자리를 고른다 (DXT 는 4x4 블록이다)."""
    x0, y0, x1, y1 = FREE
    if x0 + w > x1 or y0 + h > y1:
        raise SystemExit('빈 자리가 모자랍니다')
    return (x0 + 3) & ~3, (y0 + 3) & ~3


def scan(say=print):
    p, blob = _atlas_blob()
    size = uiatlas.layout(bytes(blob))
    t = uiatlas.table(bytes(blob))
    say('아틀라스 %s — 스프라이트 %d개 · 레코드 %d바이트'
        % (ATLAS[:12], len(t), size or -1))
    mine = sorted(k for k in t if k.startswith(NAME + '_'))
    say('트로이 것: %s' % (' · '.join(mine) if mine else '없음'))
    import numpy as np
    import UnityPy
    env = UnityPy.load(os.path.join(XD, TEXTURE))
    o = [x for x in env.objects if x.type.name == 'Texture2D'][0]
    tt = o.read_typetree()
    a = np.array(o.read().image)
    x0, y0, x1, y1 = FREE
    empty = bool((a[y0:y1, x0:x1, 3] == 0).all())
    say('텍스처 %dx%d fmt=%d — 오른쪽 위 (%d,%d)-(%d,%d) %s'
        % (tt['m_Width'], tt['m_Height'], tt['m_TextureFormat'],
           x0, y0, x1, y1, '비어 있음' if empty else '**뭔가 있음**'))
    return 0


def install(say=print):
    import numpy as np
    import UnityPy
    from UnityPy.enums import TextureFormat
    from UnityPy.export import Texture2DConverter as T2C
    from PIL import Image
    from sfparse import parse
    from sfedit import replace_object

    if not os.path.exists(ASSETS):
        raise SystemExit('troy.assets 가 없습니다. 먼저 addtroy.py 를 돌리세요.')
    os.makedirs(BAK, exist_ok=True)
    for fn in (ATLAS, TEXTURE):
        b = os.path.join(BAK, fn)
        if os.path.exists(b):
            shutil.copy2(b, os.path.join(XD, fn))     # 늘 같은 자리에서 시작
        else:
            shutil.copy2(os.path.join(XD, fn), b)

    im = icon()
    x, y = free_spot(*BOX)
    say('아이콘 %dx%d 를 (%d,%d) 에 넣습니다' % (im.width, im.height, x, y))

    # --- 텍스처 ---
    #
    # 판을 통째로 다시 압축하면 **이미 들어 있는 아이콘 42개까지** 한 번 더
    # 손실 압축을 먹는다. DXT5 는 4x4 칸끼리 서로를 모르므로, 우리 그림이
    # 덮는 칸만 따로 눌러 원본 바이트 사이에 끼워 넣는다. 나머지 칸은
    # 바이트 하나 안 바뀐다.
    tp = os.path.join(XD, TEXTURE)
    env = UnityPy.load(tp)
    o = [q for q in env.objects if q.type.name == 'Texture2D'][0]
    t = dict(o.read_typetree())
    if int(t['m_TextureFormat']) != int(TextureFormat.DXT5):
        raise SystemExit('DXT5 판만 다룹니다 (지금 %s)' % t['m_TextureFormat'])
    piece, _fmt = T2C.image_to_texture2d(im, TextureFormat.DXT5)
    data = bytearray(t['image data'])
    per_row = t['m_Width'] // 4                 # 한 줄에 든 칸 수
    bw, bh = im.width // 4, im.height // 4
    # 유니티 텍스처는 **아래에서 위로** 담긴다. 아틀라스 좌표는 반대로
    # 왼쪽 **위**가 원점이다. 그래서 줄 번호를 뒤집어야 한다.
    # (안 뒤집으면 그림이 판 아래쪽, 이미 아이콘이 있는 자리에 떨어진다)
    top = (t['m_Height'] - y - im.height) // 4
    for r in range(bh):
        dst = ((top + r) * per_row + x // 4) * 16
        src = r * bw * 16
        data[dst:dst + bw * 16] = piece[src:src + bw * 16]
    changed = bw * bh
    say('  DXT5 칸 %d개만 갈아 끼웠습니다 (판 전체 %d개)'
        % (changed, per_row * (t['m_Height'] // 4)))
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

    # --- 스프라이트 다섯 ---
    p, d = _atlas_blob()
    size = uiatlas.layout(bytes(d))
    if size is None:
        raise SystemExit('아틀라스 레코드 길이를 못 읽었습니다')
    have = set(uiatlas.table(bytes(d)))
    add = [k for k in ('%s_%s' % (NAME, c) for c in KLASSES) if k not in have]
    if not add:
        say('스프라이트가 이미 다 있습니다')
        return 0
    extra = b''.join(_record(k, x, y, im.width, im.height, size) for k in add)
    n = struct.unpack_from('<i', d, uiatlas.HDR_COUNT)[0]
    # 배열 뒤에는 꼬리 16바이트가 있다. 새 레코드는 그 **앞**에 넣는다.
    end = len(d) - uiatlas.TAIL
    d = d[:end] + extra + d[end:]
    struct.pack_into('<i', d, uiatlas.HDR_COUNT, n + len(add))
    replace_object(p, ATLAS_PID, bytes(d))
    say('스프라이트 %d개 추가: %s' % (len(add), ' · '.join(add)))
    say('아틀라스 %d -> %d개' % (n, n + len(add)))
    return 0


def restore(say=print):
    if not os.path.isdir(BAK):
        raise SystemExit('남겨 둔 원본이 없습니다: %s' % BAK)
    k = 0
    for fn in sorted(os.listdir(BAK)):
        shutil.copy2(os.path.join(BAK, fn), os.path.join(XD, fn))
        k += 1
    say('되돌린 파일 %d개' % k)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scan', action='store_true')
    ap.add_argument('--restore', action='store_true')
    ap.add_argument('--png', help='아이콘만 PNG 로 뽑아 본다')
    a = ap.parse_args()
    if a.scan:
        return scan()
    if a.restore:
        return restore()
    if a.png:
        icon().save(a.png)
        print('%s 를 썼습니다' % a.png)
        return 0
    return install()


if __name__ == '__main__':
    sys.exit(main())
