# -*- coding: utf-8 -*-
"""드라이버 9~12번 초상화를 중국판 UI 아틀라스에 추가한다.

두 가지를 동시에 해야 한다:
  1) 텍스처(Atlas_MainMenu)의 빈 공간에 1.4.2 초상화를 59x60 으로 축소해 합성
  2) UIAtlas(MonoBehaviour)의 스프라이트 표에 이름+좌표 레코드를 추가

UIAtlas 레코드는 **68바이트 고정**임을 실측으로 확인했다(이름 문자열 4+n+정렬 포함).
기존 레코드 하나를 통째로 복제한 뒤 이름과 좌표만 덮어쓰면 크기가 안 변해 안전하다.
(NGUI 는 배열 길이 필드를 먼저 읽으므로 그 값도 함께 늘린다)
"""
import io, os, re, struct, sys
from PIL import Image
import UnityPy
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile

CN = 'survey/5577.com.cjenm.chachachacn/assets/bin/Data'
SRC = 'survey/gogo142/assets/bin/Data'

# 1.4.2 아틀라스에서 가져올 초상화 (스프라이트번호 -> 중국판에 붙일 이름)
TAKE = [(8, 'PTDriverPc8'), (9, 'PTDriverPc9'), (10, 'PTDriverPc10'), (11, 'PTDriverPc11')]
SRC_COORD = {8: (444, 275), 9: (444, 37), 10: (444, 394), 11: (325, 156)}
SRC_CELL = 118
DST_SLOTS = [(632, 0), (692, 0), (752, 0), (812, 0)]   # 중국판 아틀라스 빈 자리
CELL_W, CELL_H = 59, 60


def main():
    # --- 1) 텍스처 합성 -------------------------------------------------
    src_img = Image.open('atlas_driverpic_142.png').convert('RGBA')
    dst_img = Image.open('atlas_mainmenu_cn.png').convert('RGBA')
    for (idx, name), (dx, dy) in zip(TAKE, DST_SLOTS):
        sx, sy = SRC_COORD[idx]
        cell = src_img.crop((sx, sy, sx + SRC_CELL, sy + SRC_CELL))
        cell = cell.resize((CELL_W, CELL_H), Image.LANCZOS)
        dst_img.paste(cell, (dx, dy))
        print("  %s <- 1.4.2 Pc%d  ->  (%d,%d)" % (name, idx, dx, dy))
    dst_img.save('atlas_mainmenu_new.png')
    print("텍스처 합성 완료: atlas_mainmenu_new.png")


if __name__ == '__main__':
    main()
