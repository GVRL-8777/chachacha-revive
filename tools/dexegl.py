# -*- coding: utf-8 -*-
"""유니티의 **EGL 설정 고르는 코드**를 고친다 (Mali 기기에서 3D 가 검게 나오는 문제).

무슨 문제였나. 갤럭시 A35(Mali-G68 · 안드로이드 16)에서 차와 길이 새까맣게
나왔다. 원인은 **깊이 버퍼가 없는 EGL 설정**을 잡는 것이었다. 깊이가 없으면
그리는 순서가 곧 앞뒤가 되어, 이 게임이 차 메시를 한 벌 더 복사해 그리는
**그림자가 차 위를 덮는다.**

유니티 4 의 설정 고르기는 자바(`com.unity3d.player` 의 난독화된 클래스)에 있고
이렇게 돈다.

    eglChooseConfig(조건 배열) -> 후보들
    후보를 손으로 거른다 (깊이 · 스텐실 · 색 비트 · MSAA)
    다 걸러지면 조건을 하나씩 풀어 다시 거른다
    그래도 없으면 **후보[0] 을 그냥 집는다**   ← 여기가 문제

조건 배열에 `EGL_DEPTH_SIZE` 가 **아예 없어서** 깊이 0 짜리까지 후보로 들어오고,
Mali 에서는 그 후보[0] 이 깊이 0 이었다. Adreno 는 우연히 깊이 있는 것이 앞에
와서 멀쩡했다.

고치는 법은 한 줄이다 — **조건 배열에 `EGL_DEPTH_SIZE 16` 을 넣는다.**
그러면 깊이 없는 설정이 후보에 아예 안 들어온다. 기기를 가리지 않으므로
아드레노 · 말리 판을 따로 만들 필요가 없다.

    python tools/dexegl.py --check     지금 상태를 본다
    python tools/dexegl.py             고친다
    python tools/dexegl.py --restore   backup/dex 에서 되돌린다

smali · baksmali 는 `tools/jars/` 에 둔다 (메이븐의 org.smali 2.5.2).
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

CODE = os.path.dirname(os.path.abspath(__file__))
HERE = os.path.dirname(CODE)
JARS = os.path.join(CODE, 'jars')
DEX = os.path.join(HERE, 'x77', 'classes.dex')
BAK = os.path.join(HERE, 'backup', 'dex', 'classes.dex')
WORK = os.path.join(HERE, '_scratch', 'dexegl')

NEED = ('baksmali', 'smali', 'dexlib2', 'util', 'guava', 'jcommander',
        'antlr-runtime', 'ST4')
# EGL_DEPTH_SIZE 와 최소 깊이. 16 이면 어느 기기에나 있다.
DEPTH = ('0x3025', '0x10')


def _java():
    for c in ('java', os.path.join(os.environ.get('JAVA_HOME', ''), 'bin', 'java')):
        if shutil.which(c):
            return shutil.which(c)
    raise SystemExit('java 를 못 찾았습니다')


def _cp():
    miss = [n for n in NEED if not os.path.exists(os.path.join(JARS, n + '.jar'))]
    if miss:
        raise SystemExit('tools/jars 에 없는 것: %s\n'
                         '메이븐에서 받으세요: '
                         'https://repo1.maven.org/maven2/org/smali/' % ', '.join(miss))
    sep = ';' if os.name == 'nt' else ':'
    return sep.join(os.path.join(JARS, n + '.jar') for n in NEED)


def _run(args):
    r = subprocess.run(args, capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    if r.returncode != 0:
        sys.stderr.write((r.stdout or '') + (r.stderr or ''))
        raise SystemExit('실패: %s' % args[-3:])
    return r


def _find_chooser(root):
    """`eglChooseConfig` 를 부르는 클래스를 찾는다. 이름은 난독화되어 있다."""
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            if not f.endswith('.smali'):
                continue
            p = os.path.join(dirpath, f)
            with open(p, encoding='utf-8') as fh:
                s = fh.read()
            if 'eglChooseConfig' in s and '.array-data 4' in s:
                return p, s
    return None, None


ARRAY = re.compile(r'(\n    :array_[0-9a-f]+\n    \.array-data 4\n)'
                   r'((?:        0x[0-9a-f]+\n)+)')


def _patch_text(s):
    """조건 배열마다 EGL_DEPTH_SIZE 를 끼워 넣고 배열 길이를 늘린다."""
    blocks = list(ARRAY.finditer(s))
    if not blocks:
        raise SystemExit('조건 배열을 못 찾았습니다')
    lens = set()
    for m in blocks:
        n = len(m.group(2).strip().splitlines())
        lens.add(n)
        if DEPTH[0] in m.group(2):
            return None, n          # 이미 고쳐져 있다
    if len(lens) != 1:
        raise SystemExit('조건 배열들의 길이가 다릅니다: %s' % lens)
    old = lens.pop()

    def fix(m):
        head, body = m.group(1), m.group(2)
        return head + body.replace('        0x3038\n',
                                   '        %s\n        %s\n        0x3038\n'
                                   % DEPTH)

    s2 = ARRAY.sub(fix, s)
    # `new-array v?, vN, [I` 에 쓰이는 길이 상수를 늘린다
    hit = 'const/16 v3, 0x%x' % old
    if s2.count(hit) != 1:
        raise SystemExit('배열 길이 상수(%s)를 정확히 못 짚었습니다' % hit)
    s2 = s2.replace(hit, 'const/16 v3, 0x%x' % (old + 2))
    return s2, old


def check():
    java, cp = _java(), _cp()
    shutil.rmtree(WORK, ignore_errors=True)
    _run([java, '-cp', cp, 'org.jf.baksmali.Main', 'd', DEX, '-o', WORK])
    p, s = _find_chooser(WORK)
    if p is None:
        print('EGL 설정 고르는 클래스를 못 찾았습니다')
        return 1
    print('  설정 고르는 클래스: %s' % os.path.relpath(p, WORK))
    for m in ARRAY.finditer(s):
        vals = [v.strip() for v in m.group(2).strip().splitlines()]
        mark = ' <- 깊이 요구 있음' if DEPTH[0] in vals else ' <- **깊이 요구 없음**'
        print('    조건 %d개 %s%s' % (len(vals), vals, mark))
    return 0


def apply():
    java, cp = _java(), _cp()
    shutil.rmtree(WORK, ignore_errors=True)
    _run([java, '-cp', cp, 'org.jf.baksmali.Main', 'd', DEX, '-o', WORK])
    p, s = _find_chooser(WORK)
    if p is None:
        raise SystemExit('EGL 설정 고르는 클래스를 못 찾았습니다')
    s2, old = _patch_text(s)
    if s2 is None:
        print('  이미 고쳐져 있습니다 (조건 %d개)' % old)
        return 0
    with open(p, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(s2)
    print('  %s : 조건 %d개 -> %d개 (EGL_DEPTH_SIZE 16 추가)'
          % (os.path.relpath(p, WORK), old, old + 2))

    os.makedirs(os.path.dirname(BAK), exist_ok=True)
    if not os.path.exists(BAK):
        shutil.copy2(DEX, BAK)
        print('  원본을 남겨 둠: backup/dex/classes.dex')
    out = os.path.join(HERE, '_scratch', 'classes_egl.dex')
    _run([java, '-cp', cp, 'org.jf.smali.Main', 'a', WORK, '-o', out])
    before, after = os.path.getsize(DEX), os.path.getsize(out)
    shutil.copy2(out, DEX)
    print('  classes.dex %d -> %d 바이트' % (before, after))
    return 0


def restore():
    if not os.path.exists(BAK):
        raise SystemExit('남겨 둔 원본이 없습니다: %s' % BAK)
    shutil.copy2(BAK, DEX)
    print('  원래대로 돌렸습니다')
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--restore', action='store_true')
    a = ap.parse_args()
    if a.check:
        return check()
    if a.restore:
        return restore()
    return apply()


if __name__ == '__main__':
    sys.exit(main())
