# -*- coding: utf-8 -*-
"""tb_systemtext 의 문구를 **길이를 지키며** 바꾼다.

TextAsset 은 길이가 바뀌면 뒤따르는 오브젝트 offset 이 전부 밀려 애셋 파일을
통째로 다시 써야 한다. 그래서 바이트 수가 같은 말로만 바꾼다.

  "라인" -> "카톡"   (둘 다 한글 2자 = 12바이트)

이 빌드의 한국어 표는 LINE 판에서 온 것이라 "라인으로 보내시겠습니까?" 처럼
LINE 이야기가 남아 있다. 사설 서버에는 어느 쪽도 없지만, 중국어보다는 낫고
무엇보다 길이가 같아 안전하다.

'타임라인' 안의 '라인'은 건드리지 않는다.

  python krtext.py [작업트리]
"""
import io
import os
import re
import struct
import sys

sys.path.insert(0, '.')
from sfparse import parse

TREE = sys.argv[1] if len(sys.argv) > 1 else 'x77'
ASSET = 'assets/bin/Data/50295c6b20ff907439e2ef8aa05f9ea7'
PATHID = 1


def textasset(raw, meta, pid):
    """(본문, 본문시작오프셋, 길이) 를 준다."""
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

    before = text.count('라인')
    # '타임라인' 은 그대로 둔다
    out = re.sub(r'(?<!타임)라인', '카톡', text)
    after = out.count('라인')
    print('"라인" %d곳 중 %d곳 -> "카톡" (타임라인 %d곳은 그대로)'
          % (before, before - after, after))

    blob = out.encode('utf-8')
    assert len(blob) == tlen, ('길이가 달라졌다', len(blob), tlen)
    raw[tst:tst + tlen] = blob
    io.open(p, 'wb').write(bytes(raw))
    print('%s 다시 씀 (길이 그대로 %d바이트)' % (p, tlen))

    for line in out.splitlines():
        if '카톡' in line and ('Invite' in line or 'SendTire' in line):
            print('   ', line[:90])


if __name__ == '__main__':
    main()
