# -*- coding: utf-8 -*-
"""CarDataBase 안의 차 한 대 값을 고칩니다.

텍스트 자산이라 길이가 바뀌면 파일을 통째로 다시 써야 합니다. 그래서
`trimcars.py` 가 비워 둔 **공백 자리에서 그만큼 꾸어 오거나 돌려주어**
전체 길이를 지킵니다.

  python carprice.py <차이름> --gold 0 --trophy 60
  python carprice.py helly --show
"""
import argparse
import io
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sfparse import parse

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.join(HERE, 'x77')
CARDB = os.path.join('assets', 'bin', 'Data',
                     'ade64ecd8944d9640bb1438deb4f6fe3')


def _textasset(raw, meta, pid=1):
    rec = [o for o in meta['objects'] if o['path_id'] == pid][0]
    st = meta['data_offset'] + rec['start']
    b = raw[st:st + rec['size']]
    n = struct.unpack_from('<i', b, 0)[0]
    off = 4 + n
    off += (-off) % 4
    tlen = struct.unpack_from('<i', b, off)[0]
    return st, off, tlen


def _biggest_gap(text):
    """가장 긴 공백 구간 (시작, 길이)."""
    best = (0, 0)
    i = 0
    while True:
        i = text.find('  ', i)
        if i < 0:
            break
        j = i
        while j < len(text) and text[j] == ' ':
            j += 1
        if j - i > best[1]:
            best = (i, j - i)
        i = j
    return best


def main():
    ap = argparse.ArgumentParser(prog='carprice')
    ap.add_argument('name')
    ap.add_argument('--gold', type=int)
    ap.add_argument('--trophy', type=int)
    ap.add_argument('--show', action='store_true')
    a = ap.parse_args()

    p = os.path.join(TREE, CARDB)
    raw = bytearray(io.open(p, 'rb').read())
    meta = parse(p)
    st, off, tlen = _textasset(raw, meta)
    tst = st + off + 4
    text = raw[tst:tst + tlen].decode('utf-8')
    db = json.loads(text)
    arr = db['CarDataBase']['CarInfoDB']['CarDataArray']
    hit = [c for c in arr if c['CarName'] == a.name]
    if not hit:
        raise SystemExit('그런 차가 없습니다: %s' % a.name)
    c = hit[0]
    if a.show or (a.gold is None and a.trophy is None):
        print('%s: %s급 · 골드 %d · 트로피 %d · premium=%s'
              % (c['CarName'], c['StartCarClassType'], c['CostGold'],
                 c['UnlockTrophy'], c.get('Preminum')))
        return 0

    old_piece = json.dumps(c, ensure_ascii=False, separators=(',', ':'))
    if old_piece not in text:
        raise SystemExit('항목 자리를 찾지 못했습니다(손으로 고친 적이 있나요?)')
    if a.gold is not None:
        c['CostGold'] = a.gold
    if a.trophy is not None:
        c['UnlockTrophy'] = a.trophy
    new_piece = json.dumps(c, ensure_ascii=False, separators=(',', ':'))
    out = text.replace(old_piece, new_piece, 1)

    diff = len(out) - len(text)
    if diff:
        gs, gl = _biggest_gap(out)
        if gl < diff:
            raise SystemExit('공백 자리가 %d칸 모자랍니다' % (diff - gl))
        # 길어졌으면 공백에서 꾸어 오고, 짧아졌으면 공백을 늘립니다
        out = out[:gs] + ' ' * (gl - diff) + out[gs + gl:]
    assert len(out) == len(text), (len(out), len(text))
    json.loads(out)
    raw[tst:tst + tlen] = out.encode('utf-8')
    io.open(p, 'wb').write(bytes(raw))
    print('%s: 골드 %d · 트로피 %d 로 고쳤습니다 (파일 길이 그대로)'
          % (c['CarName'], c['CostGold'], c['UnlockTrophy']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
