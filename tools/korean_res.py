# -*- coding: utf-8 -*-
"""중국 배포판에만 있는 중국어 이미지를 한국판 것으로 바꾼다.

  · assets/bin/Data/splash.png  : 起動 시 뜨는 "360手机助手" 화면
  · res/**/app_icon.png         : 런처 아이콘의 车 + 万友玩游 배지

splash 는 유니티가 그대로 띄우는 PNG 라 크기를 바꿔도 되지만,
원본 비율(800x500)을 지키고 남는 위아래는 배경색으로 채운다.

  python korean_res.py [작업트리]
"""
import io
import os
import sys
import zipfile

from PIL import Image

import chapaths

TREE = sys.argv[1] if len(sys.argv) > 1 else 'x77'
# 원본 APK 자리는 chapaths 가 찾습니다 (CHA_APK_DIR · apk/ · 여기 · 부모).
KR = chapaths.apk('kr')              # 다함께 차차차 한국판
KAKAO = chapaths.apk('kakao')        # 카카오판


def png_from(apk, name):
    with zipfile.ZipFile(apk) as z:
        return Image.open(io.BytesIO(z.read(name)))


def fit(img, size, bg=None):
    """비율을 지켜 넣고 남는 자리는 가장자리 색으로 채운다."""
    w, h = size
    src = img.convert('RGB')
    if bg is None:
        bg = src.getpixel((1, 1))
    out = Image.new('RGB', size, bg)
    s = min(w / src.width, h / src.height)
    r = src.resize((max(1, int(src.width * s)), max(1, int(src.height * s))),
                   Image.LANCZOS)
    out.paste(r, ((w - r.width) // 2, (h - r.height) // 2))
    return out


def main():
    # --- 시작 화면 ---------------------------------------------------------
    dst = os.path.join(TREE, 'assets/bin/Data/splash.png')
    cur = Image.open(dst)
    new = fit(png_from(KR, 'assets/bin/Data/splash.png'), cur.size)
    new.save(dst)
    print('시작 화면 %s <- 한국판 (%s)' % (cur.size, new.size))

    # --- 런처 아이콘 -------------------------------------------------------
    # 카카오판 아이콘이 중국판과 같은 그림에 글자만 CHA 다(중국판은 车).
    n = 0
    for sub in ('drawable', 'drawable-ldpi', 'drawable-mdpi',
                'drawable-hdpi', 'drawable-xhdpi'):
        p = os.path.join(TREE, 'res', sub, 'app_icon.png')
        if not os.path.exists(p):
            continue
        size = Image.open(p).size
        try:
            src = png_from(KAKAO, 'res/%s/app_icon.png' % sub)
        except KeyError:
            src = png_from(KAKAO, 'res/drawable-xhdpi/app_icon.png')
        src.convert('RGBA').resize(size, Image.LANCZOS).save(p)
        n += 1
    print('런처 아이콘 %d개 교체' % n)


if __name__ == '__main__':
    main()
