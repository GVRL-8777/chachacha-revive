# -*- coding: utf-8 -*-
"""
x77/ 작업 트리를 기준 APK 위에 덮어 다시 묶는다.

기준 APK(rec/installed.apk)의 엔트리 순서와 압축 방식을 그대로 두고,
x77/ 안에서 내용이 달라진 것만 교체하고 새로 생긴 것은 추가한다.
서명은 호출부에서 jarsigner 로 다시 한다.

  python pack.py [기준.apk] [출력.apk] [작업트리]
"""
import os, sys, zipfile

BASE = sys.argv[1] if len(sys.argv) > 1 else "rec/installed.apk"
OUT  = sys.argv[2] if len(sys.argv) > 2 else "chacn.apk"
TREE = sys.argv[3] if len(sys.argv) > 3 else "x77"

zin = zipfile.ZipFile(BASE)
infos = zin.infolist()
known = set(i.filename for i in infos)

# 작업 트리의 모든 파일
tree = {}
for root, _dirs, fs in os.walk(TREE):
    for f in fs:
        p = os.path.join(root, f)
        rel = os.path.relpath(p, TREE).replace("\\", "/")
        tree[rel] = p

if os.path.exists(OUT):
    os.remove(OUT)
zout = zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED)

changed = added = same = dropped = 0
for info in infos:
    n = info.filename
    if n.startswith("META-INF/") and (
            n.upper().endswith((".SF", ".RSA", ".DSA", ".EC"))
            or n == "META-INF/MANIFEST.MF"):
        continue
    if n in tree:
        data = open(tree[n], "rb").read()
        if data != zin.read(n):
            zout.writestr(info, data, info.compress_type)
            changed += 1
        else:
            zout.writestr(info, zin.read(n), info.compress_type)
            same += 1
    else:
        # 작업 트리에서 지운 파일은 빼 버린다
        dropped += 1
for rel in sorted(tree):
    if rel in known:
        continue
    zout.writestr(rel, open(tree[rel], "rb").read(), zipfile.ZIP_DEFLATED)
    added += 1
zout.close(); zin.close()
print("교체 %d / 추가 %d / 삭제 %d / 그대로 %d -> %s (%.1f MB)"
      % (changed, added, dropped, same, OUT, os.path.getsize(OUT) / 1048576.0))
