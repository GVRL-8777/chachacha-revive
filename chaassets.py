# -*- coding: utf-8 -*-
"""차차차 자산 도구 — 뽑기 · 다시 칠하기 · 들여오기.

chatool.py 가 쓰는 라이브러리다.

여기서 다루는 것
  · 자산 색인    이름 -> (파일, pathID, 종류). 한 번 훑어서 assetindex.json 에 남긴다
  · 뽑기         텍스처 PNG · 메시 OBJ · UV 안내선 PNG
  · 다시 칠하기  PNG -> DXT1 로 눌러 제자리에 덮어쓴다 (크기가 같아 길이 보존)
  · 들여오기     OBJ -> 게임 메시(압축 컨테이너)

실기에서 확인한 규칙 (어기면 조용히 깨진다)
  · 차 메시는 SkinnedMeshRenderer 라 **본**이 자세를 잡는다. 주행 씬은 -90°X 로
    누워 있어 차고에서 멀쩡해도 주행에서 뒤집힐 수 있다. 검증은 주행 화면으로.
  · 삼각형 앞면은 (t1-t0)x(t2-t0) 가 바깥을 향하는 감기. 뒤집히면 껍데기
    안쪽만 보여 차가 새까맣게 나온다. orient() 가 면마다 자동으로 맞춘다.
  · 차 텍스처는 전부 DXT1. DXT5 는 기기에서 단색으로 뭉갠다.
"""
import io
import json
import os
import struct
import sys

_HERE = (os.path.dirname(os.path.abspath(sys.executable))
         if getattr(sys, 'frozen', False)
         else os.path.dirname(os.path.abspath(__file__)))
# 구운 exe 는 dist/ 안에 있다. 작업 트리는 한 칸 위다.
if not os.path.isdir(os.path.join(_HERE, 'x77'))         and os.path.isdir(os.path.join(os.path.dirname(_HERE), 'x77')):
    _HERE = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

DATA = 'assets/bin/Data'
# 색인은 **작업 트리 옆**에 둔다. 상대경로로 두면 어느 폴더에서 실행하느냐에
# 따라 못 찾고 몇 분짜리 색인을 처음부터 다시 만든다.
INDEX = os.path.join(_HERE, 'assetindex.json')


# ------------------------------------------------------------------ 공통
def _sf(path):
    from UnityPy.streams import EndianBinaryReader
    from UnityPy.files.SerializedFile import SerializedFile
    return SerializedFile(EndianBinaryReader(io.open(path, 'rb').read()), None)


def build_index(tree='x77', out=INDEX, progress=None):
    """작업 트리를 통째로 훑어 이름 색인을 만든다. 몇 분 걸린다."""
    d = os.path.join(tree, DATA)
    files = [f for f in sorted(os.listdir(d))
             if os.path.isfile(os.path.join(d, f)) and '.split' not in f]
    idx = {}
    for i, fn in enumerate(files):
        if progress:
            progress(i, len(files), fn)
        p = os.path.join(d, fn)
        try:
            sf = _sf(p)
        except Exception:
            continue
        for pid, o in sf.objects.items():
            kind = o.type.name
            if kind not in ('Mesh', 'Texture2D', 'GameObject', 'Material'):
                continue
            try:
                name = o.read_typetree().get('m_Name')
            except Exception:
                continue
            if not name:
                continue
            idx.setdefault(name.lower(), []).append([fn, pid, kind, name])
    io.open(out, 'w', encoding='utf-8').write(
        json.dumps(idx, ensure_ascii=False))
    return idx


def load_index(out=INDEX):
    if not os.path.exists(out):
        return None
    return json.load(io.open(out, encoding='utf-8'))


def find(idx, name, kind=None):
    """색인에서 이름으로 찾는다. kind 를 주면 그 종류만."""
    rows = idx.get(name.lower(), [])
    if kind:
        rows = [r for r in rows if r[2] == kind]
    return rows


def car_list(tree='x77'):
    """CarDataBase 의 차 목록."""
    from sfparse import parse
    p = os.path.join(tree, DATA, 'ade64ecd8944d9640bb1438deb4f6fe3')
    raw = io.open(p, 'rb').read()
    meta = parse(p)
    rec = [o for o in meta['objects'] if o['path_id'] == 1][0]
    st = meta['data_offset'] + rec['start']
    blob = raw[st:st + rec['size']]
    n = struct.unpack_from('<i', blob, 0)[0]
    off = 4 + n
    off += (-off) % 4
    tlen = struct.unpack_from('<i', blob, off)[0]
    text = blob[off + 4:off + 4 + tlen].decode('utf-8')
    arr = json.loads(text)['CarDataBase']['CarInfoDB']['CarDataArray']
    out = []
    for c in arr:
        out.append({
            'index': c['CarIndex'],
            'carNo': c['CarIndex'] + 1,
            'name': c['CarName'],
            'startClass': c['StartCarClassType'],
            'classes': [x['CarClassType'] for x in c['CarClassDataArray']],
            'gotya': c.get('IsGotyaEvent', False),
        })
    return sorted(out, key=lambda x: x['index'])


# ------------------------------------------------------------------ 비트 포장
def _unpack_bits(data, bits, n):
    out = []
    acc = nb = pos = 0
    for _ in range(n):
        while nb < bits:
            acc |= data[pos] << nb
            nb += 8
            pos += 1
        out.append(acc & ((1 << bits) - 1))
        acc >>= bits
        nb -= bits
    return out


def _pack_bits(vals, bits):
    data = bytearray((len(vals) * bits + 7) // 8)
    pos = 0
    for v in vals:
        for b in range(bits):
            if (v >> b) & 1:
                data[pos >> 3] |= 1 << (pos & 7)
            pos += 1
    return bytes(data)


def _packed_float(vals, bits):
    mn, mx = min(vals), max(vals)
    rng = (mx - mn) or 1.0
    top = (1 << bits) - 1
    q = [min(top, max(0, int(round((v - mn) / rng * top)))) for v in vals]
    return {'m_NumItems': len(vals), 'm_Range': rng, 'm_Start': mn,
            'm_Data': _pack_bits(q, bits), 'm_BitSize': bits}


def _packed_int(vals, bits):
    return {'m_NumItems': len(vals), 'm_Data': _pack_bits(vals, bits),
            'm_BitSize': bits}


# ------------------------------------------------------------------ 메시
def read_mesh(tree, fn, pid):
    """압축·비압축 어느 쪽이든 (정점, uv, 삼각형, 이름) 으로 읽어 준다."""
    p = os.path.join(tree, DATA, fn)
    sf = _sf(p)
    t = sf.objects[pid].read_typetree()
    if t['m_MeshCompression']:
        cm = t['m_CompressedMesh']

        def dec(pv):
            q = _unpack_bits(bytes(pv['m_Data']), pv['m_BitSize'],
                             pv['m_NumItems'])
            top = (1 << pv['m_BitSize']) - 1
            return [pv['m_Start'] + x * pv['m_Range'] / top for x in q]

        flat = dec(cm['m_Vertices'])
        uvf = dec(cm['m_UV']) if cm['m_UV']['m_NumItems'] else []
        tri = _unpack_bits(bytes(cm['m_Triangles']['m_Data']),
                           cm['m_Triangles']['m_BitSize'],
                           cm['m_Triangles']['m_NumItems'])
    else:
        vd = t['m_VertexData']
        buf = bytes(vd['m_DataSize'])
        n = vd['m_VertexCount']
        streams = vd['m_Streams']
        chs = vd['m_Channels']
        pos_ch, uv_ch = chs[0], chs[3]
        ps = streams[pos_ch['stream']]
        us = streams[uv_ch['stream']]
        flat, uvf = [], []
        for i in range(n):
            o = ps['offset'] + i * ps['stride'] + pos_ch['offset']
            flat += list(struct.unpack_from('<fff', buf, o))
            if uv_ch['dimension']:
                o2 = us['offset'] + i * us['stride'] + uv_ch['offset']
                uvf += list(struct.unpack_from('<ff', buf, o2))
        ib = bytes(t['m_IndexBuffer'])
        tri = list(struct.unpack('<%dH' % (len(ib) // 2), ib))
    v = [tuple(flat[i:i + 3]) for i in range(0, len(flat), 3)]
    uv = [tuple(uvf[i:i + 2]) for i in range(0, len(uvf), 2)]
    return v, uv, tri, t['m_Name']


def write_obj(path, v, uv, tri, name='car'):
    """편집용 OBJ. y=길이 · z=높이 인 게임 좌표를 그대로 쓴다."""
    with io.open(path, 'w', encoding='utf-8') as f:
        f.write('# %s — 다함께 차차차 차량 메시\n' % name)
        f.write('# 좌표계: x 좌우 · y 앞뒤(길이) · z 높이.\n')
        f.write('# 블렌더에서 Z-up(Forward -Y) 으로 읽으면 그대로 맞는다.\n')
        f.write('o %s\n' % name)
        for p in v:
            f.write('v %.5f %.5f %.5f\n' % p)
        for t in uv:
            f.write('vt %.5f %.5f\n' % t)
        for i in range(0, len(tri), 3):
            a, b, c = tri[i] + 1, tri[i + 1] + 1, tri[i + 2] + 1
            if uv:
                f.write('f %d/%d %d/%d %d/%d\n' % (a, a, b, b, c, c))
            else:
                f.write('f %d %d %d\n' % (a, b, c))


def read_obj(path):
    """OBJ 를 읽는다. 면마다 정점을 따로 만들어 UV 가 정확히 붙게 한다."""
    vs, ts, faces = [], [], []
    for ln in io.open(path, encoding='utf-8', errors='replace'):
        w = ln.split()
        if not w:
            continue
        if w[0] == 'v':
            vs.append(tuple(float(x) for x in w[1:4]))
        elif w[0] == 'vt':
            ts.append(tuple(float(x) for x in w[1:3]))
        elif w[0] == 'f':
            idx = []
            for tok in w[1:]:
                bits = tok.split('/')
                vi = int(bits[0]) - 1
                ti = int(bits[1]) - 1 if len(bits) > 1 and bits[1] else None
                idx.append((vi, ti))
            for k in range(1, len(idx) - 1):        # 다각형은 부채꼴로 쪼갠다
                faces.append((idx[0], idx[k], idx[k + 1]))
    # (위치, UV) 가 같은 정점은 하나로 합친다. 면마다 새로 만들면 정점이
    # 세 배로 불어나 원본과 길이가 안 맞고, 10비트 인덱스 한계도 금방 넘는다.
    v, uv, tri = [], [], []
    seen = {}
    for f in faces:
        for vi, ti in f:
            pos = vs[vi]
            t = ts[ti] if (ti is not None and ti < len(ts)) else (0.5, 0.5)
            key = (round(pos[0], 5), round(pos[1], 5), round(pos[2], 5),
                   round(t[0], 5), round(t[1], 5))
            j = seen.get(key)
            if j is None:
                j = len(v)
                seen[key] = j
                v.append(pos)
                uv.append(t)
            tri.append(j)
    return v, uv, tri


def replace_object(tree, fn, pid, new_blob):
    """파일을 통째로 다시 써서 오브젝트 하나를 갈아 끼운다.

    제자리 덮어쓰기는 길이가 1바이트만 달라도 못 한다. 자산 파일은 대개
    메시 하나뿐이라, 나머지는 그대로 옮기고 새로 쓰는 편이 훨씬 낫다.
    """
    from sfparse import parse
    from mktaegeuk import write_serialized
    p = os.path.join(tree, DATA, fn)
    meta = parse(p)
    raw = io.open(p, 'rb').read()
    objs = []
    for o in sorted(meta['objects'], key=lambda x: x['path_id']):
        if o['path_id'] == pid:
            objs.append((pid, o['class_id'], new_blob))
        else:
            st = meta['data_offset'] + o['start']
            objs.append((o['path_id'], o['class_id'], raw[st:st + o['size']]))
    ext = [os.path.basename(e) for e in meta['externals']]
    return write_serialized(p, meta, objs, ext)


def flip_winding(tri):
    for k in range(0, len(tri), 3):
        tri[k + 1], tri[k + 2] = tri[k + 2], tri[k + 1]


def orient(v, tri, center=None):
    """모든 삼각형의 앞면이 바깥을 향하게 감기를 맞춘다."""
    if center is None:
        center = bounds(v)[0]
    flipped = 0
    for k in range(0, len(tri), 3):
        a, b, c = tri[k], tri[k + 1], tri[k + 2]
        pa, pb, pc = v[a], v[b], v[c]
        u = (pb[0] - pa[0], pb[1] - pa[1], pb[2] - pa[2])
        w = (pc[0] - pa[0], pc[1] - pa[1], pc[2] - pa[2])
        n = (u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2],
             u[0] * w[1] - u[1] * w[0])
        cx = ((pa[0] + pb[0] + pc[0]) / 3 - center[0],
              (pa[1] + pb[1] + pc[1]) / 3 - center[1],
              (pa[2] + pb[2] + pc[2]) / 3 - center[2])
        if n[0] * cx[0] + n[1] * cx[1] + n[2] * cx[2] < 0:
            tri[k + 1], tri[k + 2] = tri[k + 2], tri[k + 1]
            flipped += 1
    return flipped


def bounds(v):
    xs = [p[0] for p in v]
    ys = [p[1] for p in v]
    zs = [p[2] for p in v]
    ctr = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2,
           (min(zs) + max(zs)) / 2)
    ext = ((max(xs) - min(xs)) / 2, (max(ys) - min(ys)) / 2,
           (max(zs) - min(zs)) / 2)
    return ctr, ext


def fit_to(v, ref_ctr, ref_ext):
    """들여온 모델을 기준 차의 크기·위치에 맞춘다(등비 축소)."""
    ctr, ext = bounds(v)
    s = min((ref_ext[i] / ext[i]) if ext[i] > 1e-6 else 1.0 for i in range(3))
    return [tuple((p[i] - ctr[i]) * s + ref_ctr[i] for i in range(3)) for p in v]


def pack_mesh(donor_tree, v, uv, tri, name):
    """정점/UV/삼각형을 원본과 같은 압축 컨테이너에 담는다."""
    t = dict(donor_tree)
    t['m_Name'] = name
    ctr, ext = bounds(v)
    aabb = {'m_Center': {'x': ctr[0], 'y': ctr[1], 'z': ctr[2]},
            'm_Extent': {'x': ext[0], 'y': ext[1], 'z': ext[2]}}
    t['m_SubMeshes'] = [{'firstByte': 0, 'indexCount': len(tri), 'topology': 0,
                         'firstVertex': 0, 'vertexCount': len(v),
                         'localAABB': aabb}]
    t['m_LocalAABB'] = aabb
    cm = dict(donor_tree['m_CompressedMesh'])
    cm['m_Vertices'] = _packed_float([c for p in v for c in p], 10)
    cm['m_UV'] = _packed_float([c for p in uv for c in p], 8)
    cm['m_Weights'] = _packed_int([31] * len(v), 5)     # 정점당 본 하나, 1.0
    cm['m_BoneIndices'] = _packed_int([0] * len(v), 2)
    # 인덱스 비트 폭은 정점 수에 맞춘다. 원본(993정점)이 10비트라고 그대로
    # 쓰면 1024개를 넘는 순간 인덱스가 잘려 메시가 엉킨다.
    bits = max(1, (max(tri) if tri else 0).bit_length())
    cm['m_Triangles'] = _packed_int(list(tri), bits)
    t['m_CompressedMesh'] = cm
    return t


# ------------------------------------------------------------------ 텍스처
def export_texture(tree, fn, pid, out_png):
    import UnityPy
    env = UnityPy.load(os.path.join(tree, DATA, fn))
    for o in env.objects:
        if o.type.name != 'Texture2D':
            continue
        d = o.read()
        img = d.image
        img.save(out_png)
        return img.size
    raise SystemExit('텍스처를 못 찾았다')


def import_texture(tree, fn, pid, png):
    """PNG 를 DXT1 로 눌러 제자리에 덮어쓴다. 크기가 같으면 길이가 보존된다."""
    from PIL import Image
    from UnityPy.enums import TextureFormat
    from UnityPy.export import Texture2DConverter as T2C
    from sfparse import parse
    p = os.path.join(tree, DATA, fn)
    sf = _sf(p)
    o = sf.objects[pid]
    t = o.read_typetree()
    im = Image.open(png).convert('RGB')
    if (im.width, im.height) != (t['m_Width'], t['m_Height']):
        im = im.resize((t['m_Width'], t['m_Height']), Image.LANCZOS)
    blob, fmt = T2C.image_to_texture2d(im, TextureFormat.DXT1)
    t.update({'m_TextureFormat': int(fmt), 'm_MipMap': False,
              'm_CompleteImageSize': len(blob), 'image data': bytes(blob)})
    new = bytes(o.save_typetree(t))
    meta = parse(p)
    rec = [x for x in meta['objects'] if x['path_id'] == pid][0]
    if len(new) != rec['size']:
        raise SystemExit('길이가 달라졌다 (%d -> %d). 크기·포맷을 확인하라'
                         % (rec['size'], len(new)))
    raw = bytearray(io.open(p, 'rb').read())
    st = meta['data_offset'] + rec['start']
    raw[st:st + len(new)] = new
    io.open(p, 'wb').write(bytes(raw))
    return len(new)


def uv_guide(png_in, uv, tri, png_out, color=(255, 0, 128)):
    """텍스처 위에 UV 선을 겹쳐 그려 어디를 칠할지 보이게 한다."""
    from PIL import Image, ImageDraw
    im = Image.open(png_in).convert('RGB')
    w, h = im.size
    d = ImageDraw.Draw(im)
    for k in range(0, len(tri), 3):
        pts = []
        for i in (tri[k], tri[k + 1], tri[k + 2]):
            if i >= len(uv):
                break
            u, vv = uv[i]
            pts.append((u * w, (1 - vv) * h))
        if len(pts) == 3:
            d.polygon(pts, outline=color)
    im.save(png_out)
    return im.size


# ------------------------------------------------------------------ 내보내기
# 게임 좌표는 x 좌우 · y 앞뒤 · z 높이(Z-up) 다. OBJ 와 STL 은 그대로 두고
# (읽는 쪽에서 축을 고를 수 있다), glTF 는 규격이 Y-up 으로 못박혀 있어
# 여기서 눕혀 준다. 축 회전이라 감기는 그대로다.
def to_yup(v):
    """(x, y, z) -> (x, z, -y). X축 -90° 회전."""
    return [(p[0], p[2], -p[1]) for p in v]


def normals(v, tri):
    """면 법선을 정점마다 모아 평균 낸다. 게임 메시엔 법선이 없다."""
    import math
    acc = [[0.0, 0.0, 0.0] for _ in v]
    for k in range(0, len(tri) - 2, 3):
        a, b, c = tri[k], tri[k + 1], tri[k + 2]
        if a >= len(v) or b >= len(v) or c >= len(v):
            continue
        ax, ay, az = v[a]
        ux, uy, uz = v[b][0] - ax, v[b][1] - ay, v[b][2] - az
        wx, wy, wz = v[c][0] - ax, v[c][1] - ay, v[c][2] - az
        nx, ny, nz = uy * wz - uz * wy, uz * wx - ux * wz, ux * wy - uy * wx
        for i in (a, b, c):
            acc[i][0] += nx
            acc[i][1] += ny
            acc[i][2] += nz
    out = []
    for n in acc:
        d = math.sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2])
        out.append((n[0] / d, n[1] / d, n[2] / d) if d > 1e-9 else (0.0, 0.0, 1.0))
    return out


def write_mtl(path, name, png_name):
    """OBJ 짝꿍. 이게 있어야 블렌더가 텍스처를 같이 물고 온다."""
    with io.open(path, 'w', encoding='utf-8') as f:
        f.write('# %s\n' % name)
        f.write('newmtl %s\n' % name)
        f.write('Ka 1.000 1.000 1.000\nKd 1.000 1.000 1.000\n')
        f.write('Ks 0.000 0.000 0.000\nd 1.0\nillum 1\n')
        if png_name:
            f.write('map_Kd %s\n' % png_name)


def write_stl(path, v, tri, name='car'):
    """이진 STL. 3D 프린터·조형 도구용이라 UV 는 못 담는다."""
    n = normals(v, tri)
    faces = []
    for k in range(0, len(tri) - 2, 3):
        a, b, c = tri[k], tri[k + 1], tri[k + 2]
        if max(a, b, c) >= len(v):
            continue
        faces.append((a, b, c))
    with io.open(path, 'wb') as f:
        head = ('%s — 다함께 차차차' % name).encode('utf-8')[:79]
        f.write(head + b'\0' * (80 - len(head)))
        f.write(struct.pack('<I', len(faces)))
        for a, b, c in faces:
            fn = [(n[a][i] + n[b][i] + n[c][i]) / 3.0 for i in range(3)]
            f.write(struct.pack('<fff', *fn))
            for i in (a, b, c):
                f.write(struct.pack('<fff', *v[i]))
            f.write(b'\0\0')
    return len(faces)


def _pad4(b, fill=b'\0'):
    return b + fill * ((-len(b)) % 4)


def write_glb(path, v, uv, tri, name='car', png=None):
    """glTF 2.0 (.glb) 한 덩어리. 텍스처까지 안에 넣는다.

    윈도우 3D 뷰어 · 블렌더 · 웹 뷰어가 그냥 연다. 규격이 Y-up 이라
    좌표를 눕히고, UV 의 세로도 규격에 맞춰 뒤집는다."""
    vv = to_yup(v)
    nn = normals(vv, tri)
    idx = [i for i in tri if i < len(vv)]
    idx = idx[:len(idx) - len(idx) % 3]

    bin_parts, views, accs = [], [], []
    off = [0]

    def put(blob, target=None):
        blob = _pad4(blob)
        views.append({'buffer': 0, 'byteOffset': off[0],
                      'byteLength': len(blob)}
                     if target is None else
                     {'buffer': 0, 'byteOffset': off[0],
                      'byteLength': len(blob), 'target': target})
        bin_parts.append(blob)
        off[0] += len(blob)
        return len(views) - 1

    iv = put(struct.pack('<%dI' % len(idx), *idx), 34963)
    accs.append({'bufferView': iv, 'componentType': 5125, 'count': len(idx),
                 'type': 'SCALAR'})
    pv = put(b''.join(struct.pack('<fff', *p) for p in vv), 34962)
    mn = [min(p[i] for p in vv) for i in range(3)]
    mx = [max(p[i] for p in vv) for i in range(3)]
    accs.append({'bufferView': pv, 'componentType': 5126, 'count': len(vv),
                 'type': 'VEC3', 'min': mn, 'max': mx})
    nv = put(b''.join(struct.pack('<fff', *p) for p in nn), 34962)
    accs.append({'bufferView': nv, 'componentType': 5126, 'count': len(nn),
                 'type': 'VEC3'})
    attrs = {'POSITION': 1, 'NORMAL': 2}
    if uv and len(uv) >= len(vv):
        tv = put(b''.join(struct.pack('<ff', t[0], 1.0 - t[1])
                          for t in uv[:len(vv)]), 34962)
        accs.append({'bufferView': tv, 'componentType': 5126,
                     'count': len(vv), 'type': 'VEC2'})
        attrs['TEXCOORD_0'] = 3

    g = {'asset': {'version': '2.0', 'generator': 'chatool (다함께 차차차)'},
         'scene': 0, 'scenes': [{'nodes': [0]}],
         'nodes': [{'mesh': 0, 'name': name}],
         'meshes': [{'name': name, 'primitives': [
             {'attributes': attrs, 'indices': 0, 'material': 0}]}],
         'materials': [{'name': name, 'doubleSided': False,
                        'pbrMetallicRoughness': {
                            'metallicFactor': 0.0, 'roughnessFactor': 0.75}}],
         'accessors': accs, 'bufferViews': views}
    if png and os.path.exists(png):
        blob = io.open(png, 'rb').read()
        bv = put(blob)
        g['images'] = [{'bufferView': bv, 'mimeType': 'image/png'}]
        g['samplers'] = [{'magFilter': 9729, 'minFilter': 9987,
                          'wrapS': 10497, 'wrapT': 10497}]
        g['textures'] = [{'sampler': 0, 'source': 0}]
        g['materials'][0]['pbrMetallicRoughness']['baseColorTexture'] = {
            'index': 0}

    binblob = b''.join(bin_parts)
    g['buffers'] = [{'byteLength': len(binblob)}]
    js = _pad4(json.dumps(g, ensure_ascii=False,
                          separators=(',', ':')).encode('utf-8'), b' ')
    with io.open(path, 'wb') as f:
        f.write(b'glTF' + struct.pack('<II', 2, 12 + 8 + len(js) + 8
                                      + len(binblob)))
        f.write(struct.pack('<I', len(js)) + b'JSON' + js)
        f.write(struct.pack('<I', len(binblob)) + b'BIN\0' + binblob)
    return len(binblob) + len(js)
