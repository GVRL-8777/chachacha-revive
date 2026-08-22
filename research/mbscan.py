# -*- coding: utf-8 -*-
"""MonoBehaviour 헤더를 직접 읽어 스크립트 클래스로 찾는다.
   레이아웃(Unity 3.5/4.1): m_GameObject PPtr(int fileID,int pathID) | m_Enabled int32 | m_Script PPtr
   m_Script 의 fileID 가 0 이 아니면 externals[fileID-1] 의 파일을 가리킨다."""
import sys, os, struct, UnityPy

folder = sys.argv[1]
want = set(s.lower() for s in sys.argv[2:])

files = {}
for root, _, fs in os.walk(folder):
    for f in fs:
        try:
            files[f.lower()] = UnityPy.load(os.path.join(root, f))
        except Exception:
            pass

# 모든 MonoScript 를 (파일, pathId) -> 클래스명 으로 색인
scripts = {}
for name, env in files.items():
    for r in env.objects:
        if r.type.name == "MonoScript":
            try:
                scripts[(name, r.path_id)] = r.read().m_ClassName
            except Exception:
                pass

def ext_name(af, fid):
    try:
        return os.path.basename(af.externals[fid - 1].path).lower()
    except Exception:
        return None

hits = {}
for name, env in files.items():
    for r in env.objects:
        if r.type.name != "MonoBehaviour":
            continue
        try:
            raw = r.get_raw_data()
            if len(raw) < 20:
                continue
            go_pid, sc_fid, sc_pid = struct.unpack_from("<i", raw, 4)[0], \
                                     struct.unpack_from("<i", raw, 12)[0], \
                                     struct.unpack_from("<i", raw, 16)[0]
            key = (name if sc_fid == 0 else ext_name(r.assets_file, sc_fid), sc_pid)
            cls = scripts.get(key)
            if cls and cls.lower() in want:
                hits.setdefault(cls, []).append((name, r.path_id, go_pid))
        except Exception:
            continue

for c in sorted(hits):
    print("%s: %d개" % (c, len(hits[c])))
    for f, pid, gopid in hits[c][:8]:
        print("   파일=%-16s pathId=%-8s GO=%s" % (f[:16], pid, gopid))
if not hits:
    print("(없음)")
