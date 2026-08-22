# -*- coding: utf-8 -*-
"""AssetBundle 매니페스트를 **pathID 1** 에 놓는 변형.

실제 유니티 번들은 AssetBundle 오브젝트가 pathID 1 이다.
엔진이 그 위치를 전제하는지 확인하기 위해, 기존 오브젝트 pathID 를 +1 로 밀고
오브젝트 안의 내부 참조(PPtr: fileID=0, pathID=N)도 함께 +1 한다.

내부 PPtr 은 (int fileID, int pathID) 8바이트다. fileID==0 이고 pathID 가
기존 범위 안인 것만 골라 바꾼다. 메시(class 43)에는 PPtr 이 없으므로 건드리지 않는다.
"""
import struct, io, sys
from sfparse import parse
from sfwrite import make_manifest, ALIGN

PPTR_CLASSES = {1, 4, 23, 33, 137, 111, 95}     # GameObject/Transform/Renderer/Filter 등


def bump_pptrs(data, valid_ids, delta=1):
    out = bytearray(data)
    n = 0
    for off in range(0, len(out) - 8 + 1, 4):
        fid, pid = struct.unpack_from('<ii', out, off)
        if fid == 0 and pid in valid_ids:
            struct.pack_into('<ii', out, off, 0, pid + delta)
            n += 1
    return bytes(out), n


def build(src_path, out_path, bundle_name, key, target_old_pid):
    d = parse(src_path)
    b = io.open(src_path, 'rb').read()
    old_ids = set(o['path_id'] for o in d['objects'])

    # 데이터 재배치: 기존 오브젝트를 순서대로 다시 쌓는다(내부 PPtr 을 +1 하면서)
    src_data = b[d['data_offset']:]
    newdata = bytearray()
    newobjs = []
    fixed = 0
    for o in sorted(d['objects'], key=lambda x: x['start']):
        blob = src_data[o['start']:o['start'] + o['size']]
        if o['class_id'] in PPTR_CLASSES:
            blob, k = bump_pptrs(blob, old_ids)
            fixed += k
        while len(newdata) % 8:
            newdata += b'\x00'
        newobjs.append({'path_id': o['path_id'] + 1, 'start': len(newdata),
                        'size': len(blob), 'type_id': o['type_id'],
                        'class_id': o['class_id'], 'destroyed': 0})
        newdata += blob

    manifest = make_manifest(bundle_name, [(key, target_old_pid + 1)],
                             (0, target_old_pid + 1))
    while len(newdata) % 8:
        newdata += b'\x00'
    man_start = len(newdata)
    newdata += manifest
    newobjs.insert(0, {'path_id': 1, 'start': man_start, 'size': len(manifest),
                       'type_id': 142, 'class_id': 142, 'destroyed': 0})

    meta = d['unity'].encode('utf-8') + b'\x00'
    meta += struct.pack('<i', d['platform'])
    meta += struct.pack('<i', 0)
    meta += struct.pack('<i', d['big_id'])
    meta += struct.pack('<i', len(newobjs))
    for o in newobjs:
        meta += struct.pack('<iIIiHh', o['path_id'], o['start'], o['size'],
                            o['type_id'], o['class_id'], o['destroyed'])
    meta += struct.pack('<i', len(d['externals']))
    for name in d['externals']:
        meta += b'\x00' + b'\x00' * 16 + struct.pack('<i', 0) + name.encode('utf-8') + b'\x00'
    meta += b'\x00'          # userInformation

    data_offset = max(d['data_offset'], ALIGN(20 + len(meta) + 64))
    head = struct.pack('>IIII', len(meta), data_offset + len(newdata), 9, data_offset)
    head += bytes([1 if d['endian'] == '>' else 0, 0, 0, 0])
    blob = bytearray(head + meta)
    while len(blob) < data_offset:
        blob += b'\x00'
    blob += newdata
    io.open(out_path, 'wb').write(bytes(blob))
    print("생성: %s (%d B) | 오브젝트 %d개 | 내부 PPtr %d개 보정 | 매니페스트 pathID=1"
          % (out_path, len(blob), len(newobjs), fixed))

    d2 = parse(out_path)
    print("역검증: pathID=%s 클래스=%s"
          % ([o['path_id'] for o in d2['objects']], [o['class_id'] for o in d2['objects']]))


if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]))
