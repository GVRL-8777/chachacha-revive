# -*- coding: utf-8 -*-
"""NGUI UIAtlas(MonoBehaviour) 원시 바이트에서 스프라이트 표를 읽고 쓴다.

플레이어 빌드엔 사용자 스크립트 타입트리가 없어 정식 파싱이 안 된다.
실측한 구조는 이렇다.

    @32  스프라이트 개수(int)
    @36  배열 시작
    레코드 = int 이름길이 + 이름(4바이트 정렬) + payload 52바이트
             payload = outer 4f(16) + inner 4f(16) + int 5개(20)
    배열 뒤에 꼬리 16바이트

outer/inner 의 (x, y) 는 **텍스처 왼쪽 위**가 원점이다(픽셀 단위).
"""
import struct

HDR_COUNT = 32
ARRAY_AT = 36
PAYLOAD = 52


def records(blob):
    """[(이름, 이름오프셋, payload오프셋)] 을 순서대로 돌려준다."""
    n = struct.unpack_from('<i', blob, HDR_COUNT)[0]
    out = []
    off = ARRAY_AT
    for _ in range(n):
        ln = struct.unpack_from('<i', blob, off)[0]
        if not (0 < ln < 200) or off + 4 + ln > len(blob):
            break
        name = blob[off + 4:off + 4 + ln].decode('utf-8', 'replace')
        p = off + 4 + ln
        p += (-p) % 4
        out.append((name, off + 4, p))
        off = p + PAYLOAD
    return out


def payload(blob, p):
    """(outer, inner, ints) 로 푼다."""
    o = struct.unpack_from('<4f', blob, p)
    i = struct.unpack_from('<4f', blob, p + 16)
    v = struct.unpack_from('<5i', blob, p + 32)
    return o, i, v


def set_payload(blob, p, outer, inner, ints):
    struct.pack_into('<4f', blob, p, *outer)
    struct.pack_into('<4f', blob, p + 16, *inner)
    struct.pack_into('<5i', blob, p + 32, *ints)


def table(blob):
    """이름 -> (payload오프셋, outer, inner, ints)"""
    d = {}
    for name, _no, p in records(blob):
        o, i, v = payload(blob, p)
        d[name] = (p, o, i, v)
    return d
