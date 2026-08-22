# -*- coding: utf-8 -*-
"""양쪽 맵 자산의 (파일, pathID) 를 대조한다.

mainData 재작성이 불가능하므로, '기존 CN 자산 파일을 소스 파일로 덮어쓰는' 방식이
가능한지 본다. 이 방식은 색인을 건드리지 않으므로 **pathID 가 일치해야** 한다.
의존 파일(재질/텍스처)은 파일 이름으로 해결되므로 그냥 복사하면 된다.
"""
import os, UnityPy

def index_of(data_dir, prefix):
    env = UnityPy.load(os.path.join(data_dir, 'mainData'))
    rm = [r for r in env.objects if r.type.name == "ResourceManager"][0].read()
    af = env.objects[0].assets_file
    out = []
    for p, ptr in rm.m_Container:
        if not p.startswith(prefix):
            continue
        fid = getattr(ptr, 'file_id', None)
        pid = getattr(ptr, 'path_id', None)
        name = os.path.basename(af.externals[fid - 1].path) if fid else '(자기파일)'
        out.append((p, name, pid))
    return out

print("=== 중국판 background/ 색인 ===")
cn = index_of('survey/5577.com.cjenm.chachachacn/assets/bin/Data', 'background/')
for p, n, pid in cn[:18]:
    print("  %-40s %-34s pathID=%s" % (p, n[:32], pid))
print("  ... 총 %d개" % len(cn))

print()
print("=== gogogoracer map/ 색인 (일부) ===")
go = index_of('survey/gogogoracer-1-4-3/assets/bin/Data', 'map/')
for p, n, pid in go[:14]:
    print("  %-46s %-34s pathID=%s" % (p, n[:32], pid))
print("  ... 총 %d개" % len(go))

import collections
print()
print("CN background pathID 분포:", collections.Counter(x[2] for x in cn).most_common(6))
print("gogo map pathID 분포:", collections.Counter(x[2] for x in go).most_common(6))
