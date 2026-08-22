# -*- coding: utf-8 -*-
"""저장 전후로 오브젝트 페이로드가 보존되는지 바이트 단위로 비교한다."""
import UnityPy

FILES = [
    ('원본', 'survey/5577.com.cjenm.chachachacn/assets/bin/Data/mainData'),
    ('wtest', 'wtest_mainData'),
    ('xtest', 'xtest_mainData'),
]

data = {}
for tag, f in FILES:
    env = UnityPy.load(f)
    tot = 0
    per = {}
    for r in env.objects:
        try:
            b = r.get_raw_data()
        except Exception:
            b = b''
        per[r.path_id] = len(b)
        tot += len(b)
    data[tag] = per
    rm = [r for r in env.objects if r.type.name == "ResourceManager"][0].read()
    print("%-6s 오브젝트 페이로드 합계 %9d B | 컨테이너 %d개" % (tag, tot, len(rm.m_Container)))

base = data['원본']
for tag in ('wtest', 'xtest'):
    cur = data[tag]
    diff = [(pid, base[pid], cur.get(pid, -1)) for pid in base
            if cur.get(pid, -1) != base[pid]]
    print("%-6s 원본과 크기가 다른 오브젝트: %d개" % (tag, len(diff)))
    for pid, a, b in diff[:5]:
        print("        pathId=%-5s 원본 %8d -> %8d" % (pid, a, b))
