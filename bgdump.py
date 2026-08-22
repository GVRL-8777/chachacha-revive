# -*- coding: utf-8 -*-
"""8.apk 의 Background MonoBehaviour 를 직렬화 규칙대로 직접 읽는다.
   유니티는 public 직렬화 가능 필드만 저장한다 (ArrayList/private 제외)."""
import UnityPy, struct, os, sys

path, pid = sys.argv[1], int(sys.argv[2])
env = UnityPy.load(path)
obj = env.assets_file.objects[pid] if hasattr(env, 'assets_file') else None
if obj is None:
    for r in env.objects:
        if r.path_id == pid:
            obj = r
raw = obj.get_raw_data()
p = 0
def i32():
    global p
    v = struct.unpack_from("<i", raw, p)[0]; p += 4; return v
def f32():
    global p
    v = struct.unpack_from("<f", raw, p)[0]; p += 4; return v
def align():
    global p
    p = (p + 3) & ~3
def s():
    global p
    n = i32(); v = raw[p:p+n].decode("utf-8", "replace"); p += n; align(); return v
def pptr():
    return (i32(), i32())

print("길이 %d바이트" % len(raw))
print("m_GameObject", pptr(), " m_Enabled", i32(), " m_Script", pptr())
print("m_Name '%s'" % s())
print("mapAttachedObject", pptr())
n = i32(); print("mapThemeOrder %d개:" % n)
for k in range(n):
    nm = s(); lc = i32()
    print("   [%d] themeName='%s'  loopCount=%d" % (k, nm, lc))
n = i32(); print("tunnelMap %d개:" % n)
for k in range(n):
    print("   ", pptr())
tun = raw[p]; p += 1; align(); print("isTunnel", bool(tun))
print("groundParticlePrefab", pptr())
print("lineSpace", f32())
print("남은 바이트", len(raw) - p)
