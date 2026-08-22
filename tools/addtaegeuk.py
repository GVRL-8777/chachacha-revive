# -*- coding: utf-8 -*-
"""태극호를 게임 데이터에 등록한다.

  1. CarDataBase 에 항목 한 줄  — trimcars.py 가 지운 자리(공백)에 써 넣는다.
     그래서 파일 길이가 그대로고, 애셋 파일을 다시 쓸 필요가 없다.
  2. tb_systemtext 에 이름표  — 차 이름은 `CarName_<CarName>` 으로 찾는다.
     이쪽은 길이가 늘어나므로 텍스트 자산 파일을 통째로 다시 쓴다.

  python addtaegeuk.py [작업트리]
"""
import io
import json
import os
import struct
import sys

sys.path.insert(0, '.')
from sfparse import parse
from mktaegeuk import write_serialized

TREE = sys.argv[1] if len(sys.argv) > 1 else 'x77'
CARDB = 'assets/bin/Data/ade64ecd8944d9640bb1438deb4f6fe3'
TEXT = 'assets/bin/Data/50295c6b20ff907439e2ef8aa05f9ea7'

CAR_INDEX = 18                 # 서버 carNo = 19
CAR_NAME = 'Taegeukho'
CAR_LABEL = '태극호'

ENTRY = {
    "CarName": CAR_NAME,
    "CarIndex": CAR_INDEX,
    "StartCarClassType": "S",
    "CostGold": 0,
    "UnlockTrophy": 150,
    "Preminum": True,
    "NewCar": True,
    "EventCar": False,
    "RivalCar": False,
    "IsRobot": False,
    "HasMission": False,
    "MissionType": "none",
    "IsGotyaEvent": False,
    "GotyaCost": 15,
    "GotyaRetryCost": 10,
    "CarIconAtlas": "Atlas_CarIcon",
    # S 하나만 둔다. R 등급 프리팹이 없어서, 올릴 수 있게 두면 빈 차가 된다.
    "CarClassDataArray": [{
        "CarClassType": "S",
        "MaxSpeed": 388,
        "CarWeight": 1650,
        "SpeedPerSecond": 74,
        "NextStepSpeed": 179,
        "NextSpeedPerSecond": 8.2,
        "OilMileage": 15,
    }],
}


def textasset(raw, meta, pid=1):
    rec = [o for o in meta['objects'] if o['path_id'] == pid][0]
    st = meta['data_offset'] + rec['start']
    blob = bytes(raw[st:st + rec['size']])
    n = struct.unpack_from('<i', blob, 0)[0]
    off = 4 + n
    off += (-off) % 4
    tlen = struct.unpack_from('<i', blob, off)[0]
    return blob, st, off, tlen


def add_cardb():
    p = os.path.join(TREE, CARDB)
    raw = bytearray(io.open(p, 'rb').read())
    meta = parse(p)
    _blob, st, off, tlen = textasset(raw, meta)
    tst = st + off + 4
    text = raw[tst:tst + tlen].decode('utf-8')

    arr = json.loads(text)['CarDataBase']['CarInfoDB']['CarDataArray']
    if any(c['CarIndex'] == CAR_INDEX for c in arr):
        print('이미 등록돼 있다 (CarIndex %d)' % CAR_INDEX)
        return
    used = set(c['CarIndex'] for c in arr)
    assert CAR_INDEX not in used, 'CarIndex %d 가 이미 쓰인다' % CAR_INDEX

    piece = json.dumps(ENTRY, ensure_ascii=False, separators=(',', ':')) + ','
    # trimcars 가 비워 둔 공백 자리를 찾는다
    gap = ' ' * (len(piece) + 40)
    i = text.find(gap)
    if i < 0:
        raise SystemExit('빈 자리가 모자라다. trimcars.py 를 먼저 돌려야 한다')
    out = text[:i] + piece + text[i + len(piece):]
    assert len(out) == len(text)
    json.loads(out)                      # 문법 확인

    raw[tst:tst + tlen] = out.encode('utf-8')
    io.open(p, 'wb').write(bytes(raw))
    n = len(json.loads(out)['CarDataBase']['CarInfoDB']['CarDataArray'])
    print('CarDataBase 등록: %s (CarIndex %d) — 이제 %d대' % (CAR_NAME, CAR_INDEX, n))


def add_name():
    p = os.path.join(TREE, TEXT)
    raw = bytearray(io.open(p, 'rb').read())
    meta = parse(p)
    blob, st, off, tlen = textasset(raw, meta)
    tst = st + off + 4
    text = raw[tst:tst + tlen].decode('utf-8')
    key = 'CarName_%s' % CAR_NAME
    if key in text:
        print('이름표가 이미 있다')
        return
    anchor = 'CarName_AVEO'
    i = text.index(anchor)
    nl = '\r\n' if '\r\n' in text else '\n'
    line = '%s = %s%s' % (key, CAR_LABEL, nl)
    text = text[:i] + line + text[i:]

    # 텍스트 자산을 통째로 다시 쓴다 (길이가 늘었다).
    # TextAsset 은 m_Name · m_Script · m_PathName 세 문자열이라
    # 손으로 이어 붙이지 말고 타입트리 왕복으로 만든다.
    from UnityPy.streams import EndianBinaryReader
    from UnityPy.files.SerializedFile import SerializedFile
    sf = SerializedFile(EndianBinaryReader(bytes(raw)), None)
    o = sf.objects[1]
    tree = o.read_typetree()
    tree['m_Script'] = text
    new_blob = bytes(o.save_typetree(tree))
    write_serialized(p, meta, [(1, 49, new_blob)],
                     [os.path.basename(e) for e in meta['externals']])
    print('이름표 추가: %s = %s (본문 %d -> %d바이트)'
          % (key, CAR_LABEL, tlen, len(text.encode('utf-8'))))


if __name__ == '__main__':
    add_cardb()
    add_name()
