# -*- coding: utf-8 -*-
"""MonoBehaviour 를 스크립트 클래스 이름으로 찾는다 (붙어 있는 GameObject 이름도 함께)."""
import sys, os, UnityPy
d, want = sys.argv[1], set(s.lower() for s in sys.argv[2:])
found = {}
for root, _, files in os.walk(d):
    for f in files:
        p = os.path.join(root, f)
        try:
            env = UnityPy.load(p)
        except Exception:
            continue
        for r in env.objects:
            if r.type.name != "MonoBehaviour":
                continue
            try:
                o = r.read()
                sc = o.m_Script.read()
                cls = sc.m_ClassName
                if cls.lower() not in want:
                    continue
                try:
                    go = o.m_GameObject.read().m_Name
                except Exception:
                    go = "?"
                found.setdefault(cls, []).append((f, go, r.path_id))
            except Exception:
                continue
for c in sorted(found):
    print("%s: %d개" % (c, len(found[c])))
    for f, go, pid in found[c][:6]:
        print("   파일=%s  GameObject=%s  pathId=%s" % (f[:14], go, pid))
