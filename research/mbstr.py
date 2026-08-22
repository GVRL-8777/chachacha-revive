# -*- coding: utf-8 -*-
"""MonoBehaviour 데이터에서 길이 접두 문자열을 훑어 낸다.

플레이어 빌드에는 타입트리가 없어 MonoBehaviour 를 정식으로 못 읽는다.
그러나 유니티 직렬화 문자열은 `int32 길이 + UTF-8 바이트 + 4바이트 정렬` 이라
그 패턴만 훑어도 이름/스킬/설명 같은 알맹이는 거의 다 나온다.

사용법: python mbstr.py <파일> [최소길이]
"""
import io, os, re, struct, sys

path = sys.argv[1]
minlen = int(sys.argv[2]) if len(sys.argv) > 2 else 2
b = io.open(path, 'rb').read()

out, i, n = [], 0, len(b)
while i + 4 <= n:
    ln = struct.unpack_from('<i', b, i)[0]
    if 0 < ln <= 200 and i + 4 + ln <= n:
        raw = b[i + 4:i + 4 + ln]
        try:
            s = raw.decode('utf-8')
        except UnicodeDecodeError:
            i += 1
            continue
        # 인쇄 가능한 문자만(제어문자 제외)
        if len(s) >= minlen and not re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', s):
            out.append((i, s))
            i += 4 + ((ln + 3) & ~3)
            continue
    i += 1

print("문자열 %d개" % len(out))
for off, s in out:
    print("  %8d  %s" % (off, s))
