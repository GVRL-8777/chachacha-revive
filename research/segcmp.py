# -*- coding: utf-8 -*-
"""맵 세그먼트의 트랜스폼과 메시 크기를 배포판 간에 비교한다.

이식한 그리스 세그먼트가 차 밑에 오지 않는 원인을 찾기 위한 것.
중국판 자신의 세그먼트와 나란히 놓고 위치/회전/스케일/바운드를 본다.
"""
import os, sys, UnityPy


def index(data_dir):
    env = UnityPy.load(os.path.join(data_dir, 'mainData'))
    rm = [r for r in env.objects if r.type.name == "ResourceManager"][0].read()
    af = env.objects[0].assets_file
    out = {}
    for p, ptr in rm.m_Container:
        fid = getattr(ptr, 'file_id', None)
        pid = getattr(ptr, 'path_id', None)
        if fid is None:
            continue
        out.setdefault(p, []).append((os.path.basename(af.externals[fid - 1].path), pid))
    return out


def show(data_dir, res_path, label):
    idx = index(data_dir)
    if res_path not in idx:
        print("%s: 경로 없음 %s" % (label, res_path))
        return
    fname = idx[res_path][0][0]
    from UnityPy.streams import EndianBinaryReader
    from UnityPy.files.SerializedFile import SerializedFile
    sf = SerializedFile(EndianBinaryReader(
        open(os.path.join(data_dir, fname), 'rb').read()), None)
    print("=== %s : %s (%s)" % (label, res_path, fname[:16]))
    for pid, o in sorted(sf.objects.items()):
        t = None
        try:
            t = o.read_typetree()
        except Exception:
            continue
        if o.type.name == 'Transform':
            print("   Transform pathID=%s pos=%s rot=%s scale=%s 부모=%s 자식=%d"
                  % (pid,
                     tuple(round(v, 3) for v in t['m_LocalPosition'].values()),
                     tuple(round(v, 3) for v in t['m_LocalRotation'].values()),
                     tuple(round(v, 3) for v in t['m_LocalScale'].values()),
                     t['m_Father']['m_PathID'], len(t.get('m_Children', []))))
        elif o.type.name == 'GameObject':
            print("   GameObject pathID=%s name=%r 컴포넌트=%d"
                  % (pid, t.get('m_Name'), len(t.get('m_Component', []))))
        elif o.type.name == 'Mesh':
            aabb = t.get('m_LocalAABB')
            if aabb:
                c = aabb['m_Center']; e = aabb['m_Extent']
                print("   Mesh pathID=%s 중심=%s 반경=%s (길이 z=%.1f, 폭 x=%.1f)"
                      % (pid,
                         tuple(round(v, 2) for v in c.values()),
                         tuple(round(v, 2) for v in e.values()),
                         e['z'] * 2, e['x'] * 2))
        elif o.type.name == 'MeshFilter':
            print("   MeshFilter pathID=%s -> mesh %s" % (pid, t['m_Mesh']))


CN = 'survey/5577.com.cjenm.chachachacn/assets/bin/Data'
GO = 'survey/gogogoracer-1-4-3/assets/bin/Data'
show(CN, sys.argv[1] if len(sys.argv) > 1 else 'background/beach01', '중국판')
print()
show(GO, sys.argv[2] if len(sys.argv) > 2 else 'map/greece/gbeach/gbeach01', 'gogogoracer')
