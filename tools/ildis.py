"""
특정 메서드의 IL 을 토큰 해석까지 붙여 출력한다.

목적: AssetCatalogue JSON 의 정확한 접근 경로를 읽어낸다.
  ldstr "Catalogue" / callvirt get_Item / ldstr "PatchList" ... 형태의 체인을 보면
  root["Catalogue"]["PatchList"] 인지 root["PatchList"] 인지가 확정된다.

사용법: python ildis.py <dll> <메서드명 정규식> [최대명령수]
"""
import sys, struct, re
sys.path.insert(0, ".")
from ilscan import Asm, _oplen

# 관심 있는 오پ코드만 이름을 붙인다 (나머지는 0xNN 로 표시)
NAMES = {
    0x00: 'nop', 0x02: 'ldarg.0', 0x03: 'ldarg.1', 0x04: 'ldarg.2', 0x05: 'ldarg.3',
    0x06: 'ldloc.0', 0x07: 'ldloc.1', 0x08: 'ldloc.2', 0x09: 'ldloc.3',
    0x0A: 'stloc.0', 0x0B: 'stloc.1', 0x0C: 'stloc.2', 0x0D: 'stloc.3',
    0x11: 'ldloc.s', 0x13: 'stloc.s', 0x12: 'ldloca.s',
    0x14: 'ldnull', 0x16: 'ldc.i4.0', 0x17: 'ldc.i4.1', 0x1F: 'ldc.i4.s', 0x20: 'ldc.i4',
    0x25: 'dup', 0x26: 'pop',
    0x28: 'call', 0x6F: 'callvirt', 0x73: 'newobj', 0x72: 'ldstr',
    0x74: 'castclass', 0x75: 'isinst', 0x7B: 'ldfld', 0x7D: 'stfld',
    0x7E: 'ldsfld', 0x80: 'stsfld', 0x8C: 'box', 0xA5: 'unbox.any',
    0x2A: 'ret', 0x2B: 'br.s', 0x2C: 'brfalse.s', 0x2D: 'brtrue.s',
    0x38: 'br', 0x39: 'brfalse', 0x3A: 'brtrue',
}


def token_name(a, tok):
    tbl, idx = tok >> 24, tok & 0xFFFFFF
    if tbl == 0x70:                     # UserString
        v = a.us(idx)
        return '"%s"' % v if v is not None else '<us?>'
    if tbl == 0x0A:                     # MemberRef
        if 1 <= idx <= len(a.memberrefs):
            return a.memberrefs[idx - 1]
    if tbl == 0x06:                     # MethodDef
        if 1 <= idx <= len(a.methods):
            own = a.owner[idx] if idx < len(a.owner) else ''
            return (own + '::' if own else '') + a.methods[idx - 1][1]
    if tbl == 0x02:                     # TypeDef
        if 1 <= idx <= len(a.typedefs):
            ns, nm, _, _ = a.typedefs[idx - 1]
            return (ns + '.' if ns else '') + nm
    return '0x%08x' % tok


def body(a, rva):
    o = a.rva2off(rva)
    b = a.b
    h = b[o]
    if (h & 3) == 2:
        return b[o + 1:o + 1 + (h >> 2)]
    if (h & 3) == 3:
        fs = struct.unpack_from('<H', b, o)[0]
        hs = (fs >> 12) * 4
        size = struct.unpack_from('<I', b, o + 4)[0]
        return b[o + hs:o + hs + size]
    return b''


def main():
    a = Asm(sys.argv[1]); a.parse()
    pat = re.compile(sys.argv[2], re.I)
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 400
    for mi, (rva, name) in enumerate(a.methods, start=1):
        if not rva:
            continue
        full = (a.owner[mi] + '::' if mi < len(a.owner) and a.owner[mi] else '') + name
        if not pat.search(full):
            continue
        code = body(a, rva)
        print('=' * 70)
        print(full, ' (%d bytes IL)' % len(code))
        print('=' * 70)
        i = n = 0
        while i < len(code) and n < limit:
            op = code[i]
            ln = _oplen(code, i)
            nm = NAMES.get(op, '0x%02X' % op)
            operand = ''
            if ln == 5 and op in (0x28, 0x6F, 0x73, 0x72, 0x74, 0x75, 0x7B, 0x7D,
                                  0x7E, 0x80, 0x8C, 0xA5):
                tok = struct.unpack_from('<I', code, i + 1)[0]
                operand = ' ' + token_name(a, tok)
            elif ln == 5 and op == 0x20:
                operand = ' %d' % struct.unpack_from('<i', code, i + 1)[0]
            elif ln == 2 and op in (0x1F, 0x11, 0x13, 0x12):
                operand = ' %d' % code[i + 1]
            # JSON 접근 체인을 눈에 띄게
            mark = ''
            if op == 0x72: mark = '   <<<'
            elif operand.strip() in ('get_Item', 'ContainsKey', 'get_Count', 'IsArray', 'IsObject'):
                mark = '   <<<'
            print('  %04X  %-10s%s%s' % (i, nm, operand, mark))
            i += ln
            n += 1
        if n >= limit:
            print('  ... (%d 명령에서 절단)' % limit)
        print()


if __name__ == '__main__':
    main()
