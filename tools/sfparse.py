# -*- coding: utf-8 -*-
"""유니티 SerializedFile(포맷 9) 정밀 파서.

UnityPy 소스에서 확인한 레이아웃:
  헤더(빅엔디안 u32 ×4): metadata_size, file_size, version, data_offset
  v>=9: endian 바이트 + 예약 3바이트
  --- 메타데이터(파일 엔디안) ---
  v>=7 : 문자열 unity_version
  v>=8 : int target_platform
  v>=13: bool enable_type_tree      (9 에는 없음)
  int type_count
     SerializedType × n   (v<13 이면 타입트리를 옛 포맷으로 포함)
  7<=v<14: int big_id_enabled       <-- 이걸 빠뜨려서 앞서 파싱이 깨졌다
  int object_count
     오브젝트 × n : path_id(int), byte_start(u32), byte_size(u32), type_id(int), class_id(u16), is_destroyed(i16)
  v>=11: script 목록 (9 에는 없음)
  int externals_count
     외부 × n : 문자열 temp_empty, guid16, int type, 문자열 path
  v>=5 : 문자열 userInformation
"""
import struct, io, sys


class R:
    def __init__(self, b, pos=0, endian='<'):
        self.b, self.p, self.e = b, pos, endian

    def u32(self):
        v = struct.unpack_from(self.e + 'I', self.b, self.p)[0]; self.p += 4; return v

    def i32(self):
        v = struct.unpack_from(self.e + 'i', self.b, self.p)[0]; self.p += 4; return v

    def i16(self):
        v = struct.unpack_from(self.e + 'h', self.b, self.p)[0]; self.p += 2; return v

    def u16(self):
        v = struct.unpack_from(self.e + 'H', self.b, self.p)[0]; self.p += 2; return v

    def byte(self):
        v = self.b[self.p]; self.p += 1; return v

    def s(self):
        e = self.b.index(b'\x00', self.p)
        v = self.b[self.p:e].decode('utf-8', 'replace'); self.p = e + 1; return v

    def raw(self, n):
        v = self.b[self.p:self.p + n]; self.p += n; return v

    def align(self):
        self.p = (self.p + 3) & ~3


def read_tree_old(r):
    """v<13 의 옛 타입트리: 재귀 구조."""
    type_name = r.s()
    name = r.s()
    r.raw(6 * 4)                 # byte_size, index, is_array, version, meta_flag ... (총 5~6개 int)
    child_count = r.i32()
    kids = [read_tree_old(r) for _ in range(child_count)]
    return (type_name, name, kids)


def parse(path):
    b = io.open(path, 'rb').read()
    meta_size, file_size, version, data_offset = struct.unpack_from('>IIII', b, 0)
    endian = '>' if b[16] else '<'
    r = R(b, 20, endian)
    out = {'path': path, 'meta_size': meta_size, 'file_size': file_size,
           'version': version, 'data_offset': data_offset, 'endian': endian,
           'size': len(b)}
    out['unity'] = r.s()
    out['platform'] = r.i32()
    tc = r.i32()
    out['types'] = []
    for _ in range(tc):
        cid = r.i32()
        tree = read_tree_old(r)
        out['types'].append((cid, tree))
    out['big_id'] = r.i32()
    oc = r.i32()
    out['obj_table_at'] = r.p      # 오브젝트 표가 시작하는 자리 (고쳐 쓸 때 쓴다)
    out['obj_entry_size'] = 20
    objs = []
    for _ in range(oc):
        pid = r.i32()
        start = r.u32()
        size = r.u32()
        tid = r.i32()
        cls = r.u16()
        dest = r.i16()
        objs.append({'path_id': pid, 'start': start, 'size': size,
                     'type_id': tid, 'class_id': cls, 'destroyed': dest})
    out['objects'] = objs
    ec = r.i32()
    exts = []
    for _ in range(ec):
        r.s()                     # temp_empty
        guid = r.raw(16)
        t = r.i32()
        exts.append(r.s())
    out['externals'] = exts
    out['user_info'] = r.s()
    out['meta_end'] = r.p
    return out


if __name__ == '__main__':
    p = sys.argv[1] if len(sys.argv) > 1 else \
        'survey/gogogoracer-1-4-3/assets/bin/Data/32f46795bf14050449f88a9b04a1acfb'
    d = parse(p)
    print("%s (%d B)" % (d['path'].split('/')[-1][:20], d['size']))
    print("  포맷 %d | 유니티 %s | 엔디안 %s | 플랫폼 %d"
          % (d['version'], d['unity'], d['endian'], d['platform']))
    print("  meta_size=%d data_offset=%d  (메타 끝 실측 %d, 20+meta=%d)"
          % (d['meta_size'], d['data_offset'], d['meta_end'], 20 + d['meta_size']))
    print("  타입 %d개: %s" % (len(d['types']), [t[0] for t in d['types']]))
    print("  big_id_enabled=%d" % d['big_id'])
    print("  오브젝트 %d개:" % len(d['objects']))
    for o in d['objects']:
        print("     pathID=%-3d class=%-4d start=%-7d size=%-7d type_id=%d"
              % (o['path_id'], o['class_id'], o['start'], o['size'], o['type_id']))
    print("  외부 %d개: %s" % (len(d['externals']), d['externals'][:3]))
    print("  userInformation=%r" % d['user_info'])
