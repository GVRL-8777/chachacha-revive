# -*- coding: utf-8 -*-
"""
NetRecive.* 응답 클래스의 "키 -> 타입" 표를 IL 에서 통째로 뽑는다.

각 게터는 이런 모양이다:
    ldarg.0; ldfld <json>; ldc.i4 <N>; box eType; callvirt ToString; callvirt GetXxx
즉 **열거형 인덱스 N** 이 IL 상수로 박혀 있어서
api_schema.txt 의 eType 멤버 목록과 맞추면 키 이름을 얻고,
GetXxx 호출로 타입을 얻는다.

출력: api_types.json  {"NetRecive.X": {"키": "타입", ...}, ...}
"""
import sys, struct, re, json, io, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ilscan import Asm, _oplen

GET_TYPE = {
    "GetString": "string", "GetInt": "int", "GetFloat": "float",
    "GetLong": "long", "GetDouble": "double", "GetBoolean": "bool",
    "GetJSONObject": "object", "GetJSONArray": "array",
    "GetIntArray": "int[]", "GetStringArray": "string[]",
    "GetLongArray": "long[]", "GetDoubleArray": "double[]",
    "GetBooleanArray": "bool[]",
}

# ldc.i4 계열 -> 상수값
LDC = {i: i - 0x16 for i in range(0x16, 0x1F)}   # ldc.i4.0 .. ldc.i4.8


def enum_members(schema_path):
    """api_schema.txt -> {"NetRecive.X": [멤버...]}"""
    out, cur = {}, None
    for line in io.open(schema_path, encoding="utf-8", errors="replace"):
        m = re.match(r"^### (\S+)", line)
        if m:
            cur = m.group(1)
            continue
        m = re.match(r"^\s+(\S+)\.eType = (.+)$", line)
        if m and cur:
            out[m.group(1)] = [k.strip() for k in m.group(2).split(",")]
    return out


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    a = Asm(os.path.join(here, "mg", "Assembly-CSharp.dll"))
    a.parse()
    members = enum_members(os.path.join(here, "api_schema.txt"))

    getters = {}
    for i, nm in enumerate(a.memberrefs, start=1):
        if nm in GET_TYPE:
            getters[0x0A000000 | i] = nm
    for mi, (rva, nm) in enumerate(a.methods, start=1):
        own = a.owner[mi] if mi < len(a.owner) else ''
        if own == 'JSONObject' and nm in GET_TYPE:
            getters[0x06000000 | mi] = nm

    def body(rva):
        o = a.rva2off(rva); b = a.b; h = b[o]
        if (h & 3) == 2:
            return b[o + 1:o + 1 + (h >> 2)]
        if (h & 3) == 3:
            fs = struct.unpack_from('<H', b, o)[0]; hs = (fs >> 12) * 4
            sz = struct.unpack_from('<I', b, o + 4)[0]
            return b[o + hs:o + hs + sz]
        return b''

    result = {}
    for mi, (rva, name) in enumerate(a.methods, start=1):
        if not rva:
            continue
        own = a.owner[mi] if mi < len(a.owner) else ''
        if not own:
            continue
        # 소유 타입의 네임스페이스를 붙인 전체 이름을 찾는다
        try:
            code = body(rva)
        except Exception:
            continue
        last_const = None
        i = 0
        while i < len(code):
            op = code[i]
            if op in LDC:
                last_const = LDC[op]
            elif op == 0x1F and i + 2 <= len(code):        # ldc.i4.s
                last_const = code[i + 1]
            elif op == 0x20 and i + 5 <= len(code):        # ldc.i4
                last_const = struct.unpack_from('<i', code, i + 1)[0]
            elif op in (0x28, 0x6F) and i + 5 <= len(code):
                tok = struct.unpack_from('<I', code, i + 1)[0]
                if tok in getters and last_const is not None:
                    result.setdefault(own, {})[last_const] = GET_TYPE[tok in getters and getters[tok]]
                    last_const = None
            i += _oplen(code, i)

    # 인덱스 -> 키 이름
    typed = {}
    for cls, idxmap in result.items():
        # api_schema 의 키는 "NetRecive.X.eType" 형태이므로 뒤에서 맞춘다
        cand = [k for k in members if k.rsplit('.', 2)[-2] == cls] if '.' in cls else []
        if not cand:
            cand = [k for k in members if k.split('.')[-2] == cls]
        if not cand:
            continue
        names = members[cand[0]]
        m = {}
        for idx, t in sorted(idxmap.items()):
            if 0 <= idx < len(names) and names[idx] not in ("Count", "MaxCount"):
                m[names[idx]] = t
        if m:
            typed[cand[0].rsplit('.', 1)[0]] = m

    out = os.path.join(here, "api_types.json")
    io.open(out, "w", encoding="utf-8").write(
        json.dumps(typed, ensure_ascii=False, indent=1, sort_keys=True))
    print("타입 표 %d개 클래스 -> api_types.json" % len(typed))
    for k in sorted(typed)[:3]:
        print("  %s: %s" % (k, json.dumps(typed[k], ensure_ascii=False)[:200]))


if __name__ == '__main__':
    main()
