# -*- coding: utf-8 -*-
"""드라이버 선택 창의 능력 설명 글자 크기를 줄입니다.

NGUI 2.x 는 폰트 크기를 따로 들고 있지 않습니다. **라벨 트랜스폼의 크기가
곧 글자 크기**입니다. 그래서 설명 라벨의 `m_LocalScale` 만 고치면 됩니다.

설명 글은 프리팹에 박혀 있지 않고 `UILocalize` 가 켜질 때 채웁니다
(키가 `Char<번호>Exp`). 그래서 프리팹에서 글자를 찾을 수는 없고,
UILocalize 컴포넌트의 키로 라벨을 찾아야 합니다.

기본은 24 인데, 김준현(5번)만 원래 18.83 으로 줄여 두었습니다. 설명이
길어 카드 밖으로 넘치기 때문입니다. 갸루상(6번)·앵그리성호(7번)·쌈바여인(11번)
도 같은 이유로 같은 값에 맞춥니다.

표에 적힌 값이 곧 최종 상태입니다. 여러 번 돌려도 결과가 같습니다.
플로트만 덮어쓰므로 파일 길이는 그대로입니다.

  python drvfont.py            현재 크기를 보여 줍니다
  python drvfont.py --apply    표대로 맞춥니다
"""
import io
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import drvprice as dp                                        # noqa: E402
from UnityPy.streams import EndianBinaryReader               # noqa: E402
from UnityPy.files.SerializedFile import SerializedFile      # noqa: E402
from sfparse import parse                                    # noqa: E402

CODE = os.path.dirname(os.path.abspath(__file__))
# 도구는 tools/ 안에 있고, 작업 트리(x77 · saves · lang …)는 그 위에 있다.
HERE = os.path.dirname(CODE)
PREFAB = os.path.join(HERE, 'x77', 'assets', 'bin', 'Data',
                      '51161fc3df9f94087a76edf2817d987a')

# Transform 의 m_LocalScale 자리:
#   m_GameObject(8) + m_LocalRotation(16) + m_LocalPosition(12)
SCALE_OFF = 36

# 김준현(5번) 이 쓰는 값 그대로. 손으로 고른 게 아니라 원작이 쓰던 값입니다.
SMALL = struct.unpack('<f', struct.pack('<f', 18.825725555419922))[0]
BASE = 24.0
SMALL_KEYS = (5, 6, 7, 11)
TARGET = dict(('Char%dExp' % i, SMALL if i in SMALL_KEYS else BASE)
              for i in range(1, 13))


def scan():
    """UILocalize 키 -> (트랜스폼 pathID, 현재 크기)."""
    sf = SerializedFile(EndianBinaryReader(io.open(PREFAB, 'rb').read()), None)
    names = dp.script_names()
    loc = set(k for k, v in names.items() if v == 'UILocalize')
    tr_of = {}
    for pid, ob in sf.objects.items():
        if ob.type.name == 'Transform':
            t = ob.read_typetree()
            tr_of[t['m_GameObject']['m_PathID']] = pid
    out = {}
    for pid, ob in sf.objects.items():
        if ob.type.name != 'MonoBehaviour':
            continue
        d = ob.get_raw_data()
        if len(d) < 28 or struct.unpack_from('<i', d, 16)[0] not in loc:
            continue
        n = struct.unpack_from('<i', d, 24)[0]
        if not 0 < n < 64:
            continue
        key = d[28:28 + n].decode('utf-8', 'replace')
        go = struct.unpack_from('<i', d, 4)[0]
        if go in tr_of:
            out[key] = tr_of[go]
    return out


def offsets(want):
    """트랜스폼 pathID -> 파일 안의 m_LocalScale 자리."""
    meta = parse(PREFAB)
    out = {}
    for o in meta['objects']:
        if o['path_id'] in want:
            out[o['path_id']] = meta['data_offset'] + o['start'] + SCALE_OFF
    return out


def main():
    keys = scan()
    want = dict((k, v) for k, v in keys.items() if k.endswith('Exp'))
    off = offsets(set(want.values()))
    raw = bytearray(io.open(PREFAB, 'rb').read())

    apply_ = '--apply' in sys.argv
    changed = 0
    for key in sorted(want, key=lambda s: int(s[4:-3])):
        o = off[want[key]]
        cur = struct.unpack_from('<fff', raw, o)
        mark = ''
        goal = TARGET.get(key)
        if apply_ and goal is not None and abs(cur[0] - goal) > 1e-4:
            struct.pack_into('<fff', raw, o, goal, goal, cur[2])
            mark = ' -> %.2f' % goal
            changed += 1
        print('  %-10s %.2f%s' % (key, cur[0], mark))
    if apply_ and changed:
        io.open(PREFAB, 'wb').write(bytes(raw))
        print('%d개를 줄였습니다 (파일 길이 그대로)' % changed)
    return 0


if __name__ == '__main__':
    sys.exit(main())
