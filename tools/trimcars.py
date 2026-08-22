# -*- coding: utf-8 -*-
"""CarDataBase 에서 **모델이 없는 차**를 지운다.

중국판에는 Archangel(34) W3(35) Blitz(36) Pluto(37) 의 자원이 아예 없다.
그런데 차고 캐러셀은 CarDataBase 에 있는 차를 전부 만들어 보므로,
'자동차 샵' 탭으로 넘어가는 순간 Instantiate(null) 로 죽는다
(ViewPortcarSub.CarObject._MakeRenderObject). 그래서 탭이 먹통처럼 보인다.

TextAsset 은 길이가 바뀌면 애셋 파일을 통째로 다시 써야 하므로,
지울 항목 자리를 **공백으로 덮어** 길이를 그대로 둔다. JSON 은 공백을 무시한다.

  python trimcars.py [작업트리]
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, '.')
from sfparse import parse

TREE = sys.argv[1] if len(sys.argv) > 1 else 'x77'
ASSET = 'assets/bin/Data/ade64ecd8944d9640bb1438deb4f6fe3'
PATHID = 1
DROP = (34, 35, 36, 37)          # CarIndex


def main():
    p = os.path.join(TREE, ASSET)
    raw = bytearray(io.open(p, 'rb').read())
    meta = parse(p)
    rec = [o for o in meta['objects'] if o['path_id'] == PATHID][0]
    st = meta['data_offset'] + rec['start']
    blob = bytes(raw[st:st + rec['size']])

    # TextAsset: 이름(길이접두, 4정렬) + 본문(길이접두)
    import struct
    n = struct.unpack_from('<i', blob, 0)[0]
    off = 4 + n
    off += (-off) % 4
    tlen = struct.unpack_from('<i', blob, off)[0]
    tst = st + off + 4
    text = raw[tst:tst + tlen].decode('utf-8')
    print('CarDataBase 본문 %d바이트' % tlen)

    before = json.loads(text)['CarDataBase']['CarInfoDB']['CarDataArray']
    print('지우기 전 차 %d대' % len(before))

    out = text
    for idx in DROP:
        # "CarIndex": <idx> 를 품은 { ... } 덩어리를 찾는다
        m = re.search(r'"CarIndex"\s*:\s*%d\s*,' % idx, out)
        if not m:
            print('  이미 없음: CarIndex %d' % idx)
            continue
        # 앞쪽 여는 중괄호
        s = out.rfind('{', 0, m.start())
        # 짝 맞는 닫는 중괄호
        depth = 0
        e = s
        while e < len(out):
            if out[e] == '{':
                depth += 1
            elif out[e] == '}':
                depth -= 1
                if depth == 0:
                    break
            e += 1
        e += 1
        # 뒤에 쉼표가 있으면 같이, 없으면 앞 쉼표를 같이 지운다
        j = e
        while j < len(out) and out[j] in ' \t\r\n':
            j += 1
        if j < len(out) and out[j] == ',':
            e = j + 1
        else:
            k = s - 1
            while k >= 0 and out[k] in ' \t\r\n':
                k -= 1
            if k >= 0 and out[k] == ',':
                s = k
        out = out[:s] + ' ' * (e - s) + out[e:]
        print('  지움: CarIndex %d (%d바이트를 공백으로)' % (idx, e - s))

    assert len(out) == len(text), (len(out), len(text))
    arr = json.loads(out)['CarDataBase']['CarInfoDB']['CarDataArray']
    print('지운 뒤 차 %d대: %s' % (len(arr), [c['CarIndex'] for c in arr]))

    raw[tst:tst + tlen] = out.encode('utf-8')
    io.open(p, 'wb').write(bytes(raw))
    print('%s 다시 씀 (길이 그대로)' % p)


if __name__ == '__main__':
    main()
