# -*- coding: utf-8 -*-
"""resources.arsc 의 문자열 하나를 길이가 달라도 안전하게 바꾼다.

앱 이름은 매니페스트에 리소스 참조로만 들어 있고 실제 문자열은 arsc 의
전역 문자열 풀에 UTF-8 로 있다. 길이가 바뀌면 뒤따르는 오프셋과 청크 크기를
모두 다시 맞춰야 해서 제자리 치환으로는 안 된다.

  python setappname.py <in.apk> <out.apk> <바꿀문자열> <새문자열>
"""
import io
import struct
import sys
import zipfile

RES_STRING_POOL = 0x0001
UTF8_FLAG = 1 << 8


def u16(b, o):
    return struct.unpack_from('<H', b, o)[0]


def u32(b, o):
    return struct.unpack_from('<I', b, o)[0]


def enc_len(n):
    """UTF-8 풀의 길이 표기(0x7F 넘으면 2바이트)."""
    if n > 0x7F:
        return bytes([(n >> 8) | 0x80, n & 0xFF])
    return bytes([n])


def rewrite_pool(data, pool_off, old, new):
    """풀 하나를 다시 쓴다. (새 데이터, 크기변화) 반환."""
    typ = u16(data, pool_off)
    assert typ == RES_STRING_POOL, typ
    hdr_size = u16(data, pool_off + 2)
    size = u32(data, pool_off + 4)
    cnt = u32(data, pool_off + 8)
    style_cnt = u32(data, pool_off + 12)
    flags = u32(data, pool_off + 16)
    str_start = u32(data, pool_off + 20)
    style_start = u32(data, pool_off + 24)
    if not (flags & UTF8_FLAG):
        raise SystemExit('UTF-8 풀이 아니다')

    offs = [u32(data, pool_off + hdr_size + 4 * i) for i in range(cnt)]
    base = pool_off + str_start
    strs = []
    for o in offs:
        p = base + o
        clen = data[p]
        p += 2 if clen & 0x80 else 1
        blen = data[p]
        p += 2 if blen & 0x80 else 1
        if data[p - 1] & 0x80:      # 2바이트 표기 보정
            pass
        # 길이 표기를 다시 정확히 읽는다
        q = base + o
        c1 = data[q]
        if c1 & 0x80:
            q += 2
        else:
            q += 1
        b1 = data[q]
        if b1 & 0x80:
            nbytes = ((b1 & 0x7F) << 8) | data[q + 1]
            q += 2
        else:
            nbytes = b1
            q += 1
        strs.append(data[q:q + nbytes].decode('utf-8', 'replace'))

    hits = [i for i, s in enumerate(strs) if s == old]
    if not hits:
        raise SystemExit('그 문자열이 없다: %r' % old)
    for i in hits:
        strs[i] = new

    # 새 데이터부 만들기
    body = bytearray()
    new_offs = []
    for s in strs:
        new_offs.append(len(body))
        b = s.encode('utf-8')
        body += enc_len(len(s)) + enc_len(len(b)) + b + b'\x00'
    while len(body) % 4:
        body += b'\x00'

    new_str_start = hdr_size + 4 * cnt
    styles = b''
    if style_cnt:
        styles = data[pool_off + style_start:pool_off + size]
    head = bytearray(data[pool_off:pool_off + hdr_size])
    struct.pack_into('<I', head, 20, new_str_start)
    struct.pack_into('<I', head, 24,
                     (new_str_start + len(body)) if style_cnt else 0)
    out = bytes(head) + b''.join(struct.pack('<I', o) for o in new_offs) \
        + bytes(body) + styles
    struct.pack_into('<I', bytearray(out), 4, len(out))  # 자리표시
    out = bytearray(out)
    struct.pack_into('<I', out, 4, len(out))
    return bytes(out), len(out) - size


def main():
    src, dst, old, new = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    zin = zipfile.ZipFile(src)
    data = bytearray(zin.read('resources.arsc'))

    # 전역 문자열 풀은 테이블 헤더(8+4) 바로 뒤에 온다
    pool_off = u16(data, 2)
    newpool, delta = rewrite_pool(bytes(data), pool_off, old, new)
    out = bytearray(data[:pool_off]) + newpool \
        + data[pool_off + u32(data, pool_off + 4):]
    struct.pack_into('<I', out, 4, len(out))       # 테이블 전체 크기
    print('풀 크기 변화 %+d, arsc %d -> %d' % (delta, len(data), len(out)))

    if zipfile.is_zipfile(dst):
        pass
    zout = zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED)
    for info in zin.infolist():
        n = info.filename
        if n.startswith('META-INF/') and (
                n.upper().endswith(('.SF', '.RSA', '.DSA', '.EC'))
                or n == 'META-INF/MANIFEST.MF'):
            continue
        if n == 'resources.arsc':
            zout.writestr(info, bytes(out), info.compress_type)
        else:
            zout.writestr(info, zin.read(n), info.compress_type)
    zout.close()
    print('%s -> %s (앱 이름 %r -> %r)' % (src, dst, old, new))


if __name__ == '__main__':
    main()
