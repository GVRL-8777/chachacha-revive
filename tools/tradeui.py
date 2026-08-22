# -*- coding: utf-8 -*-
"""되팔기 팝업 프리팹의 빈 참조들을 메웁니다.

중국판은 이 기능을 들어내면서 프리팹의 참조도 같이 비워 놨습니다.
두 종류를 메웁니다.

  1) `m_CarClassSprite_SellName` · `m_CarClassSprite_BuyName` 두 UISprite
     참조가 (0,0) 입니다. `SetCarNameBoard` 가 첫 줄에서 그 색을 만지므로
     팝업을 열자마자 널참조로 죽습니다. 같은 역할의 살아 있는 스프라이트를
     가리키게 합니다.

  2) **팝업 안 UILabel 전부가 폰트 없이(mFont=(0,0)) 있습니다.** 그래서
     차 이름도 트로피 값도 버튼 글자도 아무것도 안 그려집니다.
     다른 화면의 정상 라벨들이 쓰는 폰트(sharedassets0 의 pathID 5)를
     가리키게 합니다.

PPtr 8바이트를 제자리에서 바꾸므로 파일 길이가 변하지 않습니다.

  python tradeui.py [작업트리]
"""
import glob
import io
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sfparse import parse

TREE = sys.argv[1] if len(sys.argv) > 1 else 'x77'
POP_PID = 227                      # TradeCarPop MonoBehaviour
FIELD_OFF = 24                     # 이름 길이 0 이라 필드가 여기서 시작합니다
FIX = {4: 329, 5: 333}             # 칸 번호 -> 대신 가리킬 pathID

UILABEL_SCRIPT = 579               # sharedassets0 안 UILabel 스크립트
# UILabel 은 참조를 **둘** 듭니다.
#   +24  위젯 머티리얼 ("Font Material")  — 없으면 그릴 재료가 없습니다
#   +64  UIFont (NGUI 폰트는 MonoBehaviour 입니다) — 없으면 글자 모양이 없습니다
# 둘 다 비어 있어서 이 팝업만 글자가 통째로 안 나왔습니다.
# (앞 40바이트는 색·피벗·깊이라 길이가 고정이라 자리가 늘 같습니다)
MAT_OFF, MAT_PID = 24, 5           # 정상 라벨 164개가 쓰는 머티리얼
FONT_OFF, FONT_PID = 64, 640       # 정상 라벨 268개가 쓰는 폰트


def fix_sprites(raw, meta):
    rec = [o for o in meta['objects'] if o['path_id'] == POP_PID][0]
    st = meta['data_offset'] + rec['start']
    done = 0
    for slot, target in FIX.items():
        at = st + FIELD_OFF + slot * 8
        f, q = struct.unpack_from('<ii', raw, at)
        if (f, q) == (0, 0):
            struct.pack_into('<ii', raw, at, 0, target)
            done += 1
        elif (f, q) != (0, target):
            print('  %d번 칸이 예상과 다릅니다 (%d,%d) — 건너뜁니다' % (slot, f, q))
    return done


def fix_fonts(raw, meta):
    ext = [os.path.basename(e) for e in meta['externals']]
    if 'sharedassets0.assets' not in ext:
        print('  sharedassets0 참조가 없어 폰트를 못 붙입니다')
        return 0
    s0 = ext.index('sharedassets0.assets') + 1
    done = 0
    for o in meta['objects']:
        if o['class_id'] != 114 or o['size'] < 80:
            continue
        st = meta['data_offset'] + o['start']
        if struct.unpack_from('<ii', raw, st + 12) != (s0, UILABEL_SCRIPT):
            continue
        for off, pid in ((MAT_OFF, MAT_PID), (FONT_OFF, FONT_PID)):
            at = st + off
            if struct.unpack_from('<ii', raw, at) == (0, 0):
                struct.pack_into('<ii', raw, at, s0, pid)
                done += 1
    return done


def main():
    hits = glob.glob(os.path.join(TREE, 'assets/bin/Data/cc0714d3da48*'))
    if not hits:
        raise SystemExit('TradeCarPop 프리팹을 찾지 못했습니다')
    p = hits[0]
    meta = parse(p)
    raw = bytearray(io.open(p, 'rb').read())
    a = fix_sprites(raw, meta)
    b = fix_fonts(raw, meta)
    if a or b:
        io.open(p, 'wb').write(bytes(raw))
    print('되팔기 팝업: 스프라이트 %d곳 · 라벨 참조 %d곳을 메웠습니다 (%s)'
          % (a, b, os.path.basename(p)))


if __name__ == '__main__':
    main()
