# -*- coding: utf-8 -*-
"""중국판 색인에서 '실제로 쓰이지 않는/비어 있는' 항목을 찾는다.

색인에 새 경로를 추가하는 게(=파일 재작성이) 어려우므로,
이미 있는데 아무도 안 쓰는 슬롯을 재활용하면 '포기 없는 추가' 가 된다.

판정 기준:
  · dangling  : 가리키는 외부 파일이 Data 폴더에 없음 -> 로드하면 어차피 실패
  · 중복      : 같은 파일+pathID 를 여러 경로가 가리킴 -> 하나만 있으면 됨
  · 미참조    : 게임 어셈블리 문자열에 그 경로 이름 조각이 전혀 안 나옴(추정)
"""
import os, io, re, collections, UnityPy

DATA = 'survey/5577.com.cjenm.chachachacn/assets/bin/Data'
env = UnityPy.load(os.path.join(DATA, 'mainData'))
rm = [r for r in env.objects if r.type.name == "ResourceManager"][0].read()
af = env.objects[0].assets_file

entries = []
for p, ptr in rm.m_Container:
    fid = getattr(ptr, 'file_id', None)
    pid = getattr(ptr, 'path_id', None)
    name = os.path.basename(af.externals[fid - 1].path) if fid else None
    entries.append((p, name, pid))

print("색인 항목 %d개 (경로 %d종)" % (len(entries), len(set(e[0] for e in entries))))

present = set(os.listdir(DATA))
dangling = [e for e in entries if e[1] and e[1] not in present]
print("가리키는 파일이 없는 항목: %d개" % len(dangling))
for e in dangling[:8]:
    print("   %-44s -> %s" % (e[0][:44], (e[1] or '')[:20]))

# 같은 (파일,pathID) 를 가리키는 경로가 둘 이상인 경우
bytarget = collections.defaultdict(list)
for p, n, pid in entries:
    bytarget[(n, pid)].append(p)
dup = {k: v for k, v in bytarget.items() if len(set(v)) > 1}
print()
print("한 자산을 여러 경로가 가리키는 경우: %d건" % len(dup))
for k, v in list(dup.items())[:6]:
    print("   %s -> %s" % (k[0][:16] if k[0] else None, sorted(set(v))[:3]))

# 어셈블리에서 경로 문자열이 언급되는지 (대충 마지막 세그먼트로 검색)
asm = io.open('mgcn/Assembly-CSharp.dll', 'rb').read().decode('utf-16-le', 'ignore').lower()
paths = sorted(set(e[0] for e in entries))
unref = []
for p in paths:
    last = p.split('/')[-1]
    if len(last) < 5:
        continue
    if last.lower() not in asm and p.lower() not in asm:
        unref.append(p)
print()
print("어셈블리 문자열에 이름이 전혀 안 나오는 경로: %d개 / %d" % (len(unref), len(paths)))
for p in unref[:15]:
    print("   %s" % p)
io.open('unref_cn.txt', 'w', encoding='utf-8').write("\n".join(unref))
print("-> unref_cn.txt 저장")
