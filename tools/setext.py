# -*- coding: utf-8 -*-
"""직렬화 파일의 외부참조표를 통째로 다시 쓴다(이름 길이가 달라도 된다).

오브젝트의 start 는 data_offset 기준 상대값이라, 메타데이터 길이가 바뀌어도
data_offset 만 다시 맞추면 오브젝트 표를 손댈 필요가 없다.
"""
import io, struct
from sfparse import parse, R, read_tree_old


def ext_block_offset(path):
    """외부참조 개수(int32)가 적힌 자리의 파일 오프셋."""
    b = io.open(path, 'rb').read()
    endian = '>' if b[16] else '<'
    r = R(b, 20, endian)
    r.s(); r.i32()                      # unity, platform
    tc = r.i32()
    for _ in range(tc):
        r.i32(); read_tree_old(r)
    r.i32()                             # big_id
    oc = r.i32()
    r.p += oc * 20                      # 오브젝트 표
    return r.p, b, endian


def set_externals(path, names, out=None):
    start, b, endian = ext_block_offset(path)
    meta_size, file_size, version, data_offset = struct.unpack_from('>IIII', b, 0)
    head_fixed = b[20:start]            # 유니티 버전 ~ 오브젝트 표
    blk = struct.pack(endian + 'i', len(names))
    for n in names:
        blk += b'\x00' + b'\x00' * 16 + struct.pack(endian + 'i', 0) \
               + n.encode('utf-8') + b'\x00'
    blk += b'\x00'                      # userInformation
    meta = head_fixed + blk
    new_off = data_offset
    while 20 + len(meta) > new_off:
        new_off += 4096
    data = b[data_offset:]
    outb = struct.pack('>IIII', len(meta), new_off + len(data), version, new_off)
    outb += b[16:20] + meta
    outb += b'\x00' * (new_off - len(outb))
    outb += data
    io.open(out or path, 'wb').write(outb)
    return len(meta), new_off


if __name__ == '__main__':
    import sys
    p = sys.argv[1]
    old = parse(p)['externals']
    new = sys.argv[2:]
    ms, do = set_externals(p, new)
    d = parse(p)
    print("%s\n  이전 외부: %s\n  이후 외부: %s\n  meta %d -> %d, data_offset %d"
          % (p, old, d['externals'], 0, ms, do))
