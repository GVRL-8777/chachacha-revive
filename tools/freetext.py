# -*- coding: utf-8 -*-
"""차 상점의 값 자리에 뜨는 `Free` 문구를 '무료' 로 줄입니다.

값이 0 인 차(헬리)는 값 라벨에 `Free` 키의 글이 들어갑니다. 원래 '무료지급'
이었는데, 아직 안 산 차에 '지급' 은 어울리지 않아 '무료' 로 줄입니다.

`Free` 키를 쓰는 곳은 `Generic_MyCarHouseMain::_UpdateFunctionUIDontHaveCar`
한 군데뿐이라 다른 화면에는 영향이 없습니다.

TextAsset 은 길이가 바뀌면 뒤 오브젝트가 전부 밀리므로 **줄어든 만큼 뒤에
공백을 답니다.** 표를 읽는 `ByteReader::ReadDictionary` 가 '=' 로 자른 뒤
양쪽을 Trim 하므로 공백은 사라집니다.

표는 CRLF 로 끝납니다. 정규식의 점(.) 은 캐리지리턴까지 먹으므로 줄 끝을
집어삼키지 않게 잡아야 합니다. 한 번 삼켰다가 그 줄만 LF 가 되었습니다.

  python freetext.py [작업트리]
"""
import io
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sfparse import parse

TREE = sys.argv[1] if len(sys.argv) > 1 else 'x77'
ASSET = os.path.join('assets', 'bin', 'Data',
                     '50295c6b20ff907439e2ef8aa05f9ea7')
PATHID = 1
WANT = '무료'
LINE = re.compile('^(Free[ \t]*=[ \t]*)([^\r\n]*)', re.M)


def textasset(raw, meta, pid):
    rec = [o for o in meta['objects'] if o['path_id'] == pid][0]
    st = meta['data_offset'] + rec['start']
    blob = bytes(raw[st:st + rec['size']])
    n = struct.unpack_from('<i', blob, 0)[0]
    off = 4 + n
    off += (-off) % 4
    tlen = struct.unpack_from('<i', blob, off)[0]
    tst = st + off + 4
    return raw[tst:tst + tlen].decode('utf-8'), tst, tlen


def main():
    p = os.path.join(TREE, ASSET)
    raw = bytearray(io.open(p, 'rb').read())
    meta = parse(p)
    text, tst, tlen = textasset(raw, meta, PATHID)

    m = LINE.search(text)
    if not m:
        raise SystemExit('Free 줄을 못 찾았습니다')
    cur = m.group(2)
    if cur.strip() == WANT:
        print('이미 %r 입니다' % WANT)
        return 0
    pad = len(cur.encode('utf-8')) - len(WANT.encode('utf-8'))
    if pad < 0:
        raise SystemExit('새 글이 더 깁니다 — 길이를 못 지킵니다')
    out = text[:m.start(2)] + WANT + ' ' * pad + text[m.end(2):]

    blob = out.encode('utf-8')
    assert len(blob) == tlen, ('길이가 달라졌습니다', len(blob), tlen)
    raw[tst:tst + tlen] = blob
    io.open(p, 'wb').write(bytes(raw))
    print('Free: %r -> %r (뒤에 공백 %d칸, 파일 길이 그대로)'
          % (cur.strip(), WANT, pad))
    return 0


if __name__ == '__main__':
    sys.exit(main())
