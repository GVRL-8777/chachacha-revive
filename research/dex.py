# DEX 파일 머리와 문자열 표를 직접 읽는다.
import sys, struct

def uleb(b, o):
    r=0; s=0
    while True:
        x=b[o]; o+=1
        r |= (x&0x7f)<<s
        if not (x&0x80): break
        s+=7
    return r,o

b=open(sys.argv[1],'rb').read()
print("DEX magic:", b[:8])
string_ids_size, string_ids_off = struct.unpack_from('<II', b, 56)
type_ids_size, type_ids_off = struct.unpack_from('<II', b, 64)
proto_ids_size, proto_ids_off = struct.unpack_from('<II', b, 72)
field_ids_size, field_ids_off = struct.unpack_from('<II', b, 80)
method_ids_size, method_ids_off = struct.unpack_from('<II', b, 88)
class_defs_size, class_defs_off = struct.unpack_from('<II', b, 96)
print("strings=%d types=%d methods=%d classes=%d" % (string_ids_size, type_ids_size, method_ids_size, class_defs_size))

strings=[]
for i in range(string_ids_size):
    off = struct.unpack_from('<I', b, string_ids_off+4*i)[0]
    n,p = uleb(b, off)
    e = b.index(b'\x00', p)
    strings.append(b[p:e].decode('utf-8','replace'))

types = [strings[struct.unpack_from('<I',b,type_ids_off+4*i)[0]] for i in range(type_ids_size)]

# defined classes
defined=[]
for i in range(class_defs_size):
    ti = struct.unpack_from('<I', b, class_defs_off+32*i)[0]
    defined.append(types[ti])

# methods (class, name)
methods=[]
for i in range(method_ids_size):
    ci, pi, ni = struct.unpack_from('<HHI', b, method_ids_off+8*i)
    methods.append((types[ci], strings[ni]))

mode = sys.argv[2] if len(sys.argv)>2 else 'all'
if mode in ('all','classes'):
    print("\n===== DEFINED CLASSES (%d) =====" % len(defined))
    for c in sorted(defined): print(c)
if mode in ('all','methods'):
    print("\n===== EXTERNAL/ALL METHOD REFS =====")
    seen=set()
    for c,n in methods:
        k=c+'->'+n
        if k not in seen:
            seen.add(k); print(k)
if mode in ('all','strings'):
    print("\n===== STRINGS (%d) =====" % len(strings))
    for s in strings: print(repr(s))
