# -*- coding: utf-8 -*-
"""배포판 사이에 자산을 이식한다 (색인을 건드리지 않는 '파일 교체' 방식).

배경:
  · mainData 의 ResourceManager 는 `경로 -> (fileID, pathID)` 색인을 들고 있는데,
    UnityPy 로 재작성하면 파일이 손상된다(검증 완료). 그래서 색인은 손대지 않는다.
  · 대신 색인이 이미 가리키고 있는 **대상 파일을 소스 파일로 덮어쓴다**.
    이러면 경로는 그대로인데 내용물이 바뀐다. pathID 구성이 같아야 한다.
  · 자산이 참조하는 재질/텍스처 등 의존 파일은 **파일 이름으로** 해석되므로,
    같은 이름으로 복사해 넣기만 하면 된다(색인 등록 불필요).

사용법:
  python xplant.py plan  <소스Data> <대상Data> <소스경로> <대상경로>
  python xplant.py apply <소스Data> <대상Data> <소스경로> <대상경로> [출력Data]
"""
import os, sys, shutil, UnityPy


def load_index(data_dir):
    env = UnityPy.load(os.path.join(data_dir, 'mainData'))
    rm = [r for r in env.objects if r.type.name == "ResourceManager"][0].read()
    af = env.objects[0].assets_file
    idx = {}
    for p, ptr in rm.m_Container:
        fid = getattr(ptr, 'file_id', None)
        pid = getattr(ptr, 'path_id', None)
        if fid is None:
            continue
        name = os.path.basename(af.externals[fid - 1].path)
        idx.setdefault(p, {"file": name, "pathids": []})
        idx[p]["pathids"].append(pid)
    return idx


def file_deps(data_dir, fname, seen=None):
    """파일이 externals 로 참조하는 파일들을 재귀적으로 모은다."""
    if seen is None:
        seen = set()
    if fname in seen:
        return seen
    seen.add(fname)
    p = os.path.join(data_dir, fname)
    if not os.path.isfile(p):
        return seen
    try:
        env = UnityPy.load(p)
    except Exception:
        return seen
    if not env.objects:
        return seen
    af = env.objects[0].assets_file
    for e in getattr(af, 'externals', []):
        n = os.path.basename(e.path)
        if n and n not in seen and os.path.isfile(os.path.join(data_dir, n)):
            file_deps(data_dir, n, seen)
    return seen


def describe(data_dir, fname):
    p = os.path.join(data_dir, fname)
    try:
        env = UnityPy.load(p)
    except Exception as e:
        return "(열기 실패 %s)" % type(e).__name__
    kinds = {}
    for r in env.objects:
        kinds[r.type.name] = kinds.get(r.type.name, 0) + 1
    return "%s (%.1f KB) %s" % (fname[:16], os.path.getsize(p) / 1024, kinds)


def main():
    mode = sys.argv[1]
    src_dir, dst_dir = sys.argv[2], sys.argv[3]
    src_path, dst_path = sys.argv[4], sys.argv[5]

    si = load_index(src_dir)
    di = load_index(dst_dir)
    if src_path not in si:
        raise SystemExit("소스 경로 없음: " + src_path)
    if dst_path not in di:
        raise SystemExit("대상 경로 없음: " + dst_path)
    s, d = si[src_path], di[dst_path]

    print("소스 %s" % src_path)
    print("   파일=%s  pathIDs=%s" % (s['file'][:20], sorted(s['pathids'])))
    print("   %s" % describe(src_dir, s['file']))
    print("대상 %s" % dst_path)
    print("   파일=%s  pathIDs=%s" % (d['file'][:20], sorted(d['pathids'])))
    print("   %s" % describe(dst_dir, d['file']))

    ok = sorted(s['pathids']) == sorted(d['pathids'])
    print("pathID 일치: %s" % ("예" % () if ok else "아니오 -> 이 조합은 교체 불가"))

    deps = file_deps(src_dir, s['file'])
    deps.discard(s['file'])
    print("의존 파일 %d개" % len(deps))
    conflict = [n for n in deps if os.path.exists(os.path.join(dst_dir, n))]
    print("   대상에 이미 있는 이름: %d개 (덮어쓰지 않는다)" % len(conflict))

    if mode != 'apply':
        return
    if not ok:
        raise SystemExit("pathID 불일치로 중단")

    out_dir = sys.argv[6] if len(sys.argv) > 6 else dst_dir
    if out_dir != dst_dir and not os.path.isdir(out_dir):
        shutil.copytree(dst_dir, out_dir)

    shutil.copy(os.path.join(src_dir, s['file']), os.path.join(out_dir, d['file']))
    print("교체: %s <- %s" % (d['file'][:16], s['file'][:16]))
    n = 0
    for name in sorted(deps):
        tgt = os.path.join(out_dir, name)
        if os.path.exists(tgt):
            continue
        shutil.copy(os.path.join(src_dir, name), tgt)
        n += 1
    print("의존 파일 %d개 복사" % n)


main()
