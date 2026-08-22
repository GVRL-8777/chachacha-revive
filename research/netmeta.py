# .NET PE 파일의 메타데이터 스트림을 직접 파싱한다.
import sys, struct

def compressed_uint(b, o):
    x = b[o]
    if x & 0x80 == 0:      return x, o+1
    if x & 0xC0 == 0x80:   return ((x & 0x3f) << 8) | b[o+1], o+2
    return ((x & 0x1f) << 24) | (b[o+1] << 16) | (b[o+2] << 8) | b[o+3], o+4

def load(path):
    b = open(path, 'rb').read()
    pe = struct.unpack_from('<I', b, 0x3c)[0]
    assert b[pe:pe+4] == b'PE\0\0', 'not a PE'
    nsec = struct.unpack_from('<H', b, pe+6)[0]
    optsize = struct.unpack_from('<H', b, pe+20)[0]
    opt = pe + 24
    magic = struct.unpack_from('<H', b, opt)[0]
    ddir = opt + (96 if magic == 0x10b else 112)
    secs = []
    so = opt + optsize
    for i in range(nsec):
        s = so + 40*i
        name = b[s:s+8].rstrip(b'\0').decode()
        vsize, vaddr, rsize, raddr = struct.unpack_from('<IIII', b, s+8)
        secs.append((name, vaddr, vsize, raddr, rsize))
    def rva2off(rva):
        for name, va, vs, ra, rs in secs:
            if va <= rva < va + max(vs, rs):
                return ra + (rva - va)
        raise ValueError('bad rva %x' % rva)
    cli_rva = struct.unpack_from('<I', b, ddir + 14*8)[0]
    cli = rva2off(cli_rva)
    md_rva, md_size = struct.unpack_from('<II', b, cli + 8)
    md = rva2off(md_rva)
    assert b[md:md+4] == b'BSJB', 'no metadata root'
    vlen = struct.unpack_from('<I', b, md+12)[0]
    p = md + 16 + vlen
    ver = b[md+16:md+16+vlen].rstrip(b'\0').decode('utf-8','replace')
    p += 2  # flags
    nstreams = struct.unpack_from('<H', b, p)[0]; p += 2
    streams = {}
    for i in range(nstreams):
        off, size = struct.unpack_from('<II', b, p); p += 8
        e = b.index(b'\0', p)
        nm = b[p:e].decode()
        p = e + 1
        p = (p + 3) & ~3
        streams[nm] = (md + off, size)
    return b, ver, streams

b, ver, streams = load(sys.argv[1])
mode = sys.argv[2] if len(sys.argv) > 2 else 'us'
sys.stderr.write("Runtime: %s   streams: %s\n" % (ver, list(streams)))

if mode == 'us' and '#US' in streams:
    off, size = streams['#US']
    p = off + 1
    end = off + size
    out = []
    while p < end:
        n, p2 = compressed_uint(b, p)
        if n == 0:
            p = p2
            continue
        s = b[p2:p2+n-1].decode('utf-16-le', 'replace')
        out.append(s)
        p = p2 + n
    seen = set()
    for s in out:
        if s and s not in seen:
            seen.add(s)
            print(s)

if mode == 'names' and '#Strings' in streams:
    off, size = streams['#Strings']
    raw = b[off:off+size]
    seen = set()
    for part in raw.split(b'\0'):
        if len(part) >= 3:
            s = part.decode('utf-8', 'replace')
            if s not in seen:
                seen.add(s)
                print(s)
