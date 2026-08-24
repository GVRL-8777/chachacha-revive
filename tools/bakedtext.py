# -*- coding: utf-8 -*-
"""프리팹에 박힌 문구 중 **말이 어긋난 것**을 고친다.

`bakedkr.py` 가 중국판 프리팹에 구워진 중국어 UILabel 78개를 한국어로 옮겼다.
그때는 원문만 보고 옮겼는데, 나중에 문자열표를 한국 정식판 것으로 바꾸고
나니 **표에 이미 공식 문구가 있는 자리**가 드러났다. 표를 따르는 게 맞다.

지금 고치는 것

    意外终止  →  (bakedkr) 비정상 종료  →  **일시 정지**

주행 중 일시정지 화면의 제목이다. 중국어 `意外终止`(뜻밖의 중단)를 글자대로
옮겨 '비정상 종료'가 되었는데, 이건 앱이 죽었을 때 쓰는 말이라 화면과 안
맞는다. 같은 화면의 단추 셋은 표를 타므로 이미 제대로 나온다.

    PauseTitleLabel = 일시 정지        ← 표에 있는 공식 문구
    ContinuePlay    = 게임 계속하기
    ReturnShop      = 상점으로 돌아가기
    ReturnCarRoom   = 차고로 돌아가기

제목만 프리팹(`level0`)에 박혀 있어 표를 안 탄다.

## `bakedcar.py` 와 무엇이 다른가

`bakedcar.py` 는 **바이트 수가 같은** 차 이름만 제자리에서 덮어쓴다
(미아우→미야우). 이쪽은 길이가 달라지므로(16→13바이트) 오브젝트를 다시
짜야 한다. `sfedit.replace_object` 가 그 일을 한다.

    python tools/bakedtext.py --scan     어디에 무엇이 박혀 있나
    python tools/bakedtext.py            고친다
    python tools/bakedtext.py --restore  backup/bakedtext 에서 되돌린다
"""
import argparse
import io
import os
import shutil
import struct
import sys

CODE = os.path.dirname(os.path.abspath(__file__))
HERE = os.path.dirname(CODE)
sys.path.insert(0, CODE)

XD = os.path.join(HERE, 'x77', 'assets', 'bin', 'Data')
BAK = os.path.join(HERE, 'backup', 'bakedtext')

# UILabel 의 `m_Text` 자리. MonoBehaviour 머리(오브젝트 8 · 켜짐 4 · 스크립트 8
# · 이름 4 = 24)에 UIWidget 필드가 붙고 그 뒤가 본문이다. `bakedkr.py` 가
# 실측해 쓰던 값과 같다.
TEXT_OFF = 72

# 고칠 것. (지금 박혀 있는 말, 바꿀 말, 왜)
FIX = [
    ('비정상 종료', '일시 정지',
     '주행 중 일시정지 화면 제목. 표의 PauseTitleLabel 과 맞춘다'),
]


def _files():
    for name in sorted(os.listdir(XD)):
        p = os.path.join(XD, name)
        if '.split' in name or not os.path.isfile(p) or os.path.getsize(p) < 512:
            continue
        yield name, p


def _read(blob):
    """`m_Text` 를 읽는다. UILabel 이 아니면 None."""
    if len(blob) < TEXT_OFF + 4:
        return None
    n = struct.unpack_from('<i', blob, TEXT_OFF)[0]
    if not (0 < n < 4000) or TEXT_OFF + 4 + n > len(blob):
        return None
    try:
        return blob[TEXT_OFF + 4:TEXT_OFF + 4 + n].decode('utf-8')
    except Exception:
        return None


def _swap(blob, new):
    """`m_Text` 를 갈아 끼운 새 blob. 길이가 달라져도 된다."""
    n = struct.unpack_from('<i', blob, TEXT_OFF)[0]
    end = TEXT_OFF + 4 + n
    end += (-n) % 4                                  # 4바이트 정렬 패딩
    b = new.encode('utf-8')
    mid = struct.pack('<i', len(b)) + b + b'\0' * ((-len(b)) % 4)
    return blob[:TEXT_OFF] + mid + blob[end:]


def find(say=lambda *a: None):
    """(파일, pathID, 지금 말, 바꿀 말, 원본 blob) 목록."""
    from sfparse import parse
    want = dict((old, new) for old, new, _why in FIX)
    hits = []
    for name, p in _files():
        try:
            meta = parse(p)
        except Exception:
            continue
        raw = io.open(p, 'rb').read()
        for o in meta['objects']:
            if o['class_id'] != 114 or o['size'] < TEXT_OFF + 8:
                continue
            st = meta['data_offset'] + o['start']
            blob = raw[st:st + o['size']]
            t = _read(blob)
            if t in want:
                hits.append((name, o['path_id'], t, want[t], blob))
    return hits


def scan(say=print):
    for old, new, why in FIX:
        say('  %-14s → %-12s %s' % (old, new, why))
    say('')
    hits = find(say)
    if not hits:
        say('  박혀 있는 자리가 없습니다 (이미 고쳤거나 이 판에 없습니다).')
        return 0
    for name, pid, old, new, blob in hits:
        say('  %-16s pathID %-5s %-14s → %-12s (%d → %d바이트)'
            % (name[:16], pid, old, new,
               len(blob), len(_swap(blob, new))))
    return 0


def fix(say=print):
    from sfedit import replace_object
    hits = find(say)
    if not hits:
        say('고칠 자리가 없습니다.')
        return 0
    os.makedirs(BAK, exist_ok=True)
    for name, pid, old, new, blob in hits:
        p = os.path.join(XD, name)
        b = os.path.join(BAK, name)
        if not os.path.exists(b):
            shutil.copy2(p, b)
        replace_object(p, pid, _swap(blob, new))
        say('  %-16s pathID %-5s %s → %s' % (name[:16], pid, old, new))
    say('고친 자리 %d곳. 원본은 backup/bakedtext 에 있습니다.' % len(hits))
    return 0


def restore(say=print):
    if not os.path.isdir(BAK):
        raise SystemExit('남겨 둔 원본이 없습니다: %s' % BAK)
    n = 0
    for name in sorted(os.listdir(BAK)):
        shutil.copy2(os.path.join(BAK, name), os.path.join(XD, name))
        n += 1
    say('되돌린 파일 %d개' % n)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scan', action='store_true')
    ap.add_argument('--restore', action='store_true')
    a = ap.parse_args()
    if a.scan:
        return scan()
    if a.restore:
        return restore()
    return fix()


if __name__ == '__main__':
    sys.exit(main())
