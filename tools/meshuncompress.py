# -*- coding: utf-8 -*-
"""**압축된 메시**를 풀어서 보통 정점 데이터로 다시 저장한다.

왜 필요한가. 갤럭시 A35(Mali-G68 · 안드로이드 16)에서 차 몸통이 새까맣게
나온다. 실기 대조로 좁힌 결과가 이렇다.

  · 메시는 그려진다 (셰이더를 빨강으로 바꾸면 차 모양이 빨갛게 나온다)
  · 텍스처도 제대로 묶여 있다 (UV 를 (0.5,0.5)로 박으면 그 색으로 칠해진다)
  · 그런데 `xlv_TEXCOORD0` 가 쓰레기 값이라 표본이 0 으로 나온다
  · **압축이 없는 메시를 쓰는 차(Phoenix)는 같은 폰에서 멀쩡히 나온다**

유니티 4 의 `m_MeshCompression` 은 정점·UV 를 비트 단위로 욱여넣는다(이 게임은
UV 가 8비트). 그걸 푸는 경로가 이 드라이버에서 UV 를 망친다. Adreno 는 넘어간다.
그러니 아예 굽는 쪽에서 풀어 둔다.

    python tools/meshuncompress.py --survey    무엇이 압축되어 있나
    python tools/meshuncompress.py --all       전부 푼다
    python tools/meshuncompress.py --like aveo 이름으로 골라서
    python tools/meshuncompress.py --restore   backup/mesh 에서 되돌리기

푼 뒤의 배치는 이 게임의 압축 없는 메시(예: `AVEO_LOW`)를 그대로 본떴다 —
스트림0 에 좌표(float32×3), 스트림1 에 UV(float32×2), 스트림 사이는 16바이트
경계에 맞춘다. 레코드가 길어지므로 sfedit 로 파일을 다시 짠다.
"""
import argparse
import os
import shutil
import struct
import sys

CODE = os.path.dirname(os.path.abspath(__file__))
HERE = os.path.dirname(CODE)
sys.path.insert(0, CODE)

DATA = os.path.join('assets', 'bin', 'Data')
BAK = os.path.join(HERE, 'backup', 'mesh')
ALIGN = 16          # 스트림 시작은 16바이트에 맞춘다


def _files(tree):
    root = os.path.join(tree, DATA)
    for name in sorted(os.listdir(root)):
        if '.' in name:            # 백업 등 곁다리 파일은 건드리지 않는다
            continue
        p = os.path.join(root, name)
        if os.path.isfile(p) and os.path.getsize(p) >= 512:
            yield name, p


def unpack_bits(pv):
    """PackedBitVector 를 정수 목록으로 푼다. 값은 낮은 비트부터 채워진다."""
    n = int(pv.get('m_NumItems') or 0)
    bits = int(pv.get('m_BitSize') or 0)
    if not n or not bits:
        return []
    data = pv.get('m_Data') or []
    if isinstance(data, (bytes, bytearray)):
        data = bytearray(data)
    else:
        data = bytearray(int(x) & 0xFF for x in data)
    out = []
    pos = 0          # 바이트 자리
    off = 0          # 그 바이트 안 비트 자리
    mask = (1 << bits) - 1
    for _ in range(n):
        got = 0
        val = 0
        while got < bits:
            val |= (data[pos] >> off) << got
            take = min(bits - got, 8 - off)
            off += take
            got += take
            if off == 8:
                pos += 1
                off = 0
        out.append(val & mask)
    return out


def unpack_floats(pv):
    """비트로 눌러 담은 실수를 푼다: start + range * v / (2^bits - 1)."""
    raw = unpack_bits(pv)
    if not raw:
        return []
    bits = int(pv.get('m_BitSize') or 0)
    rng = float(pv.get('m_Range') or 0.0)
    start = float(pv.get('m_Start') or 0.0)
    denom = float((1 << bits) - 1) or 1.0
    return [start + rng * (v / denom) for v in raw]


def unpack_skin(cm):
    """뼈 가중치를 푼다. 유니티는 합이 꽉 찰 때까지 한 정점에 몰아 넣는다."""
    w = unpack_bits(cm.get('m_Weights') or {})
    b = unpack_bits(cm.get('m_BoneIndices') or {})
    if not w:
        return []
    bits = int((cm.get('m_Weights') or {}).get('m_BitSize') or 0)
    full = (1 << bits) - 1
    skin = []
    cur = [0.0, 0.0, 0.0, 0.0]
    idx = [0, 0, 0, 0]
    j = 0
    total = 0
    for i, wi in enumerate(w):
        cur[j] = wi / float(full)
        idx[j] = b[i] if i < len(b) else 0
        j += 1
        total += wi
        if total >= full or j == 4:
            for k in range(j, 4):
                cur[k] = 0.0
                idx[k] = 0
            skin.append((tuple(cur), tuple(idx)))
            cur = [0.0, 0.0, 0.0, 0.0]
            idx = [0, 0, 0, 0]
            j = 0
            total = 0
    if j:
        for k in range(j, 4):
            cur[k] = 0.0
            idx[k] = 0
        skin.append((tuple(cur), tuple(idx)))
    return skin


def _blank(pv):
    """PackedBitVector 를 비운다. 있는 열쇠만 건드린다."""
    out = dict(pv)
    if 'm_NumItems' in out:
        out['m_NumItems'] = 0
    if 'm_Data' in out:
        out['m_Data'] = [] if not isinstance(out['m_Data'], (bytes, bytearray)) else b''
    if 'm_BitSize' in out:
        out['m_BitSize'] = 0
    if 'm_Range' in out:
        out['m_Range'] = 0.0
    if 'm_Start' in out:
        out['m_Start'] = 0.0
    return out


def rebuild(t):
    """압축 메시 하나를 푼 typetree 로 만든다. 못 풀면 None."""
    cm = t.get('m_CompressedMesh') or {}
    verts = unpack_floats(cm.get('m_Vertices') or {})
    uvs = unpack_floats(cm.get('m_UV') or {})
    tris = unpack_bits(cm.get('m_Triangles') or {})
    if not verts or not tris:
        return None
    n = len(verts) // 3
    if uvs and len(uvs) // 2 != n:
        # UV1 까지 들어 있으면 여기서 갈라야 한다 — 이 게임엔 없다
        return None

    # 스트림0: 좌표(float32×3) · 스트림1: UV(float32×2)
    s0 = struct.pack('<%df' % len(verts), *verts)
    off1 = (len(s0) + ALIGN - 1) // ALIGN * ALIGN
    s1 = struct.pack('<%df' % len(uvs), *uvs) if uvs else b''
    blob = s0 + b'\0' * (off1 - len(s0)) + s1

    ch = lambda st, of, dim: {'stream': st, 'offset': of,
                              'format': 0, 'dimension': dim}
    channels = [ch(0, 0, 3), ch(0, 0, 0), ch(0, 0, 0),
                ch(1, 0, 2 if uvs else 0), ch(0, 0, 0), ch(0, 0, 0)]
    stream = lambda mask, of, stride: {'channelMask': mask, 'offset': of,
                                       'stride': stride, 'dividerOp': 0,
                                       'frequency': 0}
    streams = [stream(1, 0, 12),
               stream(8, off1, 8) if uvs else stream(0, 0, 0),
               stream(0, 0, 0), stream(0, 0, 0)]

    out = dict(t)
    out['m_MeshCompression'] = 0
    out['m_IsReadable'] = True
    out['m_IndexBuffer'] = list(struct.pack('<%dH' % len(tris), *tris))
    skin = unpack_skin(cm)
    out['m_Skin'] = [{'weight[0]': w[0], 'weight[1]': w[1],
                      'weight[2]': w[2], 'weight[3]': w[3],
                      'boneIndex[0]': b[0], 'boneIndex[1]': b[1],
                      'boneIndex[2]': b[2], 'boneIndex[3]': b[3]}
                     for w, b in skin]
    out['m_VertexData'] = {'m_CurrentChannels': 9 if uvs else 1,
                           'm_VertexCount': n,
                           'm_Channels': channels,
                           'm_Streams': streams,
                           'm_DataSize': blob}
    out['m_CompressedMesh'] = dict(
        (k, _blank(v) if isinstance(v, dict) else v) for k, v in cm.items())
    return out, n, len(tris) // 3


def survey(tree):
    import UnityPy
    total = 0
    print('  %-24s %8s %8s %8s' % ('이름', '정점', '삼각형', '압축'))
    for name, p in _files(tree):
        try:
            env = UnityPy.load(p)
        except Exception:
            continue
        for o in env.objects:
            if o.type.name != 'Mesh':
                continue
            try:
                t = o.read_typetree()
            except Exception:
                continue
            if not t.get('m_MeshCompression'):
                continue
            cm = t['m_CompressedMesh']
            print('  %-24s %8d %8d %8s'
                  % ((t.get('m_Name') or '?')[:24],
                     (cm.get('m_Vertices') or {}).get('m_NumItems', 0) // 3,
                     (cm.get('m_Triangles') or {}).get('m_NumItems', 0) // 3,
                     t.get('m_MeshCompression')))
            total += 1
    print('압축된 메시 %d개' % total)
    return 0


def run(tree, like=None, everything=False):
    import UnityPy
    from sfedit import replace_object

    os.makedirs(BAK, exist_ok=True)
    done = 0
    grew = 0
    for name, p in _files(tree):
        try:
            env = UnityPy.load(p)
        except Exception:
            continue
        todo = []
        for o in env.objects:
            if o.type.name != 'Mesh':
                continue
            try:
                t = o.read_typetree()
            except Exception:
                continue
            if not t.get('m_MeshCompression'):
                continue
            nm = t.get('m_Name') or ''
            if like and like.lower() not in nm.lower():
                continue
            if not (like or everything):
                continue
            todo.append((o, t, nm))
        for o, t, nm in todo:
            got = rebuild(t)
            if got is None:
                print('  건너뜀 %-22s 풀 수 없는 짜임' % nm[:22])
                continue
            new_t, nv, nt = got
            bak = os.path.join(BAK, name)
            if not os.path.exists(bak):
                shutil.copy2(p, bak)
            _old, _new, fold, fnew = replace_object(
                p, o.path_id, bytes(o.save_typetree(new_t)))
            grew += fnew - fold
            done += 1
            print('  %-22s 정점 %5d · 삼각형 %5d   +%.0fKB'
                  % (nm[:22], nv, nt, (fnew - fold) / 1024.0))
    print('푼 메시 %d개 · 트리 %.1fMB 늘어남' % (done, grew / 2.0 ** 20))
    return 0


def restore(tree):
    root = os.path.join(tree, DATA)
    if not os.path.isdir(BAK):
        raise SystemExit('남겨 둔 원본이 없습니다: %s' % BAK)
    n = 0
    for name in sorted(os.listdir(BAK)):
        shutil.copy2(os.path.join(BAK, name), os.path.join(root, name))
        n += 1
    print('되돌린 파일 %d개' % n)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tree', default=os.path.join(HERE, 'x77'))
    ap.add_argument('--survey', action='store_true')
    ap.add_argument('--like')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--restore', action='store_true')
    a = ap.parse_args()
    if a.survey:
        return survey(a.tree)
    if a.restore:
        return restore(a.tree)
    if not (a.like or a.all):
        ap.error('--like 또는 --all 을 주세요')
    return run(a.tree, a.like, a.all)


if __name__ == '__main__':
    sys.exit(main())
