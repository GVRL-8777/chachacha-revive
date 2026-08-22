# -*- coding: utf-8 -*-
"""직렬화 파일에 AssetBundle 매니페스트를 넣되, pathID 를 **정확히** 재번호한다.

실기에서 확인한 사실:
  · AssetBundle 오브젝트가 pathID 1 이 아니면 엔진이 매니페스트를 아예 읽지 않는다.
  · pathID 를 밀 때 내부 PPtr 을 바이트 패턴 검색으로 고치면 데이터가 깨져
    libunity.so 가 잘못된 오프셋에서 죽는다.

그래서 여기서는 UnityPy 의 타입트리 왕복(read_typetree / save_typetree)으로
오브젝트별 PPtr 만 정확히 +1 한다. (m_FileID == 0 인 것만 = 같은 파일 안 참조)
파일 조립은 자체 라이터로 한다 — UnityPy 의 파일 전체 저장은 이 포맷을 깨뜨린다.
"""
import struct, io, sys
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile
from sfparse import parse
from sfwrite import make_manifest, ALIGN


def bump(node, delta, valid):
    """타입트리 dict 를 훑어 내부 PPtr 의 m_PathID 를 delta 만큼 민다."""
    n = 0
    if isinstance(node, dict):
        if set(node.keys()) == {'m_FileID', 'm_PathID'}:
            if node['m_FileID'] == 0 and node['m_PathID'] in valid:
                node['m_PathID'] += delta
                return 1
            return 0
        for v in node.values():
            n += bump(v, delta, valid)
    elif isinstance(node, (list, tuple)):
        for v in node:
            n += bump(v, delta, valid)
    return n


def build(src_path, out_path, bundle_name, key, main_old_pid):
    meta0 = parse(src_path)
    sf = SerializedFile(EndianBinaryReader(io.open(src_path, 'rb').read()), None)
    old_ids = set(sf.objects.keys())

    blobs = []          # (새 pathID, class_id, type_id, 데이터)
    fixed = 0
    for pid in sorted(sf.objects.keys()):
        o = sf.objects[pid]
        tree = o.read_typetree()
        fixed += bump(tree, 1, old_ids)
        o.save_typetree(tree)
        blobs.append((pid + 1, int(o.class_id), int(o.class_id), o.get_raw_data()))

    manifest = make_manifest(bundle_name, [(key, main_old_pid + 1)],
                             (0, main_old_pid + 1))
    entries = [(1, 142, 142, manifest)] + blobs

    # 데이터 영역 배치 (8바이트 정렬)
    data = bytearray()
    objs = []
    for pid, cls, tid, blob in entries:
        while len(data) % 8:
            data += b'\x00'
        objs.append({'path_id': pid, 'start': len(data), 'size': len(blob),
                     'type_id': tid, 'class_id': cls, 'destroyed': 0})
        data += blob

    # 메타데이터
    meta = meta0['unity'].encode('utf-8') + b'\x00'
    meta += struct.pack('<i', meta0['platform'])
    meta += struct.pack('<i', 0)                     # type_count
    meta += struct.pack('<i', meta0['big_id'])
    meta += struct.pack('<i', len(objs))
    for o in objs:
        meta += struct.pack('<iIIiHh', o['path_id'], o['start'], o['size'],
                            o['type_id'], o['class_id'], o['destroyed'])
    meta += struct.pack('<i', len(meta0['externals']))
    for name in meta0['externals']:
        meta += b'\x00' + b'\x00' * 16 + struct.pack('<i', 0) + name.encode('utf-8') + b'\x00'
    meta += b'\x00'                                   # userInformation

    data_offset = max(meta0['data_offset'], ALIGN(20 + len(meta) + 64))
    head = struct.pack('>IIII', len(meta), data_offset + len(data), 9, data_offset)
    head += bytes([1 if meta0['endian'] == '>' else 0, 0, 0, 0])
    out = bytearray(head + meta)
    while len(out) < data_offset:
        out += b'\x00'
    out += data
    io.open(out_path, 'wb').write(bytes(out))
    print("생성: %s (%d B) | 오브젝트 %d개 | 내부 PPtr %d개 정확히 재번호"
          % (out_path, len(out), len(objs), fixed))

    # 역검증
    d2 = parse(out_path)
    print("  pathID=%s 클래스=%s" % ([o['path_id'] for o in d2['objects']],
                                     [o['class_id'] for o in d2['objects']]))
    sf2 = SerializedFile(EndianBinaryReader(io.open(out_path, 'rb').read()), None)
    for pid, o in sf2.objects.items():
        if o.type.name in ('AssetBundle', 'GameObject', 'MeshFilter'):
            t = o.read_typetree()
            print("  pathId=%-3s %-12s %s" % (pid, o.type.name,
                  str(t)[:150]))


if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]))
