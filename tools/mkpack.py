# -*- coding: utf-8 -*-
"""packspec.txt 를 읽어 복원 자산 번들(bundles/pack.unity3d)을 다시 만듭니다.

  packspec.txt  한 줄 = 자산 하나
      <직렬화파일>:<번들안이름>:<루트pathID>[:<dx>][:옵션…]
  sfmerge 가 그 줄들을 하나의 직렬화 파일로 합치고,
  mkbundle 이 거기에 UnityRaw 껍데기를 씌웁니다.

  python mkpack.py
"""
import io
import os
import subprocess
import sys

CODE = os.path.dirname(os.path.abspath(__file__))
# 도구는 tools/ 안에 있고, 작업 트리(x77 · saves · lang …)는 그 위에 있다.
HERE = os.path.dirname(CODE)
SPEC = os.path.join(HERE, 'packspec.txt')
MERGED = os.path.join(HERE, 'pack.dat')
OUT = os.path.join(HERE, 'bundles', 'pack.unity3d')
CAB = 'CAB-pack.dat'


def build(quiet=False):
    if not os.path.exists(SPEC):
        raise SystemExit('packspec.txt 가 없습니다')
    n = len([x for x in io.open(SPEC, encoding='utf-8').read().splitlines()
             if x.strip()])
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    steps = [
        ([sys.executable, os.path.join(CODE, 'sfmerge.py'),
          MERGED, 'pack', '@' + SPEC],
         '자산 %d개 합치기' % n),
        ([sys.executable, os.path.join(CODE, 'mkbundle.py'), OUT, MERGED, CAB], '번들 씌우기'),
    ]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    for cmd, label in steps:
        r = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True,
                           encoding='utf-8', errors='replace', env=env)
        tail = (r.stdout or '').strip().splitlines()
        if not quiet:
            print('%-16s %s' % (label, tail[-1] if tail else 'ok'))
        if r.returncode != 0:
            print((r.stdout or '')[-800:])
            print((r.stderr or '')[-800:])
            raise SystemExit('%s 에서 실패했습니다' % label)
    return os.path.getsize(OUT)


if __name__ == '__main__':
    size = build()
    print('%s  %.1f MB' % (OUT, size / 1048576.0))
