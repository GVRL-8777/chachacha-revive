# -*- coding: utf-8 -*-
"""메서드 하나를 분기 목적지까지 붙여 IL 로 푼다.

  python ildump.py <dll> <타입> <메서드> [최대바이트]
"""
import struct
import sys

sys.path.insert(0, '.')
import ildis
from ilscan import Asm, _oplen

BR4 = {0x38: 'br', 0x39: 'brfalse', 0x3a: 'brtrue', 0x3b: 'beq', 0x3c: 'bge',
       0x3d: 'bgt', 0x3e: 'ble', 0x3f: 'blt', 0x40: 'bne.un', 0x41: 'bge.un',
       0x42: 'bgt.un', 0x43: 'ble.un', 0x44: 'blt.un'}
BR1 = {0x2b: 'br.s', 0x2c: 'brfalse.s', 0x2d: 'brtrue.s', 0x2e: 'beq.s',
       0x2f: 'bge.s', 0x30: 'bgt.s', 0x31: 'ble.s', 0x32: 'blt.s',
       0x33: 'bne.un.s', 0x34: 'bge.un.s', 0x35: 'bgt.un.s', 0x36: 'ble.un.s',
       0x37: 'blt.un.s'}
TOKOPS = (0x28, 0x6f, 0x73, 0x74, 0x75, 0x7b, 0x7d, 0x7e, 0x80, 0x8c, 0xa5, 0x72)


def body(a, rva):
    off = a.rva2off(rva)
    b = a.b
    h = b[off]
    if h & 3 == 2:
        return b[off + 1:off + 1 + (h >> 2)]
    size = struct.unpack_from('<I', b, off + 4)[0]
    hs = (struct.unpack_from('<H', b, off)[0] >> 12) * 4
    return b[off + hs:off + hs + size]


def dis(a, owner, name, limit=100000):
    n = 0
    for i, (rva, nm) in enumerate(a.methods):
        if not rva or nm != name or (owner and a.owner[i] != owner):
            continue
        il = body(a, rva)
        print('=== %s::%s (%d바이트)' % (a.owner[i], nm, len(il)))
        j = 0
        while j < len(il) and j < limit:
            c = il[j]
            ln = _oplen(il, j)
            if c in BR4:
                ex = '%s -> %04X' % (BR4[c], j + ln + struct.unpack_from('<i', il, j + 1)[0])
            elif c in BR1:
                ex = '%s -> %04X' % (BR1[c], j + ln + struct.unpack_from('<b', il, j + 1)[0])
            elif c in TOKOPS:
                ex = ildis.NAMES.get(c, hex(c)) + ' ' + ildis.token_name(
                    a, struct.unpack_from('<I', il, j + 1)[0])
            elif c == 0x1f:
                ex = 'ldc.i4.s %d' % il[j + 1]
            elif c == 0x20:
                ex = 'ldc.i4 %d' % struct.unpack_from('<i', il, j + 1)[0]
            else:
                ex = ildis.NAMES.get(c, hex(c))
            print('%04X %s' % (j, ex))
            j += ln
        print()
        n += 1
    if not n:
        print('없음: %s::%s' % (owner, name))


if __name__ == '__main__':
    a = Asm(sys.argv[1])
    a.parse()
    dis(a, sys.argv[2] or None, sys.argv[3],
        int(sys.argv[4]) if len(sys.argv) > 4 else 100000)
