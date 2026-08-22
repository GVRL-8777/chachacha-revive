# -*- coding: utf-8 -*-
"""직렬화 파일의 외부 참조 하나를 다른 파일로 갈아끼우고, 그걸 가리키는 PPtr 을 고친다.

쓰임새: gogogoracer 의 재질 `aqua_Grass` 는 셰이더 `Mobile-Particle-Alpha` 를
자기 배포판의 `sharedassets1.assets` pathID 69 에서 찾는다. 중국판의 같은 이름
파일은 내용이 전혀 달라(pathID 가 안 맞는다) 그대로 옮기면 엉뚱한 자산을 문다.
그런데 **중국판 내장 리소스 파일의 pathID 2 가 바로 그 셰이더**다.
그래서 외부 참조를 내장 파일로 바꾸고 pathID 를 2 로 돌린다.

외부 이름의 길이가 달라져 메타데이터 크기가 바뀌므로 파일을 새로 쓴다
(오브젝트 데이터는 그대로, 오프셋만 다시 계산).

사용법:
  python fixext.py <입력> <출력> <바꿀외부이름> <새외부이름> <옛pathID> <새pathID>
"""
import io, struct, sys
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile
from sfparse import parse
from sfwrite import ALIGN

src, dst, old_ext, new_ext, old_pid, new_pid = sys.argv[1:7]
old_pid, new_pid = int(old_pid), int(new_pid)

meta = parse(src)
raw = io.open(src, 'rb').read()
sf = SerializedFile(EndianBinaryReader(raw), None)

if old_ext not in meta['externals']:
    raise SystemExit("외부 참조에 %s 가 없다: %s" % (old_ext, meta['externals']))
idx = meta['externals'].index(old_ext)          # 0-based, PPtr 에서는 +1
exts = list(meta['externals'])
exts[idx] = new_ext

starts = dict((o['path_id'], (o['start'], o['size'])) for o in meta['objects'])
data_len = max(o['start'] + o['size'] for o in meta['objects'])
data = bytearray(raw[meta['data_offset']:meta['data_offset'] + data_len])

fixed = 0


def walk(node):
    global fixed
    n = 0
    if isinstance(node, dict):
        if set(node.keys()) == {'m_FileID', 'm_PathID'}:
            if node['m_FileID'] == idx + 1 and node['m_PathID'] == old_pid:
                node['m_PathID'] = new_pid
                fixed += 1
                return 1
            return 0
        for v in node.values():
            n += walk(v)
    elif isinstance(node, (list, tuple)):
        for v in node:
            n += walk(v)
    return n


objs = []
for pid, o in sorted(sf.objects.items()):
    tree = o.read_typetree()
    walk(tree)
    blob = bytes(o.save_typetree(tree))
    st, sz = starts[pid]
    if len(blob) != sz:
        raise SystemExit("길이가 달라졌다: pathID %d (%d -> %d)" % (pid, sz, len(blob)))
    data[st:st + sz] = blob
    objs.append({'path_id': pid, 'start': st, 'size': sz,
                 'type_id': int(o.class_id), 'class_id': int(o.class_id), 'destroyed': 0})

m = meta['unity'].encode('utf-8') + b'\x00'
m += struct.pack('<i', meta['platform'])
m += struct.pack('<i', 0)                       # type_count (플레이어 빌드)
m += struct.pack('<i', meta['big_id'])
m += struct.pack('<i', len(objs))
for o in objs:
    m += struct.pack('<iIIiHh', o['path_id'], o['start'], o['size'],
                     o['type_id'], o['class_id'], o['destroyed'])
m += struct.pack('<i', len(exts))
for name in exts:
    m += b'\x00' + b'\x00' * 16 + struct.pack('<i', 0) + name.encode('utf-8') + b'\x00'
m += b'\x00'                                     # userInformation

data_offset = max(meta['data_offset'], ALIGN(20 + len(m) + 64))
head = struct.pack('>IIII', len(m), data_offset + len(data), 9, data_offset)
head += bytes([1 if meta['endian'] == '>' else 0, 0, 0, 0])
out = bytearray(head + m)
while len(out) < data_offset:
    out += b'\x00'
out += data
io.open(dst, 'wb').write(bytes(out))
print("외부 %s -> %s, PPtr %d개 pathID %d -> %d" % (old_ext, new_ext, fixed, old_pid, new_pid))
print("출력: %s (%d B, 원본 %d B)" % (dst, len(out), len(raw)))
