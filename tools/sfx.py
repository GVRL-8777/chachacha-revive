# -*- coding: utf-8 -*-
"""Unity 4 SerializedFile 의 외부참조(externals) 를 읽는다.

이 배포판의 Data/ 밑 자산은 전부 32자리 16진수 이름을 가진 SerializedFile 이고,
서로를 가리킬 때 메타데이터 영역에 그 이름을 ASCII 로 그대로 적어 둔다.
이름 길이가 항상 32자로 같으므로 제자리 치환이 안전하다.
"""
import os, re, struct

HEX32 = re.compile(rb'(?<![0-9a-fA-F])[0-9a-f]{32}(?![0-9a-fA-F])')


def header(data):
    """(metadataSize, fileSize, version, dataOffset)"""
    return struct.unpack('>IIII', data[:16])


def externals(data):
    """[(오프셋, 이름)] — 메타데이터 영역에 적힌 참조 대상들."""
    ms, fs, ver, do = header(data)
    end = min(20 + ms, len(data))
    out = []
    for m in HEX32.finditer(data, 20, end):
        out.append((m.start(), m.group().decode('ascii')))
    return out


def scan(d):
    """디렉터리의 GUID 파일들을 {이름: (경로, 크기, [참조])} 로."""
    g = {}
    for n in os.listdir(d):
        if len(n) != 32 or not re.fullmatch(r'[0-9a-f]{32}', n):
            continue
        p = os.path.join(d, n)
        if not os.path.isfile(p):
            continue
        data = open(p, 'rb').read()
        try:
            refs = [x[1] for x in externals(data)]
        except Exception:
            refs = []
        g[n] = (p, len(data), refs)
    return g


if __name__ == '__main__':
    import sys
    D = sys.argv[1] if len(sys.argv) > 1 else 'x77/assets/bin/Data'
    g = scan(D)
    nref = sum(len(v[2]) for v in g.values())
    dangling = set()
    for n, (p, s, refs) in g.items():
        for r in refs:
            if r not in g:
                dangling.add(r)
    print("자산 %d개, 참조 %d개, 대상 없는 참조 %d개" % (len(g), nref, len(dangling)))
    for r in sorted(dangling)[:20]:
        print("   끊긴 참조:", r)
