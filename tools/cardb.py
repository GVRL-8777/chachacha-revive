# -*- coding: utf-8 -*-
"""빌드에서 CarDataBase 를 읽어 옵니다 (TextAsset 안의 JSON)."""
import io, json, os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sfparse import parse


def _text(p, pid=1):
    meta = parse(p)
    raw = io.open(p, 'rb').read()
    rec = [o for o in meta['objects'] if o['path_id'] == pid][0]
    st = meta['data_offset'] + rec['start']
    b = raw[st:st + rec['size']]
    n = struct.unpack_from('<i', b, 0)[0]
    off = 4 + n
    off += (-off) % 4
    tlen = struct.unpack_from('<i', b, off)[0]
    return b[off + 4:off + 4 + tlen].decode('utf-8', 'replace')


def find(tree, needle, klass=49):
    """텍스트 자산 중 needle 이 든 것을 찾아 내용을 돌려줍니다."""
    d = os.path.join(tree, 'assets/bin/Data')
    for fn in sorted(os.listdir(d)):
        if '.split' in fn:
            continue
        p = os.path.join(d, fn)
        try:
            meta = parse(p)
        except Exception:
            continue
        for o in meta['objects']:
            if o['class_id'] != klass or o['size'] < 64:
                continue
            try:
                t = _text(p, o['path_id'])
            except Exception:
                continue
            if needle in t:
                return fn, t
    return None, None


def cars(tree):
    fn, t = find(tree, 'CarInfoDB')
    if t is None:
        return None
    return json.loads(t)['CarDataBase']['CarInfoDB']['CarDataArray']
