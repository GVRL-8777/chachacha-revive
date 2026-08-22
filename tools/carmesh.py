# -*- coding: utf-8 -*-
"""새 자동차의 메시를 만든다. (태극호)

사진 한 장에서 읽은 실루엣을 파라미터로 옮겼다 — 낮고 긴 쐐기형 몸체에
가운데가 솟은 캐빈, 네 바퀴. 저폴리곤이지만 형태는 알아볼 수 있다.

**좌표계**는 중국판 차 메시를 그대로 따른다(람보르기니 AABB 로 실측).
  x = 좌우 (-0.56 ~ +0.56)
  y = 앞뒤 (-0.52 뒤 ~ +1.46 앞)   ← 길이축이 Y 다
  z = 높이 (0 ~ 0.52)
맵과 마찬가지로 씬 전체가 -90°X 로 눕혀져 있어 이렇게 된다.

UV 는 256x256 텍스처의 세 구역을 가리킨다.
  왼쪽 위  = 흰색 차체
  오른쪽 위 = 검은색 하단·유리
  아래 절반 = 태극 문양 (문짝에 붙는다)
"""
import math

# 텍스처 구역 (u, v) — 가운데 점을 찍어 단색으로 쓴다
UV_WHITE = (0.25, 0.75)
UV_BLACK = (0.75, 0.75)
UV_GLASS = (0.75, 0.60)
# 앞/뒤 마감면 그래픽 영역 (u0, v0, u1, v1) — 텍스처 왼쪽 위 사분면의 빈 구석
UV_NOSE_RECT = (0.02, 0.52, 0.23, 0.70)
UV_TAIL_RECT = (0.27, 0.52, 0.48, 0.70)
UV_WHEEL = (0.60, 0.90)   # 휠(밝은 회색)
# 태극 구역은 네 귀퉁이를 쓴다
UV_MARK = ((0.10, 0.05), (0.90, 0.05), (0.90, 0.45), (0.10, 0.45))

# 옆에서 본 단면: (y, 반폭, 바닥z, 지붕z)
PROFILE = [
    (-0.52, 0.44, 0.115, 0.30),   # 꼬리
    (-0.36, 0.52, 0.105, 0.35),
    (-0.10, 0.56, 0.100, 0.44),
    (0.16, 0.56, 0.100, 0.52),    # 지붕 꼭대기
    (0.44, 0.55, 0.100, 0.50),
    (0.72, 0.53, 0.105, 0.40),
    (1.02, 0.49, 0.110, 0.28),
    (1.28, 0.42, 0.120, 0.20),
    (1.46, 0.28, 0.130, 0.16),    # 코끝
]

# 바퀴가 차체 밑으로 큼직하게 보여야 이 게임 차량답다.
WHEELS = [(-0.50, 1.00), (0.50, 1.00), (-0.50, -0.22), (0.50, -0.22)]
WHEEL_R = 0.19
WHEEL_W = 0.13
WHEEL_SEG = 12


class Mesh(object):
    def __init__(self):
        self.v = []      # (x, y, z)
        self.uv = []     # (u, v)
        self.t = []      # 삼각형 인덱스

    def add(self, pos, uv):
        self.v.append(pos)
        self.uv.append(uv)
        return len(self.v) - 1

    def quad(self, p0, p1, p2, p3, uv, uvs=None):
        """네 점 순서는 자유. 감기(winding)는 orient()가 바깥쪽으로 맞춘다."""
        q = uvs or (uv, uv, uv, uv)
        a = self.add(p0, q[0])
        b = self.add(p1, q[1])
        c = self.add(p2, q[2])
        d = self.add(p3, q[3])
        self.t += [a, b, c, a, c, d]

    def tri(self, p0, p1, p2, uv, uvs=None):
        q = uvs or (uv, uv, uv)
        a = self.add(p0, q[0])
        b = self.add(p1, q[1])
        c = self.add(p2, q[2])
        self.t += [a, b, c]


def _orient(m):
    """모든 삼각형의 앞면이 차 바깥을 향하게 맞춘다.

    유니티에서 카메라를 향하는 앞면은, 정점 (t0,t1,t2) 에 대해
    cross(t1-t0, t2-t0) 가 카메라 쪽(=바깥쪽)을 향하는 순서다.
    감기가 틀린 면은 안쪽만 보여서, 옆에서 보면 멀쩡한데
    위에서 보면 바닥 안쪽(검정)이 보이는 개판이 난다(실기 확인).
    기준점: 바퀴 삼각형은 제 바퀴 중심, 몸통은 차 중심축."""
    def sub(a, b):
        return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

    def cross(a, b):
        return (a[1] * b[2] - a[2] * b[1],
                a[2] * b[0] - a[0] * b[2],
                a[0] * b[1] - a[1] * b[0])

    def dot(a, b):
        return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

    for k in range(0, len(m.t), 3):
        a, b, c = m.t[k], m.t[k + 1], m.t[k + 2]
        pa, pb, pc = m.v[a], m.v[b], m.v[c]
        cx = (pa[0] + pb[0] + pc[0]) / 3.0
        cy = (pa[1] + pb[1] + pc[1]) / 3.0
        cz = (pa[2] + pb[2] + pc[2]) / 3.0
        ref = None
        for wx, wy in WHEELS:
            if abs(cy - wy) <= WHEEL_R + 0.02 and abs(cx) >= 0.30                     and cz <= WHEEL_R * 2 + 0.02:
                ref = (wx, wy, WHEEL_R)
                break
        if ref is None:
            ref = (0.0, min(1.30, max(-0.40, cy)), 0.26)
        out = (cx - ref[0], cy - ref[1], cz - ref[2])
        n = cross(sub(pb, pa), sub(pc, pa))
        if dot(n, out) < 0:
            m.t[k + 1], m.t[k + 2] = m.t[k + 2], m.t[k + 1]


def _ring(y, hw, z0, z1):
    """단면 하나. 아래에서 위로 네 단: 바닥 · 스커트 · 벨트라인 · 지붕."""
    h = z1 - z0
    inset = hw * 0.74            # 지붕은 좁힌다(쐐기 느낌)
    belt = hw * 0.99
    return {
        'bl': (-hw, y, z0), 'br': (hw, y, z0),                     # 바닥
        'sl': (-hw, y, z0 + h * 0.17), 'sr': (hw, y, z0 + h * 0.17),  # 스커트 끝
        'ml': (-belt, y, z0 + h * 0.58), 'mr': (belt, y, z0 + h * 0.58),  # 벨트라인
        'tl': (-inset, y, z1), 'tr': (inset, y, z1),               # 지붕
    }


def build():
    m = Mesh()
    rings = [_ring(*p) for p in PROFILE]

    # 태극을 붙일 문짝 구간(옆면 벨트 아래). 앞뒤로 두 칸 쓴다.
    door = (4, 4)     # 한 칸에만 붙인다. 두 칸이면 태극이 두 개 찍힌다
    cabin = (2, 5)               # 유리를 두르는 구간

    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        # 1단 스커트 (검정)
        m.quad(a['bl'], b['bl'], b['sl'], a['sl'], UV_BLACK)
        m.quad(a['sr'], b['sr'], b['br'], a['br'], UV_BLACK)
        # 2단 문짝 (흰색, 가운데 두 칸은 태극)
        if door[0] <= i <= door[1]:
            m.quad(a['sl'], b['sl'], b['ml'], a['ml'], None, UV_MARK)
            m.quad(a['mr'], b['mr'], b['sr'], a['sr'], None, UV_MARK)
        else:
            m.quad(a['sl'], b['sl'], b['ml'], a['ml'], UV_WHITE)
            m.quad(a['mr'], b['mr'], b['sr'], a['sr'], UV_WHITE)
        # 3단 캐빈 옆 (유리띠)
        side_uv = UV_GLASS if cabin[0] <= i <= cabin[1] else UV_WHITE
        m.quad(a['ml'], b['ml'], b['tl'], a['tl'], side_uv)
        m.quad(a['tr'], b['tr'], b['mr'], a['mr'], side_uv)
        # 지붕 — 앞쪽 두 칸은 앞유리, 코끝 경사면엔 헤드라이트 그래픽
        if i == len(rings) - 2:
            def _hood_uv(pt):
                u0, v0, u1, v1 = UV_NOSE_RECT
                u = u0 + (pt[0] + 0.50) / 1.00 * (u1 - u0)
                v = v1 - (pt[1] - 1.28) / 0.18 * (v1 - v0)
                return (min(u1, max(u0, u)), min(v1, max(v0, v)))
            pts = (a['tl'], b['tl'], b['tr'], a['tr'])
            m.quad(*pts, uv=None, uvs=tuple(_hood_uv(q) for q in pts))
        else:
            top_uv = UV_GLASS if i in (4, 5) else UV_WHITE
            m.quad(a['tl'], b['tl'], b['tr'], a['tr'], top_uv)
        # 바닥
        m.quad(a['br'], b['br'], b['bl'], a['bl'], UV_BLACK)

    # 앞뒤 마감 — 아래단은 검정, 위단은 전면/후면 그래픽(헤드라이트 등)
    def _face_uv(pt, rect):
        u0, v0, u1, v1 = rect
        u = u0 + (pt[0] + 0.60) / 1.20 * (u1 - u0)
        v = v0 + (pt[2] - 0.08) / 0.46 * (v1 - v0)
        return (min(u1, max(u0, u)), min(v1, max(v0, v)))

    for r, rect in ((rings[0], UV_TAIL_RECT), (rings[-1], UV_NOSE_RECT)):
        lo = [r['bl'], r['sl'], r['sr'], r['br']]
        for k in range(1, len(lo) - 1):
            m.tri(lo[0], lo[k], lo[k + 1], UV_BLACK)
        hi = [r['sl'], r['ml'], r['tl'], r['tr'], r['mr'], r['sr']]
        for k in range(1, len(hi) - 1):
            m.tri(hi[0], hi[k], hi[k + 1], None,
                  (_face_uv(hi[0], rect), _face_uv(hi[k], rect),
                   _face_uv(hi[k + 1], rect)))

    # 바퀴
    for wx, wy in WHEELS:
        sx = WHEEL_W / 2 * (1 if wx > 0 else -1)
        cx_in, cx_out = wx - sx, wx + sx
        for k in range(WHEEL_SEG):
            a0 = 2 * math.pi * k / WHEEL_SEG
            a1 = 2 * math.pi * (k + 1) / WHEEL_SEG
            p0 = (wy + WHEEL_R * math.cos(a0), WHEEL_R + WHEEL_R * math.sin(a0))
            p1 = (wy + WHEEL_R * math.cos(a1), WHEEL_R + WHEEL_R * math.sin(a1))
            m.quad((cx_in, p0[0], p0[1]), (cx_in, p1[0], p1[1]),
                   (cx_out, p1[0], p1[1]), (cx_out, p0[0], p0[1]), UV_BLACK)
            m.tri((cx_out, wy, WHEEL_R), (cx_out, p0[0], p0[1]),
                  (cx_out, p1[0], p1[1]), UV_WHEEL)
            m.tri((cx_in, wy, WHEEL_R), (cx_in, p1[0], p1[1]),
                  (cx_in, p0[0], p0[1]), UV_BLACK)

    _orient(m)
    return m


def bounds(m):
    xs = [p[0] for p in m.v]
    ys = [p[1] for p in m.v]
    zs = [p[2] for p in m.v]
    ctr = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2)
    ext = ((max(xs) - min(xs)) / 2, (max(ys) - min(ys)) / 2, (max(zs) - min(zs)) / 2)
    return ctr, ext


if __name__ == '__main__':
    m = build()
    c, e = bounds(m)
    print('정점 %d개 · 삼각형 %d개' % (len(m.v), len(m.t) // 3))
    print('AABB 중심 (%.3f, %.3f, %.3f) 반지름 (%.3f, %.3f, %.3f)' % (c + e))
    print('크기  가로 %.2f · 길이 %.2f · 높이 %.2f' % (e[0] * 2, e[1] * 2, e[2] * 2))
