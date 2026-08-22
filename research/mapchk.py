# -*- coding: utf-8 -*-
"""이식 대상 맵 프리팹이 어떤 컴포넌트로 이루어졌는지 본다.

엔진 타입(GameObject/Transform/MeshFilter/MeshRenderer/Mesh/Material/Texture2D)만으로
되어 있으면 자산 파일을 그대로 옮기는 방식이 가능하다.
MonoBehaviour(게임 스크립트)가 섞여 있으면 빌드마다 스크립트 참조가 달라 깨진다.
"""
import os, sys, collections, UnityPy

SRC = 'survey/gogogoracer-1-4-3/assets/bin/Data'
WANT = sys.argv[1] if len(sys.argv) > 1 else 'data_gbridge01'

for f in sorted(os.listdir(SRC)):
    p = os.path.join(SRC, f)
    if not os.path.isfile(p):
        continue
    try:
        env = UnityPy.load(p)
    except Exception:
        continue
    names = {}
    hit = False
    for r in env.objects:
        if r.type.name != 'GameObject':
            continue
        try:
            o = r.read()
        except Exception:
            continue
        if (o.m_Name or '') == WANT:
            hit = True
            break
    if not hit:
        continue
    print("파일: %s (%.1f KB)" % (f, os.path.getsize(p) / 1024))
    c = collections.Counter(r.type.name for r in env.objects)
    print("  구성:", dict(c.most_common(12)))
    mb = [r for r in env.objects if r.type.name == 'MonoBehaviour']
    print("  MonoBehaviour %d개  -> %s" % (
        len(mb), "엔진 타입만 (파일 이식 가능)" if not mb else "스크립트 포함 (재구성 필요)"))
    # 메시 규모
    for r in env.objects:
        if r.type.name == 'Mesh':
            try:
                m = r.read()
                obj = m.export()
                print("  메시 %-24s 정점 %d / 면 %d"
                      % (m.m_Name, obj.count('\nv '), obj.count('\nf ')))
            except Exception as e:
                print("  메시 읽기 실패:", type(e).__name__)
    break
else:
    print("%s 를 가진 파일을 찾지 못함" % WANT)
