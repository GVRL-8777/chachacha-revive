# -*- coding: utf-8 -*-
"""두 APK 의 직렬화 자산에서 이름에 Background/Map 이 들어간 오브젝트를 찾는다."""
import sys, os, UnityPy

d = sys.argv[1]
pat = [s.lower() for s in sys.argv[2:]] or ["background"]
hits = {}
ver = set()
for root, _, files in os.walk(d):
    for f in files:
        p = os.path.join(root, f)
        try:
            env = UnityPy.load(p)
        except Exception:
            continue
        for r in env.objects:
            try:
                ver.add(r.assets_file.unity_version)
            except Exception:
                pass
            try:
                if r.type.name not in ("GameObject", "MonoBehaviour", "Transform"):
                    continue
                o = r.read()
                nm = getattr(o, "m_Name", "") or ""
                if not nm and r.type.name == "MonoBehaviour":
                    continue
                if any(s in nm.lower() for s in pat):
                    hits.setdefault(nm, []).append((r.type.name, f))
            except Exception:
                continue
print("유니티 버전:", sorted(ver)[:3])
for k in sorted(hits):
    kinds = sorted(set(t for t, _ in hits[k]))
    print("  %-40s %s  (%d건, 예: %s)" % (k, ",".join(kinds), len(hits[k]), hits[k][0][1][:12]))
