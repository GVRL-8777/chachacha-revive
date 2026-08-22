# -*- coding: utf-8 -*-
"""애니메이션 읽기 — 뼈대 · 클립 · 굽기.

이 게임의 차는 **스키닝 메시**다. 차고에서는 쉬는 자세라 멀쩡해 보여도
주행 화면에서는 뼈가 자세를 잡는다. 그래서 뼈 없이 보는 미리보기는
반쪽이다. 여기서 뼈와 동작을 읽어 온다.

자료가 어디에 흩어져 있나 (실측)

  · 메시 파일            정점 · UV · 삼각형 · **m_Skin(정점별 뼈 가중치)**
                        · **m_BindPose(뼈별 역바인드 행렬)**
  · 게임 프리팹 파일     `SkinnedMeshRenderer`(m_Bones · m_Mesh) ·
                        트랜스폼 계층 · `Animation`(m_Animations)
  · 클립 파일            `AnimationClip` 하나씩 따로 (파일 37개)

클립은 **구식(legacy) 무압축**이라 곡선이 평문으로 들어 있다. 위치·회전·크기
곡선이 각각 트랜스폼 **경로**(`Bone_shadow/Dummy001/Bone_wheel`)로 붙어 있고,
키마다 시간 · 값 · 접선이 있다. Mecanim 압축이었으면 훨씬 어려웠다.

여기서는 **구워서** 준다. 프레임마다 뼈별 스키닝 행렬(월드 × 역바인드)을
미리 계산해 두면 화면 쪽은 곱하기만 하면 된다. 뼈가 3~28개뿐이라 싸다.

  python chaanim.py <자산이름>            뼈대와 클립을 보여 준다
  python chaanim.py <자산이름> --bake race
"""
import io
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chaassets as A                                     # noqa: E402

CODE = os.path.dirname(os.path.abspath(__file__))
# 도구는 tools/ 안에 있고, 작업 트리(x77 · saves · lang …)는 그 위에 있다.
HERE = os.path.dirname(CODE)
# 메시 -> 그 메시를 입히는 프리팹. 만드는 데 몇 분 걸려 파일로 남긴다.
RIGINDEX = os.path.join(HERE, 'riggedindex.json')


# ------------------------------------------------------------------ 행렬
def m_ident():
    return [1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0]


def m_mul(a, b):
    """행 우선 4x4 곱. a·b."""
    o = [0.0] * 16
    for r in range(4):
        ar = r * 4
        for c in range(4):
            o[ar + c] = (a[ar] * b[c] + a[ar + 1] * b[4 + c]
                         + a[ar + 2] * b[8 + c] + a[ar + 3] * b[12 + c])
    return o


def m_trs(t, q, s):
    """위치·쿼터니언·크기 -> 4x4 (행 우선, 열 벡터를 왼쪽에서 곱하는 유니티 배치)."""
    x, y, z, w = q
    n = math.sqrt(x * x + y * y + z * z + w * w) or 1.0
    x, y, z, w = x / n, y / n, z / n, w / n
    xx, yy, zz = x * x, y * y, z * z
    xy, xz, yz = x * y, x * z, y * z
    wx, wy, wz = w * x, w * y, w * z
    sx, sy, sz = s
    return [
        (1 - 2 * (yy + zz)) * sx, (2 * (xy - wz)) * sy, (2 * (xz + wy)) * sz, t[0],
        (2 * (xy + wz)) * sx, (1 - 2 * (xx + zz)) * sy, (2 * (yz - wx)) * sz, t[1],
        (2 * (xz - wy)) * sx, (2 * (yz + wx)) * sy, (1 - 2 * (xx + yy)) * sz, t[2],
        0.0, 0.0, 0.0, 1.0]


def m_inv_affine(m):
    """아핀 4x4 역행렬. 위 3x3 을 뒤집고 이동을 되돌린다."""
    a, b, c = m[0], m[1], m[2]
    d, e, f = m[4], m[5], m[6]
    g, h, i = m[8], m[9], m[10]
    det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    if abs(det) < 1e-12:
        return m_ident()
    r = 1.0 / det
    n = [(e * i - f * h) * r, (c * h - b * i) * r, (b * f - c * e) * r,
         (f * g - d * i) * r, (a * i - c * g) * r, (c * d - a * f) * r,
         (d * h - e * g) * r, (b * g - a * h) * r, (a * e - b * d) * r]
    tx, ty, tz = m[3], m[7], m[11]
    return [n[0], n[1], n[2], -(n[0] * tx + n[1] * ty + n[2] * tz),
            n[3], n[4], n[5], -(n[3] * tx + n[4] * ty + n[5] * tz),
            n[6], n[7], n[8], -(n[6] * tx + n[7] * ty + n[8] * tz),
            0.0, 0.0, 0.0, 1.0]


def bind_matrix(d):
    """유니티의 m_BindPose 는 **열 우선**(eRC = 행 R, 열 C) 로 적혀 있다."""
    return [d['e00'], d['e01'], d['e02'], d['e03'],
            d['e10'], d['e11'], d['e12'], d['e13'],
            d['e20'], d['e21'], d['e22'], d['e23'],
            d['e30'], d['e31'], d['e32'], d['e33']]


# ------------------------------------------------------------------ 색인
def _externals(sf):
    return [e.path for e in sf.externals]


def _ptr(sf, ext, p):
    """PPtr -> (파일이름, pathID). 파일번호 0 은 자기 자신."""
    f = p['m_FileID']
    return (None if f == 0 else ext[f - 1]), p['m_PathID']


IDX_VERSION = 3


def bundle_sources(here=None):
    """번들에 담긴 원본 파일들 (뿌리폴더, 파일이름).

    이식해 넣은 것들(헬리 · 복원한 맵 · 카카오판 보이스)은 x77 이 아니라
    **원본 트리**에 있고 `bundles/pack.unity3d` 로 묶여 들어간다. 헬리의
    변신 동작이 여기 있어서, 이 목록도 함께 훑어야 뼈대가 잡힌다."""
    here = here or HERE
    spec = os.path.join(here, 'packspec.txt')
    out = []
    if not os.path.exists(spec):
        return out
    seen = set()
    for ln in io.open(spec, encoding='utf-8'):
        ln = ln.strip()
        if not ln or ln.startswith('#'):
            continue
        p = ln.split(':')[0]
        root = os.path.join(here, os.path.dirname(p))
        fn = os.path.basename(p)
        if (root, fn) in seen or not os.path.exists(os.path.join(root, fn)):
            continue
        seen.add((root, fn))
        out.append((root, fn))
    return out


def build_rig_index(tree='x77', out=RIGINDEX, progress=None):
    """`SkinnedMeshRenderer` 가 있는 파일을 훑어 메시 -> 프리팹 표를 만든다.

    작업 트리와 **번들 원본**을 함께 본다. 표에는 어느 뿌리에서 왔는지도
    적는다 — 프리팹과 클립을 그 자리에서 열어야 하기 때문이다."""
    from sfparse import parse
    d = os.path.abspath(os.path.join(tree, A.DATA))
    todo = [(d, f) for f in sorted(os.listdir(d))
            if os.path.isfile(os.path.join(d, f)) and '.split' not in f]
    todo += bundle_sources()
    idx, mats = {}, {}
    for i, (root, fn) in enumerate(todo):
        if progress:
            progress(i, len(todo), fn)
        p = os.path.join(root, fn)
        try:
            meta = parse(p)
        except Exception:
            continue
        if not any(o['class_id'] == 137 for o in meta['objects']):
            continue
        try:
            sf = A._sf(p)
        except Exception:
            continue
        ext = _externals(sf)
        for pid, o in sf.objects.items():
            if o.type.name != 'SkinnedMeshRenderer':
                continue
            try:
                t = o.read_typetree()
            except Exception:
                continue
            mf, mp = _ptr(sf, ext, t['m_Mesh'])
            if mf is None:
                mf = fn
            idx.setdefault('%s:%d' % (mf, mp), []).append([root, fn, pid])
            # 머티리얼 -> 메시. 스킨만 갈아입힌 차(블링은 아베오 메시를
            # 그대로 쓴다)는 제 이름의 메시가 아예 없어서 이 길로만 찾는다.
            for m in (t.get('m_Materials') or []):
                mtf, mtp = _ptr(sf, ext, m)
                if mtf is None:
                    mtf = fn
                mats.setdefault('%s:%d' % (mtf, mtp), [mf, mp])
                break
    io.open(out, 'w', encoding='utf-8').write(
        json.dumps({'v': IDX_VERSION, 'map': idx, 'mats': mats},
                   ensure_ascii=False))
    return idx


def load_rig_index(out=RIGINDEX):
    """표를 읽는다. 옛 판이면 None 을 줘서 다시 만들게 한다."""
    if not os.path.exists(out):
        return None
    try:
        d = json.load(io.open(out, encoding='utf-8'))
    except Exception:
        return None
    if not isinstance(d, dict) or d.get('v') != IDX_VERSION:
        return None
    return d.get('map')


def load_mat_index(out=RIGINDEX):
    """머티리얼 -> 메시. 이름이 없는 스킨 차를 찾는 데 쓴다."""
    if not os.path.exists(out):
        return None
    try:
        d = json.load(io.open(out, encoding='utf-8'))
    except Exception:
        return None
    if not isinstance(d, dict) or d.get('v') != IDX_VERSION:
        return None
    return d.get('mats') or {}


# ------------------------------------------------------------------ 가중치
def skin_of(mt):
    """정점별 뼈 가중치. **압축된 메시**도 풀어 준다.

    `_LOW` 판들은 m_MeshCompression 이 켜져 있어 `m_Skin` 이 비어 있고,
    가중치가 `m_CompressedMesh` 안에 비트열로 눌려 있다. 유니티가 쓰는
    규칙은 이렇다.

      · 가중치는 31 을 꽉 찬 값으로 보는 고정소수점이다
      · 한 정점의 가중치를 합이 31 이 될 때까지 읽는다
      · 셋을 읽고도 안 차면 넷째는 `31 - 합` 으로 채운다
    """
    sk = mt.get('m_Skin') or []
    if sk:
        return sk
    cm = mt.get('m_CompressedMesh') or {}
    pw, pb = cm.get('m_Weights'), cm.get('m_BoneIndices')
    if not pw or not pw.get('m_NumItems'):
        return []
    ws = A._unpack_bits(bytes(pw['m_Data']), pw['m_BitSize'], pw['m_NumItems'])
    bs = A._unpack_bits(bytes(pb['m_Data']), pb['m_BitSize'], pb['m_NumItems'])
    out, cur, j, tot, bp = [], None, 0, 0, 0

    def blank():
        return {'weight[0]': 0.0, 'weight[1]': 0.0, 'weight[2]': 0.0,
                'weight[3]': 0.0, 'boneIndex[0]': 0, 'boneIndex[1]': 0,
                'boneIndex[2]': 0, 'boneIndex[3]': 0}

    cur = blank()
    for w in ws:
        cur['weight[%d]' % j] = w / 31.0
        cur['boneIndex[%d]' % j] = bs[bp] if bp < len(bs) else 0
        bp += 1
        j += 1
        tot += w
        if tot >= 31:
            out.append(cur)
            cur, j, tot = blank(), 0, 0
        elif j == 3:
            cur['weight[3]'] = (31 - tot) / 31.0
            cur['boneIndex[3]'] = bs[bp] if bp < len(bs) else 0
            bp += 1
            out.append(cur)
            cur, j, tot = blank(), 0, 0
    return out


# ------------------------------------------------------------------ 뼈대
def _tree_of(sf):
    """트랜스폼 pathID -> {이름, 부모, 자식, TRS}."""
    names, tr = {}, {}
    for pid, o in sf.objects.items():
        if o.type.name == 'GameObject':
            names[pid] = o.read_typetree().get('m_Name') or ''
    for pid, o in sf.objects.items():
        if o.type.name != 'Transform':
            continue
        t = o.read_typetree()
        q = t['m_LocalRotation']
        p = t['m_LocalPosition']
        s = t['m_LocalScale']
        tr[pid] = {
            'name': names.get(t['m_GameObject']['m_PathID'], ''),
            'parent': t['m_Father']['m_PathID'],
            'children': [c['m_PathID'] for c in t['m_Children']],
            't': [p['x'], p['y'], p['z']],
            'r': [q['x'], q['y'], q['z'], q['w']],
            's': [s['x'], s['y'], s['z']],
        }
    return tr


def _paths(tr, root):
    """트랜스폼 -> 애니메이션 뿌리 기준 경로. 클립의 `path` 와 같은 표기."""
    out = {root: ''}
    stack = [root]
    while stack:
        cur = stack.pop()
        for ch in tr[cur].get('children', []):
            if ch not in tr:
                continue
            base = out[cur]
            out[ch] = (base + '/' if base else '') + tr[ch]['name']
            stack.append(ch)
    return out


def rig(tree, mesh_file, mesh_pid, idx=None):
    """메시 하나의 뼈대와 클립 목록. 못 찾으면 None."""
    ridx = idx if idx is not None else load_rig_index()
    if not ridx:
        return None
    hit = ridx.get('%s:%d' % (mesh_file, mesh_pid))
    if not hit:
        return None
    # 후보가 여럿이면 **동작이 붙은 쪽**을 고른다. 메시 파일 자신에도
    # 렌더러가 들어 있지만(FBX 가 그대로 딸려 온다) 거기엔 클립이 없다.
    proot, pf_file, smr_pid = hit[0]
    if len(hit) > 1:
        from sfparse import parse
        for rt, f, q in hit:
            try:
                meta = parse(os.path.join(rt, f))
            except Exception:
                continue
            if any(o['class_id'] == 111 for o in meta['objects']):
                proot, pf_file, smr_pid = rt, f, q
                break
    sf = A._sf(os.path.join(proot, pf_file))
    ext = _externals(sf)
    smr = sf.objects[smr_pid].read_typetree()
    tr = _tree_of(sf)

    # 애니메이션 뿌리 = **렌더러의 조상 중 Animation 을 든 가장 가까운 것.**
    # 클립 경로가 그 자리를 기준으로 적혀 있다. 한 파일에 렌더러와
    # Animation 이 여럿인 것도 있어서(헬리는 차와 로봇이 한 파일이다)
    # 아무거나 첫 번째를 집으면 뼈가 딴 가지로 가 버린다.
    tr_of_go, anim_of_go = {}, {}
    for pid, o in sf.objects.items():
        if o.type.name == 'Transform':
            tr_of_go[o.read_typetree()['m_GameObject']['m_PathID']] = pid
        elif o.type.name == 'Animation':
            anim_of_go[o.read_typetree()['m_GameObject']['m_PathID']] = pid

    cur = tr_of_go.get(smr['m_GameObject']['m_PathID'])
    root, anim_pid = None, None
    while cur in tr:
        go = None
        for g, t2 in tr_of_go.items():
            if t2 == cur:
                go = g
                break
        if go is not None and go in anim_of_go:
            root, anim_pid = cur, anim_of_go[go]
            break
        nxt = tr[cur]['parent']
        if nxt == cur or nxt not in tr:
            break
        cur = nxt

    clips = []
    if anim_pid is not None:
        a = sf.objects[anim_pid].read_typetree()
        for c in a.get('m_Animations') or []:
            f, q = _ptr(sf, ext, c)
            clips.append({'root': proot, 'file': f or pf_file, 'pid': q})
    if root is None:                       # Animation 이 없으면 맨 위를 뿌리로
        tops = [p for p, v in tr.items() if v['parent'] not in tr]
        root = tops[0] if tops else list(tr)[0]

    paths = _paths(tr, root)
    bones = [p['m_PathID'] for p in smr['m_Bones']]

    # 렌더러가 붙은 트랜스폼의 쉬는 자세 월드 행렬. 굽기에서 되돌리는 데 쓴다.
    rgo = smr['m_GameObject']['m_PathID']
    rtr = None
    for pid, o in sf.objects.items():
        if (o.type.name == 'Transform'
                and o.read_typetree()['m_GameObject']['m_PathID'] == rgo):
            rtr = pid
            break
    pre = m_ident()
    if rtr is not None:
        chain, cur = [], rtr
        while cur in tr:
            chain.append(cur)
            if cur == root:
                break
            cur = tr[cur]['parent']
        for c in reversed(chain):
            v = tr[c]
            pre = m_mul(pre, m_trs(v['t'], v['r'], v['s']))

    mesh = A._sf(os.path.join(tree, A.DATA, mesh_file)).objects[mesh_pid]
    mt = mesh.read_typetree()
    bind = [bind_matrix(b) for b in mt.get('m_BindPose') or []]
    skin = skin_of(mt)

    return {
        'prefab': pf_file, 'prefabRoot': proot, 'smr': smr_pid, 'root': root,
        'tr': tr, 'paths': paths, 'bones': bones, 'bind': bind,
        'pre': pre, 'renderTr': rtr,
        'skin': skin, 'clips': clips,
        'meshName': mt.get('m_Name'),
    }


# ------------------------------------------------------------------ 클립
def read_clip_at(root, fn, pid):
    """클립 하나. `root` 는 그 파일이 놓인 폴더다(작업 트리일 수도, 번들
    원본일 수도 있다)."""
    o = A._sf(os.path.join(root, fn)).objects[pid]
    t = o.read_typetree()

    def curves(key, dim):
        out = {}
        for c in t.get(key) or []:
            ks = []
            for k in c['curve']['m_Curve']:
                v = k['value']
                i, g = k['inSlope'], k['outSlope']
                if dim == 4:
                    ks.append((k['time'], [v['x'], v['y'], v['z'], v['w']],
                               [i['x'], i['y'], i['z'], i['w']],
                               [g['x'], g['y'], g['z'], g['w']]))
                else:
                    ks.append((k['time'], [v['x'], v['y'], v['z']],
                               [i['x'], i['y'], i['z']],
                               [g['x'], g['y'], g['z']]))
            if ks:
                out[c['path']] = ks
        return out

    rot = curves('m_RotationCurves', 4)
    pos = curves('m_PositionCurves', 3)
    scl = curves('m_ScaleCurves', 3)
    end = 0.0
    for grp in (rot, pos, scl):
        for ks in grp.values():
            end = max(end, ks[-1][0])
    return {'name': t.get('m_Name'), 'length': end,
            'fps': t.get('m_SampleRate') or 30.0,
            'wrap': t.get('m_WrapMode'), 'rot': rot, 'pos': pos, 'scl': scl}


def read_clip(tree, fn, pid):
    """작업 트리 안의 클립. 예전 부르던 모양 그대로 남겨 둔다."""
    return read_clip_at(os.path.join(tree, A.DATA), fn, pid)


def clip_of(c):
    """rig() 가 준 클립 항목을 그대로 읽는다."""
    return read_clip_at(c['root'], c['file'], c['pid'])


def _eval(keys, time):
    """유니티 곡선 한 점. 키 사이는 **3차 에르미트**(접선 보간)다."""
    if not keys:
        return None
    if time <= keys[0][0]:
        return list(keys[0][1])
    if time >= keys[-1][0]:
        return list(keys[-1][1])
    lo = 0
    for i in range(len(keys) - 1):
        if keys[i][0] <= time <= keys[i + 1][0]:
            lo = i
            break
    t0, v0, _i0, o0 = keys[lo]
    t1, v1, i1, _o1 = keys[lo + 1]
    dt = t1 - t0
    if dt <= 0:
        return list(v1)
    u = (time - t0) / dt
    u2, u3 = u * u, u * u * u
    h00 = 2 * u3 - 3 * u2 + 1
    h10 = u3 - 2 * u2 + u
    h01 = -2 * u3 + 3 * u2
    h11 = u3 - u2
    return [h00 * v0[k] + h10 * dt * o0[k] + h01 * v1[k] + h11 * dt * i1[k]
            for k in range(len(v0))]


def bake(rigd, clip, fps=30.0):
    """프레임마다 뼈별 **스키닝 행렬**(월드 × 역바인드)을 굽는다.

    화면 쪽은 정점마다 이 행렬을 가중치로 섞기만 하면 된다."""
    tr, paths, root = rigd['tr'], rigd['paths'], rigd['root']
    n = max(1, int(round((clip['length'] or 0) * fps)) + 1)
    by_path = {}
    for pid, p in paths.items():
        by_path.setdefault(p, pid)
    order = []                                  # 부모가 먼저 오도록
    stack = [root]
    while stack:
        cur = stack.pop()
        order.append(cur)
        stack += [c for c in tr[cur].get('children', []) if c in tr]

    # 쉬는 자세에서 스키닝 행렬은 **렌더러의 월드 행렬**이 된다(유니티는
    # 역바인드에 그것까지 담아 둔다). 이 게임은 그게 -90°X 라, 그대로 쓰면
    # 정지 미리보기와 견줘 차가 눕는다. 그래서 그 자리를 되돌려 놓고 굽는다.
    pre = m_inv_affine(rigd.get('pre') or m_ident())

    frames = []
    for f in range(n):
        time = f / fps
        world = {}
        for pid in order:
            v = tr[pid]
            p = paths.get(pid, '')
            t = _eval(clip['pos'].get(p), time) or v['t']
            q = _eval(clip['rot'].get(p), time) or v['r']
            s = _eval(clip['scl'].get(p), time) or v['s']
            local = m_trs(t, q, s)
            par = v['parent']
            world[pid] = local if pid == root or par not in world else \
                m_mul(world[par], local)
        mats = []
        for i, b in enumerate(rigd['bones']):
            w = world.get(b, m_ident())
            bp = rigd['bind'][i] if i < len(rigd['bind']) else m_ident()
            mats.append([round(x, 5) for x in m_mul(pre, m_mul(w, bp))])
        frames.append(mats)
    return {'fps': fps, 'frames': frames, 'count': n,
            'length': clip['length'], 'name': clip['name']}


def rest_matrices(rigd):
    """쉬는 자세의 스키닝 행렬. 이걸로 정점을 옮기면 **원본 그대로**여야 한다."""
    empty = {'pos': {}, 'rot': {}, 'scl': {}, 'length': 0.0, 'name': '쉬는자세'}
    return bake(rigd, empty, 1.0)['frames'][0]


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__.strip().splitlines()[-2].strip())
    import chatool
    name = sys.argv[1]
    idx = A.load_index()
    mesh, _tex = chatool._car_assets(idx, name)
    if not mesh:
        raise SystemExit('메시를 못 찾았습니다: %s' % name)
    ridx = load_rig_index()
    if ridx is None:
        print('뼈대 색인을 만드는 중입니다… (몇 분)')
        ridx = build_rig_index(chatool.TREE, progress=lambda i, n, f:
                               (i % 60 == 0) and print('  %d/%d' % (i, n)))
    r = rig(chatool.TREE, mesh[0], mesh[1], ridx)
    if not r:
        raise SystemExit('%s 는 뼈대가 없습니다(스키닝 메시가 아닙니다)' % name)
    print('메시 %s — 프리팹 %s' % (r['meshName'], r['prefab'][:10]))
    print('뼈 %d개:' % len(r['bones']))
    for i, b in enumerate(r['bones']):
        print('   %d  %-34s' % (i, r['paths'].get(b, '?')))
    print('정점별 가중치 %d개 · 역바인드 %d개' % (len(r['skin']), len(r['bind'])))
    print('클립 %d개:' % len(r['clips']))
    for c in r['clips']:
        cl = clip_of(c)
        print('   %-16s %5.2f초  회전 %d · 위치 %d · 크기 %d'
              % (cl['name'], cl['length'], len(cl['rot']), len(cl['pos']),
                 len(cl['scl'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
