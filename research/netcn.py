# -*- coding: utf-8 -*-
"""중국판의 NetQuery/NetRecive 패킷 스키마를 뽑아 netcn.json 으로 저장한다.

  · NetQuery.<X>::.ctor 안의 ldstr "/경로"   -> 경로
  · NetRecive.<X>/eType 열거형               -> 응답 JSON 키 목록
    (Count/MaxCount 는 센티널이라 제외)

0번 키가 배열 컨테이너인지는 이름 규칙으로 판별한다(messages, cars, skillList …).
IL 로 인덱스 상수를 읽어 판별하려 했으나 안정적이지 않아 이름 쪽이 확실하다.
"""
import subprocess, re, json, io

paths = {}
out = subprocess.run(['./cdump.exe', 'mgcn/Assembly-CSharp.dll', 'mgcn', 'strings', '^/[a-z]'],
                     capture_output=True).stdout.decode('utf-8', 'replace')
cur = None
for ln in out.splitlines():
    m = re.match(r'\s+(NetQuery\.\w+)::', ln)
    if m:
        cur = m.group(1).split('.')[1]
        continue
    m2 = re.match(r'\s+"(/[^"]+)"', ln)
    if m2 and cur:
        paths[m2.group(1)] = cur
        cur = None

enums = {}
out2 = subprocess.run(['./enumdump.exe', 'mgcn/Assembly-CSharp.dll', 'NetRecive'],
                      capture_output=True).stdout.decode('utf-8', 'replace')
cls = None
for ln in out2.splitlines():
    m = re.match(r'### NetRecive\.(\w+)/eType', ln)
    if m:
        cls = m.group(1)
        enums[cls] = []
        continue
    m2 = re.match(r'\s+(\d+) = (\w+)', ln)
    if m2 and cls:
        enums[cls].append(m2.group(2))


def is_container(keys):
    if len(keys) < 2:
        return False
    k = keys[0]
    return k.endswith('List') or k.endswith('s')


table = {}
for p, c in sorted(paths.items()):
    keys = enums.get(c)
    if not keys:
        continue
    keys = [k for k in keys if k not in ('Count', 'MaxCount')]
    table[p] = {"class": c, "keys": keys, "container": is_container(keys)}

json.dump(table, io.open('netcn.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print("경로 %d개 / 패킷 %d종, 매핑 %d개 -> netcn.json" % (len(paths), len(enums), len(table)))
for p in sorted(table):
    t = table[p]
    print("  %-42s %-26s 배열=%-5s %s" % (p, t['class'], t['container'], t['keys'][:4]))
