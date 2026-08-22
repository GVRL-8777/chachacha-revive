# -*- coding: utf-8 -*-
"""사진 한 장에서 새 자동차 '태극호'를 만들어 넣는다.

없던 차를 새로 만드는 길은 이렇다.
  1. 메시는 파이썬으로 찍는다 (carmesh.py) — 압축 없이 쓴다.
     중국판 차 메시는 m_MeshCompression=3 로 비트단위 압축돼 있지만,
     엔진은 압축 안 된 메시도 그냥 읽는다. 맵 조각이 그 증거다.
  2. 껍데기(프리팹·본·스크립트)는 기존 S급 차에서 통째로 베낀다.
     스크립트는 sharedassets0 에 있고 참조만 남기면 그대로 붙는다.
  3. 텍스처는 새로 그린다 — 흰 차체 · 검은 하단 · 문짝의 태극.

  python mktaegeuk.py            # taegeuk.assets 를 만든다
"""
import io
import math
import os
import struct
import sys

sys.path.insert(0, '.')

from PIL import Image, ImageDraw
from UnityPy.enums import TextureFormat
from UnityPy.export import Texture2DConverter as T2C
from UnityPy.files.SerializedFile import SerializedFile
from UnityPy.streams import EndianBinaryReader

import carmesh
from sfparse import parse

D = 'x77/assets/bin/Data'
DONOR_PREFAB = '6af067f63f19ae84eb93fdee6c07f0e1'   # player_lamborghini_s
DONOR_MODEL = 'e9929419738592541aade46bf0cf3a4e'    # Lamborghini 모델(메시+본)
OUT = 'taegeuk.assets'

NEW = 'Taegeukho'
OLD = 'Lamborghini'
TEX_SIZE = 256

ALIGN = lambda n: (n + 3) & ~3


# ---------------------------------------------------------------- 텍스처
def make_texture():
    import os
    if os.environ.get('TAEGEUK_PROBE'):
        # 진단용: 사분면을 원색으로 칠해 어느 UV 가 어디로 가는지 본다
        im = Image.new('RGB', (TEX_SIZE, TEX_SIZE), (255, 0, 255))
        d = ImageDraw.Draw(im)
        h = TEX_SIZE // 2
        d.rectangle([0, 0, h - 1, h - 1], fill=(255, 0, 0))        # 좌상 빨강
        d.rectangle([h, 0, TEX_SIZE - 1, h - 1], fill=(0, 255, 0)) # 우상 초록
        d.rectangle([0, h, h - 1, TEX_SIZE - 1], fill=(0, 0, 255)) # 좌하 파랑
        d.rectangle([h, h, TEX_SIZE - 1, TEX_SIZE - 1], fill=(255, 255, 0))
        return im
    return _make_texture_real()


def _make_texture_real():
    """흰 차체 / 검은 하단 / 유리 / 태극 문양."""
    im = Image.new('RGBA', (TEX_SIZE, TEX_SIZE), (255, 255, 255, 255))
    d = ImageDraw.Draw(im)
    h = TEX_SIZE // 2
    d.rectangle([0, 0, h - 1, h - 1], fill=(242, 244, 248, 255))      # 흰 차체
    d.rectangle([h, 0, TEX_SIZE - 1, h - 1], fill=(24, 26, 30, 255))  # 검은 하단
    # 유리(오른쪽 위 구역의 아래쪽) — UV_GLASS 가 여기를 가리킨다
    d.rectangle([h, int(h * 0.62), TEX_SIZE - 1, h - 1], fill=(44, 60, 82, 255))
    # 휠(밝은 회색) — carmesh.UV_WHEEL 이 여기를 찍는다
    d.rectangle([136, 8, 184, 52], fill=(176, 180, 188, 255))

    # 전면 = 보닛 경사면 그래픽 (UV_NOSE_RECT, x 5..59 / y 77..122)
    #  v1(y77) = 뒤쪽(캐빈 방향), v0(y122) = 코끝. 헤드라이트는 코끝 쪽에.
    d.rectangle([5, 77, 58, 122], fill=(238, 240, 244, 255))
    d.polygon([(6, 118), (20, 106), (24, 112), (10, 122)], fill=(180, 230, 245, 255))
    d.polygon([(57, 118), (43, 106), (39, 112), (53, 122)], fill=(180, 230, 245, 255))
    d.rectangle([27, 112, 36, 122], fill=(30, 32, 36, 255))    # 코끝 흡기구
    d.line([(31, 77), (31, 104)], fill=(210, 214, 220, 255), width=2)  # 보닛 라인
    # 후면 그래픽 (UV_TAIL_RECT, x 69..122) — 실제 보이는 대역은 y 101..120
    d.rectangle([69, 77, 122, 122], fill=(238, 240, 244, 255))
    d.rectangle([69, 115, 122, 122], fill=(30, 32, 36, 255))   # 디퓨저
    d.rectangle([70, 101, 92, 108], fill=(214, 40, 46, 255))   # 테일램프
    d.rectangle([99, 101, 121, 108], fill=(214, 40, 46, 255))
    d.rectangle([90, 104, 101, 113], fill=(60, 62, 68, 255))   # 번호판 자리

    # 아래 절반 = 태극 문양판
    d.rectangle([0, h, TEX_SIZE - 1, TEX_SIZE - 1], fill=(238, 240, 244, 255))
    cx, cy, r = TEX_SIZE // 2, h + TEX_SIZE // 4, TEX_SIZE // 5
    # 태극: 위 빨강, 아래 파랑, 가운데 S 곡선
    d.pieslice([cx - r, cy - r, cx + r, cy + r], 180, 360, fill=(205, 45, 55, 255))
    d.pieslice([cx - r, cy - r, cx + r, cy + r], 0, 180, fill=(30, 70, 160, 255))
    rr = r // 2
    d.ellipse([cx - r, cy - rr, cx, cy + rr], fill=(30, 70, 160, 255))
    d.ellipse([cx, cy - rr, cx + r, cy + rr], fill=(205, 45, 55, 255))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(20, 22, 26, 255), width=3)
    # 원본 차 텍스처가 전부 DXT1 이다. DXT5 는 이 기기에서 단색으로 뭉갠다.
    return im.convert('RGB')


# ------------------------------------------------------- 압축 메시 인코딩
# 실기 실험 결과: 비압축 메시는 차고(쉬는 자세)에선 멀쩡하지만 주행에서
# 스킨이 무시되어 차가 눕는다. 원본 차 메시(압축)를 꽂으면 주행도 선다.
# 그래서 원본과 똑같이 m_CompressedMesh 에 비트팩해서 넣는다.
# 패킹 규칙(원본 실측): LSB 우선 비트스트림, 길이 = ceil(개수*비트/8).
# 실수는 (값-start)/range 를 (2^비트-1) 단계로 양자화. range/start 는
# 배열 전체(x·y·z 통틀어)의 최소/최대다.
def _pack_bits(vals, bits):
    data = bytearray((len(vals) * bits + 7) // 8)
    pos = 0
    for v in vals:
        for b in range(bits):
            if (v >> b) & 1:
                data[pos >> 3] |= 1 << (pos & 7)
            pos += 1
    return bytes(data)


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


def build_mesh_compressed(donor_tree, gm):
    """원본(압축) 메시 트리를 바탕으로 내 형상을 같은 방식으로 담는다."""
    t = dict(donor_tree)
    t['m_Name'] = NEW
    n = len(gm.v)

    ctr, ext = carmesh.bounds(gm)
    aabb = {'m_Center': {'x': ctr[0], 'y': ctr[1], 'z': ctr[2]},
            'm_Extent': {'x': ext[0], 'y': ext[1], 'z': ext[2]}}
    t['m_SubMeshes'] = [{
        'firstByte': 0, 'indexCount': len(gm.t), 'topology': 0,
        'firstVertex': 0, 'vertexCount': n, 'localAABB': aabb,
    }]
    t['m_LocalAABB'] = aabb

    cm = dict(donor_tree['m_CompressedMesh'])
    flat = [c for v in gm.v for c in v]
    cm['m_Vertices'] = _packed_float(flat, 10)
    cm['m_UV'] = _packed_float([c for uv in gm.uv for c in uv], 8)
    # 정점마다 영향 본 1개: 가중치 31(=1.0)이 나오면 다음 정점으로 넘어간다
    cm['m_Weights'] = _packed_int([31] * n, 5)
    cm['m_BoneIndices'] = _packed_int([0] * n, 2)   # 전부 Bone_body
    cm['m_Triangles'] = _packed_int(list(gm.t), 10)
    t['m_CompressedMesh'] = cm

    # 비압축 쪽은 원본과 똑같이 비워 둔다 (donor_tree 가 이미 빈 상태)
    return t


# ---------------------------------------------------------------- 메시
def build_mesh_tree(donor_tree, gm):
    """생성한 형상을 압축 없는 Mesh 타입트리로 옮긴다."""
    t = dict(donor_tree)
    t['m_Name'] = NEW
    t['m_MeshCompression'] = 0
    t['m_StreamCompression'] = 0
    t['m_IsReadable'] = True
    t['m_KeepVertices'] = False       # Phoenix_A 실측과 동일하게
    t['m_KeepIndices'] = False
    t['m_Shapes'] = []
    t['m_ShapeVertices'] = []
    t['m_MeshUsageFlags'] = 0

    n = len(gm.v)
    # 스키닝 메시는 맵 메시와 **배치가 다르다**. 유니티 4 는 스킨을 CPU 로 굽고
    # 그 결과를 0번 스트림에 덮어쓰기 때문에, 0번에는 위치만 있어야 하고
    # UV 는 1번 스트림으로 빠져 있어야 한다. 한 스트림에 다 몰아넣으면
    # 위치는 맞는데 UV 가 뭉개져 차가 단색 덩어리가 된다(실기 확인).
    # 배치는 중국판 차 메시(Phoenix_A · cyclone_C_LOW · mp4-12c_LOW)를 실측해
    # 그대로 따랐다: 채널마스크 9, 스트림0 stride 12, 스트림1 stride 8,
    # 법선도 정점색도 없다. 셰이더가 Mobile-Lightmap-Unlit 이라 필요 없다.
    s0 = bytearray()                       # 위치만 (12)
    for (x, y, z) in gm.v:
        s0 += struct.pack('<fff', x, y, z)
    while len(s0) % 16:                    # 스트림 시작은 16바이트 경계
        s0.append(0)
    s1 = bytearray()                       # uv0 만 (8) — Phoenix_A 와 동일
    for (u, v) in gm.uv:
        s1 += struct.pack('<ff', u, v)
    buf = s0 + s1

    idx = bytearray()
    for i in gm.t:
        idx += struct.pack('<H', i)

    ctr, ext = carmesh.bounds(gm)
    aabb = {'m_Center': {'x': ctr[0], 'y': ctr[1], 'z': ctr[2]},
            'm_Extent': {'x': ext[0], 'y': ext[1], 'z': ext[2]}}

    t['m_IndexBuffer'] = bytes(idx)
    t['m_SubMeshes'] = [{
        'firstByte': 0, 'indexCount': len(gm.t), 'topology': 0,
        'firstVertex': 0, 'vertexCount': n, 'localAABB': aabb,
    }]
    t['m_LocalAABB'] = aabb

    ch = lambda s, o, f, dim: {'stream': s, 'offset': o, 'format': f, 'dimension': dim}
    t['m_VertexData'] = {
        'm_CurrentChannels': 9,           # 0 위치 · 3 uv0 (Phoenix_A 와 동일)
        'm_VertexCount': n,
        'm_Channels': [ch(0, 0, 0, 3), ch(0, 0, 0, 0), ch(0, 0, 0, 0),
                       ch(1, 0, 0, 2), ch(0, 0, 0, 0), ch(0, 0, 0, 0)],
        'm_Streams': [{'channelMask': 1, 'offset': 0, 'stride': 12,
                       'dividerOp': 0, 'frequency': 0},
                      {'channelMask': 8, 'offset': len(s0), 'stride': 8,
                       'dividerOp': 0, 'frequency': 0}] +
                     [{'channelMask': 0, 'offset': 0, 'stride': 0,
                       'dividerOp': 0, 'frequency': 0} for _ in range(2)],
        'm_DataSize': bytes(buf),
    }

    # 본은 하나에만 묶는다. 쉬는 자세에서는 어느 본에 묶든 결과가 같다
    # (최종 = 본월드행렬 x 바인드포즈 이고, 바인드 시점엔 서로 역행렬이다).
    # 바퀴가 따로 돌지 않는다는 뜻이지만 형태는 정확히 나온다.
    t['m_Skin'] = [{'weight[0]': 1.0, 'weight[1]': 0.0,
                    'weight[2]': 0.0, 'weight[3]': 0.0,
                    'boneIndex[0]': 0, 'boneIndex[1]': 0,
                    'boneIndex[2]': 0, 'boneIndex[3]': 0} for _ in range(n)]

    # 압축 메시는 비운다
    empty = {'m_NumItems': 0, 'm_Range': 0.0, 'm_Start': 0.0,
             'm_Data': bytes(), 'm_BitSize': 0}
    cm = {}
    for k, v in donor_tree['m_CompressedMesh'].items():
        cm[k] = dict((kk, empty[kk]) for kk in v.keys() if kk in empty)
    t['m_CompressedMesh'] = cm
    return t


# ---------------------------------------------------------------- 파일 쓰기
def write_serialized(out_path, meta_src, objects, externals):
    """objects = [(path_id, class_id, bytes)] 를 포맷 9 파일로 쓴다."""
    data = bytearray()
    recs = []
    for pid, cid, blob in objects:
        while len(data) % 8:
            data.append(0)
        recs.append({'path_id': pid, 'start': len(data), 'size': len(blob),
                     'class_id': cid})
        data += blob

    meta = meta_src['unity'].encode('utf-8') + b'\x00'
    meta += struct.pack('<i', meta_src['platform'])
    meta += struct.pack('<i', 0)
    meta += struct.pack('<i', meta_src['big_id'])
    meta += struct.pack('<i', len(recs))
    for r in recs:
        meta += struct.pack('<iIIiHh', r['path_id'], r['start'], r['size'],
                            r['class_id'], r['class_id'], 0)
    meta += struct.pack('<i', len(externals))
    for name in externals:
        meta += b'\x00' + b'\x00' * 16 + struct.pack('<i', 0) \
            + name.encode('utf-8') + b'\x00'
    meta += b'\x00'

    data_offset = ALIGN(20 + len(meta) + 64)
    head = struct.pack('>IIII', len(meta), data_offset + len(data), 9, data_offset)
    head += bytes([0, 0, 0, 0])
    out = bytearray(head + meta)
    while len(out) < data_offset:
        out += b'\x00'
    out += data
    io.open(out_path, 'wb').write(bytes(out))
    return len(out)


def load(fn):
    p = os.path.join(D, fn)
    raw = io.open(p, 'rb').read()
    return SerializedFile(EndianBinaryReader(raw), None), parse(p), raw


def walk_pptr(node, fn):
    """타입트리 안의 모든 PPtr 을 찾아 fn(dict) 을 먹인다."""
    n = 0
    if isinstance(node, dict):
        if 'm_FileID' in node and 'm_PathID' in node:
            fn(node)
            return 1
        for v in node.values():
            n += walk_pptr(v, fn)
    elif isinstance(node, (list, tuple)):
        for v in node:
            n += walk_pptr(v, fn)
    return n


def build_all():
    gm = carmesh.build()
    ctr, ext = carmesh.bounds(gm)
    print('메시: 정점 %d · 삼각형 %d · %.2f x %.2f x %.2f'
          % (len(gm.v), len(gm.t) // 3, ext[0] * 2, ext[1] * 2, ext[2] * 2))

    model, model_meta, _ = load(DONOR_MODEL)
    prefab, prefab_meta, prefab_raw = load(DONOR_PREFAB)
    matf, mat_meta, _ = load('d7dae3647564ca94798f0b5c2bba2a6f')

    # 내 파일의 외부 목록 = 프리팹의 외부 + 재질이 쓰는 셰이더
    my_ext = [os.path.basename(e) for e in prefab_meta['externals']]
    mat_ext = [os.path.basename(e) for e in mat_meta['externals']]
    shader_ext = mat_ext[0]                       # 0000...f000... (내장 셰이더)
    if shader_ext not in my_ext:
        my_ext.append(shader_ext)
    idx = dict((n, i + 1) for i, n in enumerate(my_ext))

    MESH_PID, TEX_PID, MAT_PID = 1, 2, 3
    objs = []

    # ---- 메시 -----------------------------------------------------------
    if os.environ.get('TAEGEUK_DONORMESH'):
        # 진단용: 원본 압축 메시를 그대로 쓴다 (형상은 람보르기니).
        # TAEGEUK_DONORMESH=name 이면 이름만 Taegeukho 로 바꾼다 (이름 이분법).
        if os.environ['TAEGEUK_DONORMESH'] in ('reenc', 'reenc0'):
            # 원본 압축 데이터를 풀어 내 인코더로 다시 싼다.
            # reenc  = 스킨도 원본 그대로  -> 인코더 검증
            # reenc0 = 스킨만 전부 본0    -> 본 분포 검증
            dt = dict(model.objects[1].read_typetree())
            dt['m_Name'] = NEW
            cm = dict(dt['m_CompressedMesh'])
            def dec_f(pv):
                q = _unpack_bits(bytes(pv['m_Data']), pv['m_BitSize'], pv['m_NumItems'])
                top = (1 << pv['m_BitSize']) - 1
                return [pv['m_Start'] + x * pv['m_Range'] / top for x in q]
            verts = dec_f(cm['m_Vertices'])
            uvs = dec_f(cm['m_UV'])
            tris = _unpack_bits(bytes(cm['m_Triangles']['m_Data']), 10,
                                cm['m_Triangles']['m_NumItems'])
            nv = cm['m_Vertices']['m_NumItems'] // 3
            if os.environ['TAEGEUK_DONORMESH'] == 'reenc0':
                bones = [0] * nv
            else:
                bones = _unpack_bits(bytes(cm['m_BoneIndices']['m_Data']), 2,
                                     cm['m_BoneIndices']['m_NumItems'])
            cm['m_Vertices'] = _packed_float(verts, 10)
            cm['m_UV'] = _packed_float(uvs, 8)
            cm['m_Weights'] = _packed_int([31] * nv, 5)
            cm['m_BoneIndices'] = _packed_int(bones, 2)
            cm['m_Triangles'] = _packed_int(tris, 10)
            dt['m_CompressedMesh'] = cm
            objs.append((MESH_PID, 43, bytes(model.objects[1].save_typetree(dt))))
        elif os.environ['TAEGEUK_DONORMESH'] == 'name':
            dt = dict(model.objects[1].read_typetree())
            dt['m_Name'] = NEW
            objs.append((MESH_PID, 43, bytes(model.objects[1].save_typetree(dt))))
        else:
            rec = [o for o in model_meta['objects'] if o['path_id'] == 1][0]
            raw = io.open(os.path.join(D, DONOR_MODEL), 'rb').read()
            st = model_meta['data_offset'] + rec['start']
            objs.append((MESH_PID, 43, raw[st:st + rec['size']]))
    else:
        mtree = build_mesh_compressed(model.objects[1].read_typetree(), gm)
        objs.append((MESH_PID, 43, bytes(model.objects[1].save_typetree(mtree))))

    # ---- 텍스처 ---------------------------------------------------------
    texf, _, _ = load('fcbdea69c77d91f45ba387ed1ef3671f')
    tex_obj = [o for o in texf.objects.values() if o.type.name == 'Texture2D'][0]
    ttree = dict(tex_obj.read_typetree())
    im = make_texture()
    blob, fmt = T2C.image_to_texture2d(im, TextureFormat.DXT1)
    ttree.update({'m_Name': NEW, 'm_Width': TEX_SIZE, 'm_Height': TEX_SIZE,
                  'm_TextureFormat': int(fmt), 'm_MipMap': False,
                  'm_MipCount': 1, 'm_CompleteImageSize': len(blob),
                  'image data': bytes(blob)})
    if 'm_ImageCount' in ttree:
        ttree['m_ImageCount'] = 1
    objs.append((TEX_PID, 28, bytes(tex_obj.save_typetree(ttree))))
    print('텍스처: %dx%d %s %d바이트' % (TEX_SIZE, TEX_SIZE, fmt, len(blob)))

    # ---- 재질 -----------------------------------------------------------
    mo = matf.objects[1]
    mtree2 = dict(mo.read_typetree())
    mtree2['m_Name'] = NEW
    mtree2['m_Shader'] = {'m_FileID': idx[shader_ext], 'm_PathID': 1}
    for k, v in mtree2['m_SavedProperties']['m_TexEnvs']:
        v['m_Texture'] = {'m_FileID': 0, 'm_PathID': TEX_PID}
    if os.environ.get('TAEGEUK_PROBE'):
        # 진단용: 재질이 실제로 쓰이는지 보려고 색을 빨강으로 둔다
        for k, v in mtree2['m_SavedProperties']['m_Colors']:
            if k['name'] == '_Color':
                v.update({'r': 1.0, 'g': 0.0, 'b': 0.0, 'a': 1.0})
    objs.append((MAT_PID, 21, bytes(mo.save_typetree(mtree2))))

    # ---- 프리팹 통째로 베끼기 -------------------------------------------
    src_ext = [os.path.basename(e) for e in prefab_meta['externals']]
    pmap = dict((pid, 10 + i) for i, pid in enumerate(sorted(prefab.objects)))
    recs = dict((o['path_id'], o) for o in prefab_meta['objects'])

    def fix(p):
        f, q = p['m_FileID'], p['m_PathID']
        if f == 0:
            p['m_PathID'] = pmap.get(q, q)
        else:
            nm = src_ext[f - 1]
            p['m_FileID'] = idx.get(nm, 0)

    # 프리팹이 참조하는 '차 재질' 파일들 (람보르기니 본체 + 저품질)
    MAT_FILES = {'d7dae3647564ca94798f0b5c2bba2a6f',
                 '471d72379d3479c44968ed0acb52efad'}
    mbptr = []
    kept = 0
    for pid in sorted(prefab.objects):
        o = prefab.objects[pid]
        cid = int(o.class_id)
        if o.type.name == 'MonoBehaviour':
            # 타입트리가 없다. 원시 바이트로 옮기고 앞의 두 PPtr 만 고친다.
            r = recs[pid]
            st = prefab_meta['data_offset'] + r['start']
            b = bytearray(prefab_raw[st:st + r['size']])
            gf, gp = struct.unpack_from('<ii', b, 0)
            if gf == 0:
                struct.pack_into('<ii', b, 0, 0, pmap.get(gp, gp))
            sf_, sp_ = struct.unpack_from('<ii', b, 12)
            if sf_:
                struct.pack_into('<ii', b, 12, idx.get(src_ext[sf_ - 1], 0), sp_)
            # ChangeTextureMaterial 은 Start() 에서 renderer.material 을
            # 자기가 들고 있는 Material[] 로 **덮어쓴다**. 렌더러만 고치면
            # 소용이 없다. 배열의 재질 참조를 내 재질로 돌려놓는다.
            # (타입트리가 없어 자리를 바이트로 찾는다: 재질 파일을 가리키는
            #  8바이트 쌍을 통째로 바꾼다)
            for j in range(20, len(b) - 7, 4):
                f2, p2 = struct.unpack_from('<ii', b, j)
                if 0 < f2 <= len(src_ext) and p2 == 1 and \
                        src_ext[f2 - 1] in MAT_FILES:
                    struct.pack_into('<ii', b, j, 0, MAT_PID)
                    mbptr.append((pmap[pid], j))
            objs.append((pmap[pid], cid, bytes(b)))
            kept += 1
            continue

        t = o.read_typetree()
        if o.type.name == 'GameObject':
            # **루트만** 이름을 바꾼다. 안쪽 오브젝트 이름을 건드리면
            # 원본 애니메이션 클립의 경로가 어긋난다.
            if t['m_Name'].startswith('Player'):
                t['m_Name'] = t['m_Name'].replace(OLD, NEW)
        if o.type.name == 'SkinnedMeshRenderer':
            t['m_Mesh'] = {'m_FileID': 0, 'm_PathID': MESH_PID}
            t['m_Materials'] = [{'m_FileID': 0, 'm_PathID': MAT_PID}]
        walk_pptr(t, fix)
        if o.type.name == 'SkinnedMeshRenderer':
            t['m_Mesh'] = {'m_FileID': 0, 'm_PathID': MESH_PID}
            t['m_Materials'] = [{'m_FileID': 0, 'm_PathID': MAT_PID}]
        objs.append((pmap[pid], cid, bytes(o.save_typetree(t))))

    root = [pid for pid in sorted(prefab.objects)
            if prefab.objects[pid].type.name == 'GameObject'
            and prefab.objects[pid].read_typetree()['m_Name'].startswith('Player')]
    root_pid = pmap[root[0]] if root else pmap[sorted(prefab.objects)[0]]
    print('프리팹 %d개 복제 (스크립트 %d개 유지), 루트 pathID %d'
          % (len(prefab.objects), kept, root_pid))

    size = write_serialized(OUT, model_meta, objs, my_ext)
    print('%s (%d바이트) 외부 %d개' % (OUT, size, len(my_ext)))
    # 스크립트 안 재질 참조는 타입트리가 없어 sfmerge 가 스스로 못 옮긴다.
    # 자리를 알려 준다. packspec 줄 뒤에 그대로 붙이면 된다.
    spec = ':'.join('mbptr=%d@%d' % x for x in mbptr)
    print('스크립트 재질 참조 %d곳 → packspec 옵션: %s' % (len(mbptr), spec))
    io.open('taegeuk_mbptr.txt', 'w').write(spec)
    return root_pid


def main_old():
    gm = carmesh.build()
    ctr, ext = carmesh.bounds(gm)
    print('메시 생성: 정점 %d · 삼각형 %d · 크기 %.2f x %.2f x %.2f'
          % (len(gm.v), len(gm.t) // 3, ext[0] * 2, ext[1] * 2, ext[2] * 2))

    model = SerializedFile(EndianBinaryReader(
        io.open(os.path.join(D, DONOR_MODEL), 'rb').read()), None)
    donor_mesh = model.objects[1]
    mtree = build_mesh_tree(donor_mesh.read_typetree(), gm)
    mesh_blob = bytes(donor_mesh.save_typetree(mtree))
    print('메시 직렬화: %d바이트' % len(mesh_blob))

    # 되읽어 확인
    meta_src = parse(os.path.join(D, DONOR_MODEL))
    size = write_serialized(OUT, meta_src, [(1, 43, mesh_blob)], [])
    chk = SerializedFile(EndianBinaryReader(io.open(OUT, 'rb').read()), None)
    t2 = chk.objects[1].read_typetree()
    vd = t2['m_VertexData']
    print('되읽기: 이름 %s · 정점 %d · 인덱스 %d바이트 · 스킨 %d · 압축 %d'
          % (t2['m_Name'], vd['m_VertexCount'], len(t2['m_IndexBuffer']),
             len(t2['m_Skin']), t2['m_MeshCompression']))
    print('%s (%d바이트)' % (OUT, size))

    im = make_texture()
    im.save('taegeuk_tex.png')
    print('텍스처: taegeuk_tex.png (%dx%d)' % im.size)


if __name__ == '__main__':
    build_all()
