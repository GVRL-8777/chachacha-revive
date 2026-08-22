# -*- coding: utf-8 -*-
"""SerializedFile(포맷 9) 메타데이터를 정확히 파싱한다.

포맷 9 레이아웃(플레이어 빌드):
  헤더(빅엔디안 4개): metadata_size, file_size, version, data_offset
  offset 16: endian 바이트 + 예약 3바이트
  메타데이터(offset 20 부터, 리틀엔디안):
    문자열 unity_version
    int  platform
    int  type_count
      각 타입: int class_id + (타입트리 있으면 트리, 플레이어 빌드는 보통 없음)
    int  object_count
      각 오브젝트: int path_id, int byte_start, int byte_size, int type_id, int class_id, short is_destroyed
    int  external_count
      각 외부: 문자열 temp_empty, byte[16] guid, int type, 문자열 path

UnityPy 가 읽은 결과(오브젝트 488개)와 대조해 파싱이 맞는지 검증한다.
"""
import struct, io, sys, UnityPy

path = sys.argv[1] if len(sys.argv) > 1 else \
    'survey/5577.com.cjenm.chachachacn/assets/bin/Data/mainData'
b = io.open(path, 'rb').read()
meta_size, file_size, version, data_offset = struct.unpack_from('>IIII', b, 0)
print("헤더: meta=%d file=%d version=%d data_offset=%d (실제 크기 %d)"
      % (meta_size, file_size, version, data_offset, len(b)))

p = 20


def rstr():
    global p
    e = b.index(b'\x00', p)
    s = b[p:e].decode('utf-8', 'replace')
    p = e + 1
    return s


def i32():
    global p
    v = struct.unpack_from('<i', b, p)[0]
    p += 4
    return v


uver = rstr()
platform = i32()
ntype = i32()
print("유니티=%s 플랫폼=%d 타입 %d개 (타입테이블 시작 %d)" % (uver, platform, ntype, p))
# 타입트리 없는 빌드: 항목당 class_id(4) 만
p += ntype * 4
nobj = i32()
print("오브젝트 %d개, 테이블 오프셋 %d" % (nobj, p))

objs = []
for i in range(nobj):
    pid, start, size, tid, cid = struct.unpack_from('<iiiii', b, p)
    p += 20
    dest = struct.unpack_from('<h', b, p)[0]
    p += 2
    objs.append((pid, start, size, tid, cid))

nx = i32()
print("외부 파일 %d개, 목록 오프셋 %d" % (nx, p))
exts = []
for i in range(nx):
    rstr()                 # temp_empty
    p += 16                # guid
    i32()                  # type
    exts.append(rstr())    # path

print("메타 끝 오프셋 %d (헤더 기록 %d)" % (p, meta_size + 20))
print()
ref = UnityPy.load(path)
ref_ids = sorted(r.path_id for r in ref.objects)
mine = sorted(o[0] for o in objs)
print("UnityPy 오브젝트 %d개 / 직접 파싱 %d개 / pathID 집합 일치: %s"
      % (len(ref_ids), len(mine), ref_ids == mine))
print("외부 파일 예: %s" % exts[:3])
print()
print("데이터 영역: %d ~ %d" % (data_offset, len(b)))
print("가장 뒤 오브젝트: 시작 %d 크기 %d -> 끝 %d"
      % (max(o[1] for o in objs),
         [o[2] for o in objs if o[1] == max(x[1] for x in objs)][0],
         data_offset + max(o[1] for o in objs)
         + [o[2] for o in objs if o[1] == max(x[1] for x in objs)][0]))
