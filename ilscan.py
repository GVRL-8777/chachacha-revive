"""
.NET 어셈블리에서 '메서드별 문자열 리터럴'을 추출한다.

용도:
 1) 각 응답 핸들러가 실제로 읽는 JSON 필드명을 확인 -> 서버 DTO 와 버전 일치 검증
 2) httpServerIP 등 설정 키를 다루는 메서드를 찾아 패치 지점 특정

#~ 테이블 스트림을 파싱해 TypeDef/MethodDef 를 읽고, 각 메서드 IL 본문에서
ldstr(0x72) 오퍼랜드를 모아 #US 힙에서 해석한다.
"""
import struct, sys, re

def u8(b, o):  return b[o]
def u16(b, o): return struct.unpack_from('<H', b, o)[0]
def u32(b, o): return struct.unpack_from('<I', b, o)[0]

class Asm:
    def __init__(self, path):
        self.b = b = open(path, 'rb').read()
        pe = u32(b, 0x3c)
        nsec = u16(b, pe + 6)
        optsize = u16(b, pe + 20)
        opt = pe + 24
        magic = u16(b, opt)
        ddir = opt + (96 if magic == 0x10b else 112)
        self.secs = []
        so = opt + optsize
        for i in range(nsec):
            s = so + 40 * i
            _, vaddr, rsize, raddr = struct.unpack_from('<IIII', b, s + 8)
            vsize = u32(b, s + 8)
            self.secs.append((vaddr, vsize, raddr, rsize))
        cli = self.rva2off(u32(b, ddir + 14 * 8))
        md = self.rva2off(u32(b, cli + 8))
        self.md = md
        vlen = u32(b, md + 12)
        p = md + 16 + vlen + 2
        nstreams = u16(b, p); p += 2
        self.streams = {}
        for _ in range(nstreams):
            off, size = struct.unpack_from('<II', b, p); p += 8
            e = b.index(b'\0', p)
            self.streams[b[p:e].decode()] = (md + off, size)
            p = e + 1
            p = (p + 3) & ~3
        self._strings()
        self._tables()

    def rva2off(self, rva):
        for vaddr, vsize, raddr, rsize in self.secs:
            if vaddr <= rva < vaddr + max(vsize, rsize):
                return raddr + (rva - vaddr)
        raise ValueError('bad rva 0x%x' % rva)

    def _strings(self):
        b = self.b
        off, size = self.streams['#Strings']
        self.strheap = b[off:off + size]
        off, size = self.streams['#US']
        self.usheap = (off, size)

    def s(self, idx):
        e = self.strheap.index(b'\0', idx)
        return self.strheap[idx:e].decode('utf-8', 'replace')

    def us(self, idx):
        """#US 힙 인덱스 -> 문자열"""
        off, size = self.usheap
        b = self.b
        p = off + idx
        if p >= off + size: return None
        x = b[p]
        if x & 0x80 == 0:      n, p = x, p + 1
        elif x & 0xC0 == 0x80: n, p = ((x & 0x3f) << 8) | b[p+1], p + 2
        else:                  n, p = ((x & 0x1f) << 24) | (b[p+1] << 16) | (b[p+2] << 8) | b[p+3], p + 4
        if n == 0: return ''
        return b[p:p + n - 1].decode('utf-16-le', 'replace')

    def _tables(self):
        b = self.b
        off, _ = self.streams['#~']
        heapsizes = u8(b, off + 6)
        self.sS = 4 if heapsizes & 1 else 2   # #Strings 인덱스 크기
        self.sG = 4 if heapsizes & 2 else 2
        self.sB = 4 if heapsizes & 4 else 2
        valid = struct.unpack_from('<Q', b, off + 8)[0]
        p = off + 24
        self.rows = {}
        for i in range(64):
            if valid >> i & 1:
                self.rows[i] = u32(b, p); p += 4
        self.tstart = p

    def _idx(self, table):
        """단순 테이블 인덱스 크기"""
        return 4 if self.rows.get(table, 0) >= 0x10000 else 2

    def _coded(self, tables, bits):
        mx = max((self.rows.get(t, 0) for t in tables), default=0)
        return 4 if mx >= (1 << (16 - bits)) else 2

    def parse(self):
        b = self.b
        p = self.tstart
        sS, sB, sG = self.sS, self.sB, self.sG
        resscope = self._coded([0, 26, 35, 1], 2)      # ResolutionScope
        typedeforref = self._coded([2, 1, 27], 2)      # TypeDefOrRef
        iField = self._idx(4)
        iMethod = self._idx(6)

        # --- table 0: Module ---
        if 0 in self.rows:
            p += self.rows[0] * (2 + sS + 3 * sG)
        # --- table 1: TypeRef ---
        if 1 in self.rows:
            p += self.rows[1] * (resscope + 2 * sS)
        # --- table 2: TypeDef ---
        typedefs = []
        if 2 in self.rows:
            rsz = 4 + 2 * sS + typedeforref + iField + iMethod
            for i in range(self.rows[2]):
                o = p + i * rsz
                name_i = u32(b, o + 4) if sS == 4 else u16(b, o + 4)
                ns_i = u32(b, o + 4 + sS) if sS == 4 else u16(b, o + 4 + sS)
                fo = o + 4 + 2 * sS + typedeforref
                flist = u32(b, fo) if iField == 4 else u16(b, fo)
                mo = fo + iField
                mlist = u32(b, mo) if iMethod == 4 else u16(b, mo)
                typedefs.append((self.s(ns_i), self.s(name_i), mlist, flist))
            p += self.rows[2] * rsz
        # --- table 3: FieldPtr ---
        if 3 in self.rows:
            p += self.rows[3] * self._idx(4)
        # --- table 4: Field ---
        fields = []
        if 4 in self.rows:
            rsz = 2 + sS + sB
            for i in range(self.rows[4]):
                o = p + i * rsz
                flags = u16(b, o)
                name_i = u32(b, o + 2) if sS == 4 else u16(b, o + 2)
                fields.append((flags, self.s(name_i)))
            p += self.rows[4] * rsz
        self.fields = fields
        # --- table 5: MethodPtr ---
        if 5 in self.rows:
            p += self.rows[5] * self._idx(6)
        # --- table 6: MethodDef ---
        methods = []
        if 6 in self.rows:
            iParam = self._idx(8)
            rsz = 4 + 2 + 2 + sS + sB + iParam
            for i in range(self.rows[6]):
                o = p + i * rsz
                rva = u32(b, o)
                name_i = u32(b, o + 8) if sS == 4 else u16(b, o + 8)
                methods.append((rva, self.s(name_i)))
            p += self.rows[6] * rsz
        # --- table 7: ParamPtr / 8: Param / 9: InterfaceImpl ---
        if 7 in self.rows:
            p += self.rows[7] * self._idx(8)
        if 8 in self.rows:
            p += self.rows[8] * (2 + 2 + sS)
        if 9 in self.rows:
            p += self.rows[9] * (self._idx(2) + self._coded([2, 1, 27], 2))
        # --- table 10: MemberRef (호출 대상 이름 해석용) ---
        memberrefs = []
        if 10 in self.rows:
            mrp = self._coded([2, 1, 26, 6, 27], 3)   # MemberRefParent
            rsz = mrp + sS + sB
            for i in range(self.rows[10]):
                o = p + i * rsz
                name_i = u32(b, o + mrp) if sS == 4 else u16(b, o + mrp)
                memberrefs.append(self.s(name_i))
        self.memberrefs = memberrefs
        self.typedefs = typedefs
        self.methods = methods

        # 메서드 -> 소유 타입 매핑 (MethodList 는 1-based, 다음 타입까지가 범위)
        owner = [''] * (len(methods) + 1)
        for i, (ns, nm, mlist, flist) in enumerate(typedefs):
            end = typedefs[i + 1][2] if i + 1 < len(typedefs) else len(methods) + 1
            full = (ns + '.' + nm) if ns else nm
            for mi in range(mlist, end):
                if 1 <= mi <= len(methods):
                    owner[mi] = full
        self.owner = owner

        # 타입 -> 인스턴스 필드 목록 (FieldList 범위)
        self.type_fields = {}
        for i, (ns, nm, mlist, flist) in enumerate(typedefs):
            end = typedefs[i + 1][3] if i + 1 < len(typedefs) else len(fields) + 1
            full = (ns + '.' + nm) if ns else nm
            names = []
            for fi in range(flist, end):
                if 1 <= fi <= len(fields):
                    flags, fname = fields[fi - 1]
                    if flags & 0x10:      # static 제외 -> 인스턴스 필드만
                        continue
                    names.append(fname)
            self.type_fields[full] = names

    def literals(self, rva):
        """메서드 IL 본문에서 ldstr 문자열 수집"""
        if rva == 0: return []
        try: o = self.rva2off(rva)
        except ValueError: return []
        b = self.b
        hdr = b[o]
        if (hdr & 3) == 2:                       # tiny
            size = hdr >> 2
            code = b[o + 1:o + 1 + size]
        elif (hdr & 3) == 3:                     # fat
            flags_size = u16(b, o)
            hsize = (flags_size >> 12) * 4
            size = u32(b, o + 4)
            code = b[o + hsize:o + hsize + size]
        else:
            return []
        out = []
        i = 0
        n = len(code)
        while i < n:
            op = code[i]
            if op == 0x72 and i + 5 <= n:        # ldstr <token>
                tok = struct.unpack_from('<I', code, i + 1)[0]
                if tok >> 24 == 0x70:
                    v = self.us(tok & 0xFFFFFF)
                    if v: out.append(v)
                i += 5
                continue
            i += _oplen(code, i)
        return out


# --- IL 오퍼랜드 크기 테이블 (ECMA-335 기준) ---
# 1바이트 오퍼랜드: 짧은 분기, 짧은 지역/인자 접근, ldc.i4.s
_OP1 = set(range(0x2B, 0x38)) | {0x0E, 0x0F, 0x10, 0x11, 0x12, 0x13, 0x1F, 0xDE}
# 4바이트 오퍼랜드: 긴 분기, 토큰(메서드/타입/필드/문자열), ldc.i4, ldc.r4
_OP4 = set(range(0x38, 0x45)) | {
    0x20, 0x22, 0x28, 0x29, 0x6F, 0x70, 0x71, 0x72, 0x73, 0x74, 0x75, 0x79,
    0x7B, 0x7C, 0x7D, 0x7E, 0x7F, 0x80, 0x81, 0x8C, 0x8D, 0x8F, 0x90,
    0xA3, 0xA4, 0xA5, 0xC2, 0xC6, 0xD0,
}
# 8바이트 오퍼랜드: ldc.i8, ldc.r8
_OP8 = {0x21, 0x23}
# 0xFE 접두 2바이트 오퍼랜드(ldarg/ldloc 계열)
_FE_OP2 = {0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E}
# 0xFE 접두 4바이트 오퍼랜드(ldftn/ldvirtftn/initobj/constrained/sizeof 등)
_FE_OP4 = {0x06, 0x07, 0x15, 0x16, 0x1C, 0x1D}

def _oplen(code, i):
    """code[i] 위치 명령의 전체 길이(오퍼랜드 포함)를 반환."""
    op = code[i]
    if op == 0xFE:
        op2 = code[i + 1] if i + 1 < len(code) else 0
        if op2 in _FE_OP4: return 6
        if op2 in _FE_OP2: return 4
        return 2
    if op in _OP1: return 2
    if op in _OP4: return 5
    if op in _OP8: return 9
    if op == 0x45:                       # switch: count + count*int32
        if i + 5 > len(code): return 1
        cnt = struct.unpack_from('<I', code, i + 1)[0]
        return 5 + 4 * cnt
    return 1


if __name__ == '__main__':
    a = Asm(sys.argv[1])
    a.parse()

    # --types <정규식> : 타입의 인스턴스 필드 목록 출력 (= LitJSON 이 기대하는 JSON 스키마)
    if len(sys.argv) > 2 and sys.argv[1 + 1] == '--types':
        tp = re.compile(sys.argv[3], re.I) if len(sys.argv) > 3 else re.compile('.')
        n = 0
        for full, names in sorted(a.type_fields.items()):
            if not tp.search(full) or not names:
                continue
            n += 1
            print('==== %s  (%d fields)' % (full, len(names)))
            for f in names:
                print('       %s' % f)
        print('\n[%d types matched]' % n)
        sys.exit(0)

    pat = re.compile(sys.argv[2], re.I) if len(sys.argv) > 2 else None
    hits = 0
    for mi, (rva, name) in enumerate(a.methods, start=1):
        lits = a.literals(rva)
        if not lits: continue
        own = a.owner[mi] if mi < len(a.owner) else ''
        full = own + '::' + name
        if pat and not (pat.search(full) or any(pat.search(l) for l in lits)):
            continue
        hits += 1
        print('=' * 4, full)
        for l in lits:
            print('      ', repr(l))
    print('\n[%d methods matched, %d types, %d methods total]'
          % (hits, len(a.typedefs), len(a.methods)))
