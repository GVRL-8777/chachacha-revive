# -*- coding: utf-8 -*-
"""프리팹에 **박혀 있는** 차 이름을 한국 정식 이름으로 고친다.

`tools/krmerge.py` 가 문자열표(`tb_systemtext`)를 한국 정식판 것으로 바꾸는데,
그것만으로는 부족한 자리가 있다. 이 빌드에는 **UILabel 에 글자가 직접 구워진**
곳이 있어서(초대 보상 화면의 "미아우 또는 골드 X20000" 같은) 표를 고쳐도
옛 이름이 그대로 남는다.

다행히 고쳐야 할 이름들은 **바이트 수가 같다.**

    미아우 → 미야우   (둘 다 9바이트)
    허미  → 해미    (둘 다 6바이트)

그래서 파일 길이도 오브젝트 표도 건드리지 않고 제자리에서 덮어쓰면 된다.
길이가 다른 이름이 새로 나오면 이 도구는 **건드리지 않고 알려만 준다** —
그건 `sfedit` 로 오브젝트를 다시 짜야 하는 일이다.

    python tools/bakedcar.py --scan     어디에 무엇이 박혀 있나
    python tools/bakedcar.py            고친다
    python tools/bakedcar.py --restore  backup/baked 에서 되돌린다
"""
import argparse
import io
import os
import shutil
import sys

CODE = os.path.dirname(os.path.abspath(__file__))
HERE = os.path.dirname(CODE)
DATA = os.path.join(HERE, 'x77', 'assets', 'bin', 'Data')
BAK = os.path.join(HERE, 'backup', 'baked')

# 옛 이름 -> 한국 정식 이름. `tb_systemtext` 의 `CarName_*` 와 같은 짝이다.
# 바이트 수가 같은 것만 여기 둔다.
RENAME = {
    '미아우': '미야우',      # CAT
    '허미': '해미',         # Hummer
}

# 길이가 달라 제자리 수정이 안 되는 것들. 나오면 알려만 준다.
WATCH = {
    '가루다': '수리카', '칸칠': '카방', '엠퍼러': '엠페러', '블링': '싸넹',
    '블록스': '블럭스', '스피드스터': '블럭스', '팔콘': '팰콘', '모게': '쵸퍼',
    '앰버': '엠버', '판다': 'Ne88', '빅풋': '하드로드', '미니': '당기니',
}

# 차 이름이 아닌데 걸리는 말들. 세는 데서 뺀다.
# `아이패드 미니` 는 초대 이벤트 경품 이름이라 차 `미니`(당기니)와 무관하다.
EXCLUDE = ('아이패드 미니',)

SKIP = ('50295c6b20ff907439e2ef8aa05f9ea7',)   # 문자열표는 krmerge 담당


def _count(blob, word):
    """오탐(다른 말의 일부)을 뺀 등장 횟수."""
    n = blob.count(word.encode('utf-8'))
    for phrase in EXCLUDE:
        if word in phrase:
            n -= blob.count(phrase.encode('utf-8'))
    return max(0, n)


def files():
    for name in sorted(os.listdir(DATA)):
        p = os.path.join(DATA, name)
        if name in SKIP or not os.path.isfile(p) or os.path.getsize(p) < 128:
            continue
        yield name, p


def scan():
    both = dict(RENAME)
    both.update(WATCH)
    found = 0
    for name, p in files():
        b = io.open(p, 'rb').read()
        for old, new in sorted(both.items()):
            c = _count(b, old)
            if not c:
                continue
            ok = len(old.encode('utf-8')) == len(new.encode('utf-8'))
            print('  %-16s %-6s -> %-6s %d곳   %s'
                  % (name[:16], old, new, c,
                     '제자리 수정 가능' if ok else '**길이가 달라 손으로 고쳐야 함**'))
            found += c
    if not found:
        print('  박혀 있는 옛 이름이 없습니다.')
    return 0


def fix():
    os.makedirs(BAK, exist_ok=True)
    total = 0
    for name, p in files():
        b = io.open(p, 'rb').read()
        out = b
        hits = []
        for old, new in RENAME.items():
            o, n = old.encode('utf-8'), new.encode('utf-8')
            if len(o) != len(n):
                continue
            c = _count(out, old)
            if c:
                out = out.replace(o, n)
                hits.append('%s->%s ×%d' % (old, new, c))
                total += c
        if out != b:
            bak = os.path.join(BAK, name)
            if not os.path.exists(bak):
                shutil.copy2(p, bak)
            io.open(p, 'wb').write(out)
            print('  %-16s %s' % (name[:16], ' · '.join(hits)))
    print('고친 자리 %d곳' % total)
    # 길이가 달라 못 고친 것이 남아 있으면 알려 준다.
    left = []
    for name, p in files():
        b = io.open(p, 'rb').read()
        for old, new in WATCH.items():
            if _count(b, old):
                left.append((name, old, new))
    for name, old, new in left:
        print('  남음: %-16s %s -> %s (길이가 달라 손으로 고쳐야 함)'
              % (name[:16], old, new))
    return 0


def restore():
    if not os.path.isdir(BAK):
        raise SystemExit('남겨 둔 원본이 없습니다: %s' % BAK)
    n = 0
    for name in sorted(os.listdir(BAK)):
        shutil.copy2(os.path.join(BAK, name), os.path.join(DATA, name))
        n += 1
    print('되돌린 파일 %d개' % n)
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
