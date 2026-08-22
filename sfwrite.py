# -*- coding: utf-8 -*-
"""직렬화 파일(포맷 9)에 AssetBundle 매니페스트(classID 142)를 합성해 넣는다.

왜 필요한가:
  손으로 만든 번들을 엔진이 열기는 하는데, `AssetBundle.Load(이름)` / `LoadAll` 은
  번들 안의 AssetBundle 오브젝트(m_Container)를 보고 자산을 찾는다.
  그 오브젝트가 없으면 "열리지만 비어 있는" 번들이 된다.

레이아웃(UnityPy 의 TPK 에서 Unity 4.1.5 기준으로 확인):
  string m_Name                                  (문자열 뒤 4바이트 정렬)
  vector m_PreloadTable   : int size + PPtr{int fileID,int pathID} × size
  map    m_Container      : int size + pair{ string first(정렬) , AssetInfo } × size
  AssetInfo m_MainAsset   : int preloadIndex, int preloadSize, PPtr asset
  vector m_ScriptCompatibility : int size (0)
  vector m_ClassCompatibility  : int size (0)

플레이어 빌드의 이 파일들은 **타입 테이블이 비어 있어**(type_count=0) 타입트리를 쓸 필요가 없다.
"""
import struct, io, sys
from sfparse import parse

ALIGN = lambda n: (n + 3) & ~3


def w_str(s):
    b = s.encode('utf-8')
    out = struct.pack('<i', len(b)) + b
    while len(out) % 4:
        out += b'\x00'
    return out


def w_pptr(fid, pid):
    return struct.pack('<ii', fid, pid)


def make_manifest(name, entries, main=(0, 0)):
    """entries: [(컨테이너키, pathID)] — 번들에서 이름으로 꺼낼 자산 목록"""
    out = w_str(name)
    # m_PreloadTable: 각 자산을 그대로 넣는다
    out += struct.pack('<i', len(entries))
    for _, pid in entries:
        out += w_pptr(0, pid)
    # m_Container
    out += struct.pack('<i', len(entries))
    for i, (key, pid) in enumerate(entries):
        out += w_str(key)
        out += struct.pack('<ii', i, 1)      # preloadIndex, preloadSize
        out += w_pptr(0, pid)
    # m_MainAsset
    out += struct.pack('<ii', 0, 0) + w_pptr(main[0], main[1])
    # m_ScriptCompatibility, m_ClassCompatibility (둘 다 0개)
    out += struct.pack('<i', 0)
    out += struct.pack('<i', 0)
    return out


def build(src_path, out_path, bundle_name, entries, main_pid=0):
    d = parse(src_path)
    b = io.open(src_path, 'rb').read()
    if d['version'] != 9:
        raise SystemExit("포맷 9 전용 (이 파일은 %d)" % d['version'])
    if d['types']:
        raise SystemExit("타입 테이블이 있는 파일은 아직 지원하지 않는다")

    manifest = make_manifest(bundle_name, entries, (0, main_pid))
    new_pid = max(o['path_id'] for o in d['objects']) + 1
    last = max(d['objects'], key=lambda o: o['start'])
    data_end = ALIGN(last['start'] + last['size'])

    # 유니티는 번들에서 AssetBundle 오브젝트를 오브젝트 테이블 **앞쪽**에서 찾는다.
    # pathID 는 그대로 두고 표 순서만 맨 앞으로 놓는다(내부 참조는 pathID 기준이라 안전).
    objs = [{'path_id': new_pid, 'start': data_end, 'size': len(manifest),
             'type_id': 142, 'class_id': 142, 'destroyed': 0}]
    objs += list(d['objects'])

    # --- 메타데이터 재구성 ---
    meta = b''
    meta += d['unity'].encode('utf-8') + b'\x00'
    meta += struct.pack('<i', d['platform'])
    meta += struct.pack('<i', 0)                    # type_count
    meta += struct.pack('<i', d['big_id'])
    meta += struct.pack('<i', len(objs))
    for o in objs:
        meta += struct.pack('<iIIiHh', o['path_id'], o['start'], o['size'],
                            o['type_id'], o['class_id'], o['destroyed'])
    meta += struct.pack('<i', len(d['externals']))
    for name in d['externals']:
        meta += b'\x00'                             # temp_empty
        meta += b'\x00' * 16                        # guid
        meta += struct.pack('<i', 0)                # type
        meta += name.encode('utf-8') + b'\x00'
    meta += d['user_info'].encode('utf-8') + b'\x00'

    data_offset = d['data_offset']
    if 20 + len(meta) > data_offset:
        data_offset = ALIGN(20 + len(meta) + 64)

    # --- 데이터 영역 ---
    src_data = b[d['data_offset']:]
    data = bytearray(src_data[:data_end])
    while len(data) < data_end:
        data += b'\x00'
    data += manifest

    head = struct.pack('>IIII', len(meta), data_offset + len(data), 9, data_offset)
    head += bytes([1 if d['endian'] == '>' else 0, 0, 0, 0])
    blob = bytearray(head + meta)
    while len(blob) < data_offset:
        blob += b'\x00'
    blob += data

    io.open(out_path, 'wb').write(bytes(blob))
    print("생성: %s (%d B) | 오브젝트 %d개 (매니페스트 pathID=%d, %d B)"
          % (out_path, len(blob), len(objs), new_pid, len(manifest)))
    return out_path


if __name__ == '__main__':
    src = sys.argv[1]
    out = sys.argv[2]
    name = sys.argv[3]
    key = sys.argv[4]
    pid = int(sys.argv[5])
    build(src, out, name, [(key, pid)], pid)
    # 역검증
    d2 = parse(out)
    print("역검증: 오브젝트 %d개, 클래스 %s"
          % (len(d2['objects']), [o['class_id'] for o in d2['objects']]))
    try:
        import UnityPy
        env = UnityPy.load(out)
        for r in env.objects:
            if r.type.name == 'AssetBundle':
                ab = r.read()
                print("   UnityPy 확인: AssetBundle m_Name=%r 컨테이너=%s"
                      % (ab.m_Name, [k for k, _ in ab.m_Container]))
    except Exception as e:
        print("   UnityPy 확인 실패:", type(e).__name__, e)
