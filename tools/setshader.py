# -*- coding: utf-8 -*-
"""재질이 가리키는 셰이더를 다른 것으로 갈아 끼운다.

왜 필요한가. 차 재질은 `Normal-DiffuseFast` 를 쓰는데, 이 셰이더는 **본체가
없는 껍데기**다. 속성만 있고 `Fallback "VertexLit"` 한 줄이 전부다. 그래서
실제로는 `Normal-VertexLit` 으로 그려지는데, 그쪽 첫 SubShader 는 셰이더
프로그램이 아니라 **고정 기능**(Lighting On + SetTexture combine)이다.

유니티 4 는 고정 기능을 실행 중에 GLSL 로 흉내 내는데, 그 경로가 요즘 Mali
드라이버에서 죽는다. Adreno 에서는 멀쩡한데 Mali 에서 차가 검게 나오는
까닭이 이것이다. `Normal-Diffuse` 는 SubProgram 28개를 갖춘 진짜 프로그램
셰이더라 그쪽으로 돌리면 살아난다.

    python tools/setshader.py --like aveo --to 7
    python tools/setshader.py --list                 어떤 셰이더가 있는지
    python tools/setshader.py --survey               어느 재질이 무엇을 쓰는지

PPtr 은 크기가 고정이라 레코드 길이가 안 변한다. 그래서 파일을 통째로 다시
쓰지 않고 그 자리만 덮어쓴다.
"""
import argparse
import io
import os
import sys

CODE = os.path.dirname(os.path.abspath(__file__))
# 도구는 tools/ 안에 있고, 작업 트리(x77 · saves · lang …)는 그 위에 있다.
HERE = os.path.dirname(CODE)
sys.path.insert(0, CODE)

DATA = os.path.join('assets', 'bin', 'Data')
BUILTIN = 'unity default resources'


def _files(tree):
    root = os.path.join(tree, DATA)
    for name in sorted(os.listdir(root)):
        p = os.path.join(root, name)
        if os.path.isfile(p) and os.path.getsize(p) >= 512:
            yield name, p


def shaders(tree):
    """내장 셰이더 목록 — 이름 -> (pathID, 프로그램 수, 고정기능 수)"""
    import UnityPy
    p = os.path.join(tree, DATA, BUILTIN)
    out = {}
    if not os.path.exists(p):
        return out
    for o in UnityPy.load(p).objects:
        if o.type.name != 'Shader':
            continue
        try:
            t = o.read_typetree()
        except Exception:
            continue
        s = t.get('m_Script') or ''
        if isinstance(s, (bytes, bytearray)):
            s = bytes(s).decode('utf-8', 'replace')
        out[t.get('m_Name', '?')] = (o.path_id, s.count('SubProgram "'),
                                     s.count('SetTexture'))
    return out


def survey(tree, like=None):
    """재질 -> 지금 가리키는 셰이더 (fileID, pathID)"""
    import UnityPy
    rows = []
    for name, p in _files(tree):
        try:
            env = UnityPy.load(p)
        except Exception:
            continue
        for o in env.objects:
            if o.type.name != 'Material':
                continue
            try:
                t = o.read_typetree()
            except Exception:
                continue
            nm = t.get('m_Name') or ''
            if like and like.lower() not in nm.lower():
                continue
            sh = t.get('m_Shader') or {}
            rows.append((nm, name, o.path_id,
                         sh.get('m_FileID'), sh.get('m_PathID')))
    return rows


def repoint(tree, like, to_path, to_file=None, dry=False):
    """이름에 `like` 가 든 재질의 셰이더를 pathID `to_path` 로 돌린다."""
    import UnityPy
    from sfparse import parse
    done, skipped = 0, 0
    for name, p in _files(tree):
        try:
            env = UnityPy.load(p)
        except Exception:
            continue
        edits = []
        for o in env.objects:
            if o.type.name != 'Material':
                continue
            try:
                t = o.read_typetree()
            except Exception:
                continue
            nm = t.get('m_Name') or ''
            if like.lower() not in nm.lower():
                continue
            sh = dict(t.get('m_Shader') or {})
            if sh.get('m_PathID') == to_path and (to_file is None
                                                  or sh.get('m_FileID') == to_file):
                continue
            old = (sh.get('m_FileID'), sh.get('m_PathID'))
            sh['m_PathID'] = to_path
            if to_file is not None:
                sh['m_FileID'] = to_file
            t['m_Shader'] = sh
            edits.append((o, nm, old, t))
        if not edits:
            continue
        meta = parse(p)
        raw = bytearray(io.open(p, 'rb').read())
        touched = False
        for o, nm, old, t in edits:
            new = bytes(o.save_typetree(t))
            rec = [x for x in meta['objects'] if x['path_id'] == o.path_id][0]
            if len(new) != rec['size']:
                print('  건너뜀 %-24s 길이가 달라짐 (%d -> %d)'
                      % (nm, rec['size'], len(new)))
                skipped += 1
                continue
            st = meta['data_offset'] + rec['start']
            raw[st:st + len(new)] = new
            touched = True
            done += 1
            print('  %-26s %s -> (%s, %s)   [%s]'
                  % (nm, old, to_file if to_file is not None else old[0],
                     to_path, name[:14]))
        if touched and not dry:
            io.open(p, 'wb').write(bytes(raw))
    return done, skipped


def main():
    ap = argparse.ArgumentParser(description='재질의 셰이더를 갈아 끼운다')
    ap.add_argument('--tree', default=os.path.join(HERE, 'x77'))
    ap.add_argument('--list', action='store_true', help='내장 셰이더 목록')
    ap.add_argument('--survey', action='store_true', help='재질이 무엇을 쓰는지')
    ap.add_argument('--like', help='이름에 이 말이 든 재질만')
    ap.add_argument('--to', type=int, help='바꿀 셰이더의 pathID')
    ap.add_argument('--to-file', type=int, default=None, help='바꿀 셰이더의 fileID')
    ap.add_argument('--dry', action='store_true', help='쓰지 않고 보기만')
    a = ap.parse_args()

    if a.list:
        sh = shaders(a.tree)
        print('  %-30s %8s %9s %10s' % ('이름', 'pathID', 'Program', 'SetTexture'))
        for nm in sorted(sh):
            pid, sp, st = sh[nm]
            mark = '   <- 껍데기' if sp == 0 and st == 0 else (
                '   <- 고정기능' if st else '')
            print('  %-30s %8s %9d %10d%s' % (nm, pid, sp, st, mark))
        return 0

    if a.survey:
        rows = survey(a.tree, a.like)
        print('  재질 %d개' % len(rows))
        for nm, f, pid, fid, spid in rows[:80]:
            print('  %-28s [%s] pathID=%-6s -> 셰이더 (fileID=%s, pathID=%s)'
                  % (nm, f[:14], pid, fid, spid))
        return 0

    if not (a.like and a.to):
        ap.error('--like 와 --to 를 함께 주세요 (또는 --list / --survey)')
    done, skipped = repoint(a.tree, a.like, a.to, a.to_file, a.dry)
    print('바꾼 재질 %d개%s' % (done, ' · 건너뜀 %d개' % skipped if skipped else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
