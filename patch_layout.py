# -*- coding: utf-8 -*-
"""sfwrite3.py 의 데이터 배치를 '원본 그대로 + 매니페스트 추가' 로 바꾼다.

원본과의 구조 차이를 최소화하기 위해서다.
PPtr 만 바뀌므로 각 오브젝트의 길이가 그대로라 제자리 덮어쓰기가 가능하다.
"""
import io

p = 'sfwrite3.py'
s = io.open(p, encoding='utf-8').read()

start = s.index('    manifest = make_manifest(bundle_name,')
end = s.index('    # 메타데이터')
new = '''    manifest = make_manifest(bundle_name, [(key, main_old_pid + 1)],
                             (0, main_old_pid + 1))

    # 데이터 영역은 **원본 배치를 그대로** 쓴다(오프셋/정렬을 건드리지 않는다).
    # PPtr 만 바뀌어 길이가 같으므로 제자리 덮어쓰기가 된다.
    # 매니페스트는 맨 뒤에 붙이고, 오브젝트 테이블에서만 pathID 1 로 맨 앞에 놓는다.
    src_all = io.open(src_path, 'rb').read()[meta0['data_offset']:]
    orig = dict((o['path_id'], o) for o in meta0['objects'])
    data_len = max(o['start'] + o['size'] for o in meta0['objects'])
    data = bytearray(src_all[:data_len])
    objs = []
    for (newpid, cls, tid, blob) in blobs:
        oldpid = newpid - 1
        st = orig[oldpid]['start']
        if len(blob) != orig[oldpid]['size']:
            raise SystemExit("길이가 달라졌다: pathID %d (%d -> %d)"
                             % (oldpid, orig[oldpid]['size'], len(blob)))
        data[st:st + len(blob)] = blob
        objs.append({'path_id': newpid, 'start': st, 'size': len(blob),
                     'type_id': tid, 'class_id': cls, 'destroyed': 0})
    while len(data) % 8:
        data.append(0)
    man_start = len(data)
    data += manifest
    objs.insert(0, {'path_id': 1, 'start': man_start, 'size': len(manifest),
                    'type_id': 142, 'class_id': 142, 'destroyed': 0})

'''
s = s[:start] + new + s[end:]
io.open(p, 'w', encoding='utf-8').write(s)
import ast
ast.parse(io.open(p, encoding='utf-8').read())
print('sfwrite3.py 배치 방식 변경 완료')
