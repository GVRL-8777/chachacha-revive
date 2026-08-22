# -*- coding: utf-8 -*-
"""mainData 의 externals(외부 파일 참조) 목록을 들여다보고 추가가 가능한지 본다."""
import os, shutil, UnityPy

SRC = 'survey/5577.com.cjenm.chachachacn/assets/bin/Data/mainData'
TMP = 'xtest_mainData'
shutil.copy(SRC, TMP)

env = UnityPy.load(TMP)
af = env.file if hasattr(env.file, 'externals') else env.objects[0].assets_file
print("타입:", type(af).__name__)
print("externals %d개" % len(af.externals))
for i, e in enumerate(af.externals[:5]):
    print("  [%d] path=%r" % (i + 1, e.path))
    for a in dir(e):
        if a.startswith('_'):
            continue
        v = getattr(e, a, None)
        if callable(v):
            continue
        print("        %-12s %r" % (a, v))
    break

# 새 external 추가 시도 (기존 항목을 복제해 경로만 바꾼다)
import copy
try:
    ne = copy.deepcopy(af.externals[0])
    ne.path = "bba96ef597fd90b42b4c3e5017ce0de3"
    af.externals.append(ne)
    print("추가 후 externals %d개" % len(af.externals))
    with open(TMP, 'wb') as f:
        f.write(env.file.save())
    print("저장 성공 (%.1f KB)" % (os.path.getsize(TMP) / 1024))
    env2 = UnityPy.load(TMP)
    af2 = env2.file if hasattr(env2.file, 'externals') else env2.objects[0].assets_file
    print("재읽기 externals %d개, 마지막=%r" % (len(af2.externals), af2.externals[-1].path))
except Exception as e:
    print("실패:", type(e).__name__, e)
