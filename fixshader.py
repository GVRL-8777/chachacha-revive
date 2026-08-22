# -*- coding: utf-8 -*-
"""이식한 머티리얼의 셰이더 참조를 대상 배포판에 맞게 고친다.

내장 셰이더 파일(0000000000000000f000...)의 내용이 배포판마다 다르다.
  gogogoracer: pathID 1=Mobile-Lightmap-Unlit, 2=Unlit-AlphaTest
  중국판     : pathID 1=Mobile-Lightmap-Unlit, 2=Mobile-Particle-Alpha
따라서 pathID 2 를 가리키는 머티리얼은 엉뚱한 셰이더를 물게 된다.
맵 재질은 라이트맵이 구워진 아틀라스 방식이라 1번(Mobile-Lightmap-Unlit)으로 통일한다.

바이너리를 직접 고친다. UnityPy 로 재저장하면 파일이 손상되므로,
머티리얼 안의 셰이더 PPtr(fileID,pathID) 위치를 찾아 pathID 값만 바꾼다.
"""
import os, sys, struct, shutil, UnityPy

OVL = 'overlay'
targets = sys.argv[1:] if len(sys.argv) > 1 else None

for fn in sorted(os.listdir(OVL)):
    p = os.path.join(OVL, fn)
    if not os.path.isfile(p):
        continue
    try:
        env = UnityPy.load(p)
    except Exception:
        continue
    mats = [r for r in env.objects if r.type.name == 'Material']
    if not mats:
        continue
    for r in mats:
        m = r.read()
        sh = getattr(m, 'm_Shader', None)
        fid = getattr(sh, 'file_id', None)
        pid = getattr(sh, 'path_id', None)
        print("%s : %s  셰이더 fileID=%s pathID=%s" % (fn[:16], m.m_Name, fid, pid))
        if pid == 1:
            print("   그대로 둔다 (Mobile-Lightmap-Unlit)")
            continue
        raw = r.get_raw_data()
        # 머티리얼 레이아웃: m_Name(문자열) 다음에 m_Shader PPtr(int fileID, int pathID)
        want = struct.pack('<ii', fid, pid)
        idx = raw.find(want)
        if idx < 0:
            print("   셰이더 PPtr 위치를 찾지 못함 -> 건너뜀")
            continue
        newraw = bytearray(raw)
        struct.pack_into('<ii', newraw, idx, fid, 1)
        # 파일 안에서 이 오브젝트의 시작 오프셋을 찾아 그 자리에 덮어쓴다
        blob = open(p, 'rb').read()
        at = blob.find(raw)
        if at < 0:
            print("   파일에서 오브젝트 바이트를 찾지 못함 -> 건너뜀")
            continue
        out = bytearray(blob)
        out[at:at + len(raw)] = bytes(newraw)
        shutil.copy(p, p + '.bak')
        open(p, 'wb').write(bytes(out))
        print("   pathID %s -> 1 로 수정 (오프셋 %d)" % (pid, at + idx))

# 확인
print()
for fn in sorted(os.listdir(OVL)):
    if fn.endswith('.bak'):
        continue
    p = os.path.join(OVL, fn)
    try:
        env = UnityPy.load(p)
    except Exception:
        continue
    for r in env.objects:
        if r.type.name != 'Material':
            continue
        m = r.read()
        print("확인 %s : %s -> pathID=%s"
              % (fn[:16], m.m_Name, getattr(m.m_Shader, 'path_id', None)))
