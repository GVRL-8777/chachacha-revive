# -*- coding: utf-8 -*-
"""교체 가능한 (소스 맵 -> CN 맵) 짝을 찾는다.

Resources.Load 는 경로로 자산을 찾고, 게임은 GameObject 를 받는다.
따라서 **소스 파일의 GameObject pathID 가 대상의 GameObject pathID 와 같으면**
파일을 덮어써도 색인이 그대로 맞아떨어진다.
"""
import os, sys, UnityPy, collections

CN = 'survey/5577.com.cjenm.chachachacn/assets/bin/Data'
GO = 'survey/gogogoracer-1-4-3/assets/bin/Data'


def index(data_dir, prefix):
    env = UnityPy.load(os.path.join(data_dir, 'mainData'))
    rm = [r for r in env.objects if r.type.name == "ResourceManager"][0].read()
    af = env.objects[0].assets_file
    out = {}
    for p, ptr in rm.m_Container:
        if not p.startswith(prefix):
            continue
        fid = getattr(ptr, 'file_id', None)
        if fid is None:
            continue
        out.setdefault(p, set()).add(os.path.basename(af.externals[fid - 1].path))
    return out


def go_pathid(data_dir, fname):
    """파일 안에서 '루트 GameObject' 의 pathID 를 찾는다(자식이 아닌 것 우선)."""
    p = os.path.join(data_dir, fname)
    if not os.path.isfile(p):
        return None, None, 0
    try:
        env = UnityPy.load(p)
    except Exception:
        return None, None, 0
    gos = [r for r in env.objects if r.type.name == 'GameObject']
    if not gos:
        return None, None, len(env.objects)
    best = None
    for r in gos:
        try:
            nm = r.read().m_Name
        except Exception:
            nm = ''
        if best is None or r.path_id < best[0]:
            best = (r.path_id, nm)
    return best[0], best[1], len(env.objects)


want = sys.argv[1] if len(sys.argv) > 1 else 'map/greece/'
cn = index(CN, 'background/')
go = index(GO, want)

cn_info = {}
for p, files in cn.items():
    if p.endswith(('completemap', 'completemap_low', '_low')) or 'materials/' in p:
        continue
    f = sorted(files)[0]
    pid, nm, n = go_pathid(CN, f)
    if pid is not None:
        cn_info[p] = (f, pid, nm, n)

print("=== CN 맵 프리팹 (교체 대상 후보) ===")
for p in sorted(cn_info):
    f, pid, nm, n = cn_info[p]
    print("  %-34s GO pathID=%-3s 오브젝트 %-4s %s" % (p, pid, n, nm))

print()
print("=== %s 소스 후보 ===" % want)
rows = []
for p, files in sorted(go.items()):
    if p.endswith(('completemap', 'completemap_low', '_low')) or 'materials/' in p:
        continue
    f = sorted(files)[0]
    pid, nm, n = go_pathid(GO, f)
    if pid is None:
        continue
    rows.append((p, f, pid, nm, n))
    print("  %-46s GO pathID=%-3s 오브젝트 %-4s %s" % (p, pid, n, nm))

print()
print("=== 교체 가능한 짝 (GO pathID 일치) ===")
cnt = 0
for p, f, pid, nm, n in rows:
    for cp, (cf, cpid, cnm, cn_n) in sorted(cn_info.items()):
        if cpid == pid:
            print("  %-44s -> %-30s (pathID %s)" % (p, cp, pid))
            cnt += 1
            break
print("  총 %d개 조합 가능" % cnt)
