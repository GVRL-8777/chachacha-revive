# -*- coding: utf-8 -*-
"""복원한 원본 sfmerge.py 에 꼭 필요한 두 가지만 다시 얹는다.

  · @목록파일 인자 (스펙 줄에 콜론이 섞여 있어 인자로 넘기기 번거롭다)
  · 이름을 갈라낸 의존 자산의 새 이름을 바깥참조표에 반영

나머지(프리로드 표 전체 적재, 컨테이너 키 여러 표기, 번들 내부참조 전환,
MonoBehaviour 처리)는 이번에 넣었다가 맵이 안 뜨는 원인 후보가 되었으므로
일단 빼고 간다.
"""
import ast
import io

p = 'sfmerge.py'
s = io.open(p, encoding='utf-8').read()

old = "    merge(sys.argv[1], sys.argv[2], sys.argv[3:])"
new = """    specs = []
    for a in sys.argv[3:]:
        if a.startswith('@'):
            for ln in io.open(a[1:], encoding='utf-8').read().splitlines():
                if ln.strip():
                    specs.append(ln.strip())
        else:
            specs.append(a)
    merge(sys.argv[1], sys.argv[2], specs)"""
assert old in s
s = s.replace(old, new, 1)

old = """    meta += struct.pack('<i', len(ext_order))
    for name in ext_order:"""
new = """    import json, os.path as _op
    _ren = {}
    if _op.exists('rename_ov.json'):
        _ren = json.load(io.open('rename_ov.json', encoding='utf-8'))
    ext_order = [_ren.get(_op.basename(e), e) for e in ext_order]
    meta += struct.pack('<i', len(ext_order))
    for name in ext_order:"""
assert old in s
s = s.replace(old, new, 1)

io.open(p, 'w', encoding='utf-8').write(s)
ast.parse(s)
print('sfmerge 에 @목록 + 새 이름 반영 (구문 OK)')
