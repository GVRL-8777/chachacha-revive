# -*- coding: utf-8 -*-
"""apischema.exe 가 놓치는 컨테이너/배열 타입을 IL 에서 직접 읽어 스키마 JSON 에 보정한다.

게터가 `HTTP_Data::_getObjectData` 를 쓰면 그 키는 오브젝트 컨테이너,
`_getArrayData` 면 배열, `_getIntArrayData` 면 int[] 다.
서버의 auto() 가 이 타입을 알아야 응답을 올바른 모양으로 만든다.

사용법: python fixschema.py <Assembly-CSharp.dll> <managed폴더> <스키마.json>
"""
import subprocess, sys, json, io, re, os

dll, managed, sch = sys.argv[1], sys.argv[2], sys.argv[3]

out = subprocess.run(['./cdump.exe', dll, managed, 'il', r'^HTTP_\w+::get_\w+$'],
                     capture_output=True)
txt = out.stdout.decode('utf-8', 'replace')

cur = None
found = {}
for ln in txt.split('\n'):
    m = re.match(r'==== (HTTP_\w+)::get_(\w+)', ln)
    if m:
        cur = m.groups()
        continue
    if not cur:
        continue
    if '_getIntArrayData' in ln:
        found.setdefault(cur[0], {})[cur[1]] = 'int[]'; cur = None
    elif '_getArrayData' in ln:
        found.setdefault(cur[0], {})[cur[1]] = 'array'; cur = None
    elif '_getObjectData' in ln:
        found.setdefault(cur[0], {})[cur[1]] = 'object'; cur = None

d = json.load(io.open(sch, encoding='utf-8-sig'))
n = 0
for cls, kv in found.items():
    if cls not in d:
        continue
    t = d[cls].setdefault('types', {})
    for k, v in kv.items():
        if t.get(k) != v:
            t[k] = v
            n += 1
            print("  %s.%s -> %s" % (cls, k, v))
json.dump(d, io.open(sch, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print("보정 %d건 -> %s" % (n, sch))
