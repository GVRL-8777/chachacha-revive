# -*- coding: utf-8 -*-
"""NGUI UIAtlas(MonoBehaviour) 원시 바이트에서 스프라이트 표를 읽고 쓴다.

플레이어 빌드엔 사용자 스크립트 타입트리가 없어 정식 파싱이 안 된다.
실측한 구조는 이렇다.

    @32  스프라이트 개수(int)
    @36  배열 시작
    레코드 = int 이름길이 + 이름(4바이트 정렬) + payload
    배열 뒤에 꼬리 16바이트

payload 는 **판마다 다르다.**

    유니티 4.1.5 (차차차 CN · 우리 빌드)   52바이트 = outer 4f + inner 4f + int 5개
    유니티 3.5.6 (다함께 차차차 한국판 1.2.3) 48바이트 = outer 4f + inner 4f + int 4개

NGUI 가 중간에 int 하나(padding 계열)를 늘렸다. 그래서 크기를 못 박지 않고
**레코드를 끝까지 훑어 딱 맞아떨어지는 쪽**을 고른다.

outer/inner 의 (x, y) 는 **텍스처 왼쪽 위**가 원점이다(픽셀 단위).
"""
import struct

HDR_COUNT = 32
ARRAY_AT = 36
PAYLOAD = 52            # 예전 코드가 쓰던 기본값 (유니티 4)
SIZES = (52, 48)        # 아는 판들. 앞에 있는 것부터 맞춰 본다.
TAIL = 16

_PRINTABLE = set(range(0x20, 0x7f))


def _walk(blob, size):
    """이 payload 크기로 끝까지 읽히면 (레코드들, 끝오프셋), 아니면 None."""
    if HDR_COUNT + 4 > len(blob):
        return None
    (n,) = struct.unpack_from('<i', blob, HDR_COUNT)
    if not (0 <= n <= 5000):
        return None
    out = []
    off = ARRAY_AT
    for _ in range(n):
        if off + 4 > len(blob):
            return None
        (ln,) = struct.unpack_from('<i', blob, off)
        if not (0 < ln < 200) or off + 4 + ln > len(blob):
            return None
        raw = blob[off + 4:off + 4 + ln]
        if not all(c in _PRINTABLE for c in raw):
            return None
        p = off + 4 + ln
        p += (-p) % 4
        if p + size > len(blob):
            return None
        out.append((raw.decode('utf-8', 'replace'), off + 4, p))
        off = p + size
    return out, off


def layout(blob):
    """이 아틀라스의 payload 크기를 알아낸다. 못 찾으면 None."""
    best = None
    for size in SIZES:
        got = _walk(blob, size)
        if not got:
            continue
        _recs, end = got
        tail = len(blob) - end
        if tail < 0:
            continue
        # 꼬리가 16바이트인 것이 정답. 아니면 가장 가까운 것을 후보로 둔다.
        score = abs(tail - TAIL)
        if best is None or score < best[0]:
            best = (score, size)
        if score == 0:
            break
    return best[1] if best else None


def records(blob, size=None):
    """[(이름, 이름오프셋, payload오프셋)] 을 순서대로 돌려준다."""
    size = size or layout(blob)
    if size is None:
        return []
    got = _walk(blob, size)
    return got[0] if got else []


def payload(blob, p, size=None):
    """(outer, inner, ints) 로 푼다. ints 는 판에 따라 4개 또는 5개."""
    size = size or PAYLOAD
    o = struct.unpack_from('<4f', blob, p)
    i = struct.unpack_from('<4f', blob, p + 16)
    k = (size - 32) // 4
    v = struct.unpack_from('<%di' % k, blob, p + 32)
    return o, i, v


def set_payload(blob, p, outer, inner, ints):
    struct.pack_into('<4f', blob, p, *outer)
    struct.pack_into('<4f', blob, p + 16, *inner)
    struct.pack_into('<%di' % len(ints), blob, p + 32, *ints)


def table(blob):
    """이름 -> (payload오프셋, outer, inner, ints)"""
    size = layout(blob)
    if size is None:
        return {}
    d = {}
    for name, _no, p in records(blob, size):
        o, i, v = payload(blob, p, size)
        d[name] = (p, o, i, v)
    return d
