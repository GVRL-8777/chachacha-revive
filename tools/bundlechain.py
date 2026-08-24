# -*- coding: utf-8 -*-
"""번들에 **차례로 덧붙이는** 도구들이 서로를 지우지 않게 한다.

`packadd` 는 이미 구운 번들에 얹는 도구다. 처음부터 다시 굽는 길은 없다
(`tools/packadd.py` 의 설명을 보라). 그래서 얹는 도구는 저마다 "손대기 전
모습"으로 되돌린 뒤 자기 것을 붙인다 — 두 번 돌려도 두 번 붙지 않도록.

그런데 되돌릴 자리가 하나뿐이면 **뒷사람이 앞사람 것을 지운다.** 차를 넣고
보이스를 넣으면 차가 사라진다. 그래서 단계마다 자리를 따로 둔다.

    bundle       손대기 전 원본
    bundle5      addcars5   정품 차 8대
    bundlevox    addvox5    보이스 3명
    bundletroy   addtroy    트로이

`start(단계)` 는 **바로 앞에 있는 단계**에서 되살리고, `done(단계)` 는 지금
모습을 그 단계에 남기면서 **뒤 단계들을 지운다**(이제 낡았으므로).

앞 단계가 아직 없으면 그보다 더 앞을 찾는다. 그래서 도구를 건너뛰고 돌려도
말이 된다 — 차를 안 넣고 트로이만 넣으면 원본 위에 트로이만 얹힌다.
"""
import io
import os
import shutil

CODE = os.path.dirname(os.path.abspath(__file__))
HERE = os.path.dirname(CODE)

PACKDAT = os.path.join(HERE, 'pack.dat')
BUNDLE = os.path.join(HERE, 'bundles', 'pack.unity3d')
FILES = (PACKDAT, BUNDLE)

STAGES = [('bundle', '손대기 전 원본'),
          ('bundle5', '정품 차 8대 (addcars5)'),
          ('bundlevox', '보이스 3명 (addvox5)'),
          ('bundletroy', '트로이 (addtroy)')]


def _dir(name):
    return os.path.join(HERE, 'backup', name)


def _has(name):
    d = _dir(name)
    return all(os.path.exists(os.path.join(d, os.path.basename(p)))
               for p in FILES)


def _put(name):
    d = _dir(name)
    os.makedirs(d, exist_ok=True)
    for p in FILES:
        shutil.copy2(p, os.path.join(d, os.path.basename(p)))


def _get(name):
    d = _dir(name)
    for p in FILES:
        shutil.copy2(os.path.join(d, os.path.basename(p)), p)


def index(stage):
    for i, (n, _t) in enumerate(STAGES):
        if n == stage:
            return i
    raise SystemExit('모르는 단계입니다: %s' % stage)


def start(stage, say=print):
    """앞 단계에서 되살린다. 아무 것도 없으면 지금 것을 원본으로 남긴다."""
    i = index(stage)
    for j in range(i - 1, -1, -1):
        if _has(STAGES[j][0]):
            _get(STAGES[j][0])
            say('번들을 %s 에서 되살렸습니다 (%s)'
                % (STAGES[j][0], STAGES[j][1]))
            return STAGES[j][0]
    _put('bundle')
    say('번들 원본을 backup/bundle 에 남겼습니다')
    return None


def done(stage, say=print):
    """지금 모습을 이 단계에 남기고 뒤 단계들을 지운다(낡았다)."""
    _put(stage)
    i = index(stage)
    stale = [n for n, _t in STAGES[i + 1:] if os.path.isdir(_dir(n))]
    for n in stale:
        shutil.rmtree(_dir(n))
    say('번들을 backup/%s 에 남겼습니다%s'
        % (stage, ' · 낡은 단계 %s 를 지웠습니다' % ', '.join(stale)
           if stale else ''))


def status(say=print):
    for n, t in STAGES:
        d = _dir(n)
        size = 0
        if _has(n):
            size = os.path.getsize(os.path.join(d, 'pack.unity3d'))
        say('  %-12s %-24s %s'
            % (n, t, '%.1f MB' % (size / 1048576.0) if size else '없음'))
    return 0


if __name__ == '__main__':
    status()
