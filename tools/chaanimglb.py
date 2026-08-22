# -*- coding: utf-8 -*-
"""뼈대와 동작까지 담은 glTF 2.0 (.glb) 내보내기.

정지 메시용 글쓴이는 `chaassets.write_glb` 다. 여기는 스키닝과 동작이
붙는 쪽이라 따로 뒀다.

두 가지가 맞아떨어져서 셈이 깔끔하다.

  · 유니티의 역바인드(m_BindPose)에는 **렌더러의 월드 행렬이 이미 들어
    있다.** 그래서 정점은 메시 공간 그대로 두면 된다.
  · glTF 도 스킨 메시 마디의 자체 변환을 무시하도록 규정돼 있다.
    (spec: "the transform of the skinned mesh node MUST be ignored")

즉 유니티가 하던 셈과 같은 모양이라, 뼈만 옮겨 심으면 된다.

축은 마디 하나로 해결한다. glTF 는 Y-up 규격이고 이 게임은 Z-up 이다.
정점을 돌리는 대신 **맨 위에 마디를 씌워** X축 -90° 를 준다. 뼈 행렬이
그 밑에서 계산되므로 자세도 함께 돌아간다.
"""
import io
import json
import math
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chaassets as A                                     # noqa: E402
import chaanim as N                                       # noqa: E402

# X축 -90°. (x, y, z) -> (x, z, -y) 와 같은 회전이다.
YUP_Q = [-0.7071067811865476, 0.0, 0.0, 0.7071067811865476]


def _pad4(b, fill=b'\0'):
    return b + fill * ((-len(b)) % 4)


def write(path, rigd, v, uv, tri, clips, png=None, fps=30.0):
    """(파일크기, 담은 동작 수) 를 돌려준다."""
    tr, root = rigd['tr'], rigd['root']
    order, stack = [], [root]
    while stack:
        cur = stack.pop()
        order.append(cur)
        stack += [c for c in tr[cur].get('children', []) if c in tr]
    nidx = dict((pid, i + 1) for i, pid in enumerate(order))   # 0 은 씌운 마디

    nodes = [{'name': 'Z_up_to_Y_up', 'rotation': YUP_Q,
              'children': [nidx[root]]}]
    for pid in order:
        t = tr[pid]
        n = {'name': t['name'] or ('node%d' % pid),
             'translation': list(t['t']),
             'rotation': list(t['r']),
             'scale': list(t['s'])}
        kids = [nidx[c] for c in t.get('children', []) if c in nidx]
        if kids:
            n['children'] = kids
        nodes.append(n)
    mesh_node = nidx.get(rigd.get('renderTr')) or nidx[root]
    nodes[mesh_node]['mesh'] = 0
    nodes[mesh_node]['skin'] = 0

    parts, views, accs = [], [], []
    off = [0]

    def put(blob, target=None):
        blob = _pad4(blob)
        vw = {'buffer': 0, 'byteOffset': off[0], 'byteLength': len(blob)}
        if target:
            vw['target'] = target
        views.append(vw)
        parts.append(blob)
        off[0] += len(blob)
        return len(views) - 1

    def acc(bv, comp, count, typ, extra=None):
        a = {'bufferView': bv, 'componentType': comp, 'count': count,
             'type': typ}
        if extra:
            a.update(extra)
        accs.append(a)
        return len(accs) - 1

    idx = [i for i in tri if i < len(v)]
    idx = idx[:len(idx) - len(idx) % 3]
    a_idx = acc(put(struct.pack('<%dI' % len(idx), *idx), 34963),
                5125, len(idx), 'SCALAR')
    a_pos = acc(put(b''.join(struct.pack('<fff', *p) for p in v), 34962),
                5126, len(v), 'VEC3',
                {'min': [min(p[i] for p in v) for i in range(3)],
                 'max': [max(p[i] for p in v) for i in range(3)]})
    nn = A.normals(v, tri)
    a_nrm = acc(put(b''.join(struct.pack('<fff', *p) for p in nn), 34962),
                5126, len(v), 'VEC3')
    attrs = {'POSITION': a_pos, 'NORMAL': a_nrm}
    if uv and len(uv) >= len(v):
        attrs['TEXCOORD_0'] = acc(
            put(b''.join(struct.pack('<ff', t[0], 1.0 - t[1])
                         for t in uv[:len(v)]), 34962),
            5126, len(v), 'VEC2')

    skin, nb = rigd['skin'], len(rigd['bones'])
    jb, wb = bytearray(), bytearray()
    for i in range(len(v)):
        s = skin[i] if i < len(skin) else None
        ws, js = [0.0] * 4, [0] * 4
        if s:
            for k in range(4):
                w = float(s['weight[%d]' % k])
                b = int(s['boneIndex[%d]' % k])
                ws[k] = w if w > 0 else 0.0
                js[k] = b if 0 <= b < nb else 0
        tot = sum(ws)
        ws = [1.0, 0.0, 0.0, 0.0] if tot <= 0 else [x / tot for x in ws]
        jb += struct.pack('<HHHH', *js)
        wb += struct.pack('<ffff', *ws)
    attrs['JOINTS_0'] = acc(put(bytes(jb), 34962), 5123, len(v), 'VEC4')
    attrs['WEIGHTS_0'] = acc(put(bytes(wb), 34962), 5126, len(v), 'VEC4')

    # 역바인드는 glTF 규격이 **열 우선**이다. 우리 것은 행 우선이라 뒤집는다.
    ib = bytearray()
    for i in range(nb):
        m = rigd['bind'][i] if i < len(rigd['bind']) else N.m_ident()
        for c in range(4):
            for r in range(4):
                ib += struct.pack('<f', m[r * 4 + c])
    a_ibm = acc(put(bytes(ib)), 5126, nb, 'MAT4')

    name = rigd.get('meshName') or 'car'
    g = {'asset': {'version': '2.0', 'generator': 'chatool (다함께 차차차)'},
         'scene': 0, 'scenes': [{'nodes': [0]}], 'nodes': nodes,
         'meshes': [{'name': name, 'primitives': [
             {'attributes': attrs, 'indices': a_idx, 'material': 0}]}],
         'skins': [{'inverseBindMatrices': a_ibm, 'skeleton': nidx[root],
                    'joints': [nidx.get(b, nidx[root])
                               for b in rigd['bones']]}],
         'materials': [{'name': name, 'doubleSided': False,
                        'pbrMetallicRoughness': {'metallicFactor': 0.0,
                                                 'roughnessFactor': 0.75}}],
         'accessors': accs, 'bufferViews': views}

    if png and os.path.exists(png):
        bv = put(io.open(png, 'rb').read())
        g['images'] = [{'bufferView': bv, 'mimeType': 'image/png'}]
        g['samplers'] = [{'magFilter': 9729, 'minFilter': 9987,
                          'wrapS': 10497, 'wrapT': 10497}]
        g['textures'] = [{'sampler': 0, 'source': 0}]
        g['materials'][0]['pbrMetallicRoughness']['baseColorTexture'] = \
            {'index': 0}

    anims = []
    paths = rigd['paths']
    by_path = {}
    for pid, p in paths.items():
        by_path.setdefault(p, pid)
    for cl in clips:
        n = max(2, int(round((cl['length'] or 0) * fps)) + 1)
        times = [i / fps for i in range(n)]
        a_t = acc(put(b''.join(struct.pack('<f', t) for t in times)),
                  5126, n, 'SCALAR',
                  {'min': [times[0]], 'max': [times[-1]]})
        chans, samps = [], []
        for p, pid in by_path.items():
            if pid not in nidx:
                continue
            base = tr[pid]
            for key, src, cnt, rest in (
                    ('translation', cl['pos'], 3, base['t']),
                    ('rotation', cl['rot'], 4, base['r']),
                    ('scale', cl['scl'], 3, base['s'])):
                keys = src.get(p)
                if not keys:
                    continue
                buf = bytearray()
                for t in times:
                    val = N._eval(keys, t) or list(rest)
                    if key == 'rotation':
                        L = math.sqrt(sum(x * x for x in val)) or 1.0
                        val = [x / L for x in val]
                    buf += struct.pack('<%df' % cnt, *val[:cnt])
                a_v = acc(put(bytes(buf)), 5126, n,
                          'VEC4' if cnt == 4 else 'VEC3')
                samps.append({'input': a_t, 'output': a_v,
                              'interpolation': 'LINEAR'})
                chans.append({'sampler': len(samps) - 1,
                              'target': {'node': nidx[pid], 'path': key}})
        if chans:
            anims.append({'name': cl['name'], 'channels': chans,
                          'samplers': samps})
    if anims:
        g['animations'] = anims

    blob = b''.join(parts)
    g['buffers'] = [{'byteLength': len(blob)}]
    js = _pad4(json.dumps(g, ensure_ascii=False,
                          separators=(',', ':')).encode('utf-8'), b' ')
    with io.open(path, 'wb') as f:
        f.write(b'glTF' + struct.pack('<II', 2,
                                      12 + 8 + len(js) + 8 + len(blob)))
        f.write(struct.pack('<I', len(js)) + b'JSON' + js)
        f.write(struct.pack('<I', len(blob)) + b'BIN\0' + blob)
    return len(blob) + len(js), len(anims)
