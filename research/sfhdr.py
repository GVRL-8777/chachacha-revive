# -*- coding: utf-8 -*-
"""유니티 SerializedFile(mainData)의 헤더/테이블 구조를 직접 파싱한다.

'색인에 새 경로를 추가하려면 무엇을 고쳐야 하는가' 를 정확히 파악하기 위한 것.
UnityPy 재저장이 파일을 망가뜨리므로, 직접 패치가 가능한지 구조를 본다.
"""
import struct, sys, io

path = sys.argv[1] if len(sys.argv) > 1 else \
    'survey/5577.com.cjenm.chachachacn/assets/bin/Data/mainData'
b = io.open(path, 'rb').read()
print("파일 크기 %d B" % len(b))

# 헤더는 빅엔디안 4개 (유니티 4 기준)
meta_size, file_size, version, data_offset = struct.unpack_from('>IIII', b, 0)
print("메타데이터 크기 %d | 파일 크기(기록) %d | 포맷 버전 %d | 데이터 시작 %d"
      % (meta_size, file_size, version, data_offset))

p = 16
endian = b[p]; p += 1          # 1 = 빅엔디안
p += 3                          # 예약
print("엔디안 플래그: %d (%s)" % (endian, "빅" if endian else "리틀"))

def rstr(pos):
    e = b.index(b'\x00', pos)
    return b[pos:e].decode('utf-8', 'replace'), e + 1

ver_str, p = rstr(p)
print("유니티 버전 문자열: %s" % ver_str)
platform = struct.unpack_from('<i', b, p)[0]; p += 4
print("플랫폼: %d" % platform)

has_tt = b[p]; p += 1
print("타입트리 포함: %s  <-- 플레이어 빌드는 보통 0" % bool(has_tt))

ntypes = struct.unpack_from('<i', b, p)[0]; p += 4
print("타입 개수 %d" % ntypes)
# 타입트리가 없으면 항목이 (classID, 16바이트 해시) 정도로 짧다
p += ntypes * (4 + 16) if not has_tt else 0

nobj = struct.unpack_from('<i', b, p)[0]; p += 4
print("오브젝트 개수 %d  (테이블 시작 오프셋 %d)" % (nobj, p))
first = struct.unpack_from('<iiiii', b, p)[:5]
print("첫 항목(pathID, 오프셋, 크기, typeIdx, classID) = %s" % (first,))
print()
print("=== 새 경로를 추가하려면 고쳐야 할 것 ===")
print(" 1) ResourceManager 오브젝트의 m_Container 배열: 항목 수 +1, (문자열 + PPtr 8바이트) 추가")
print(" 2) 그 오브젝트가 커지므로 뒤따르는 모든 오브젝트의 '오프셋' 갱신")
print(" 3) externals 목록에 파일 추가 시 메타데이터가 커지므로 data_offset 과 전 오프셋 재계산")
print(" 4) 헤더의 meta_size / file_size 갱신")
print()
print("오브젝트끼리는 파일 오프셋이 아니라 pathID 로 서로를 가리키므로,")
print("데이터 블롭을 통째로 옮겨도 참조가 깨지지 않는다 -> 재배치가 안전하다.")
