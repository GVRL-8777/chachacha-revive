# -*- coding: utf-8 -*-
"""잘려 나간 차 **트로이**를 게임 안에 되살린다.

무엇이 남아 있었나. 한국 초기판(`8.apk`, 2013-01)에는 `Troy` 라는 이름의
메시 · 재질 · 텍스처가 통째로 들어 있다. 그림을 뽑아 보면 **바퀴 달린
트로이 목마**다. 그런데 정작 그것으로 차를 만드는 조각이 없다.

  · `car/troy/troy`            메시 + 본 + 애니메이션 (1143정점 · 삼각형 1157)
  · `car/troy/materials/troy`  재질
  · `car/troy/troy_lock`       잠금 그림
  · `car/troy/player_troy_?`   **없다**

다른 차는 등급마다 `player_<이름>_<등급>` 프리팹이 있는데 트로이만 없다.
한국 마지막 정식판(7.7.0)에도, 중국판에도 흔적이 없다. 만들다 만 채로
잘린 차다. 그래서 '복원'은 **프리팹을 우리가 만들어 주는 일**이 된다.

## 어떻게 넣나 — 런처를 거치지 않고 코드로

헬리를 넣을 때와 같은 길이다. 런처의 '모델 들여오기' 카드는 OBJ·PNG 를
받아 새 차를 짓는 도구라 여기엔 맞지 않는다. 여기서는 이미 있는 자산을
쓰므로 이 파일 하나가 전부 한다.

  1. `troy.assets`  — 메시 · 텍스처 · 재질 13개 · 효과 · 프리팹 10벌을
     담은 직렬화 파일 하나. 유니티 4.1 배치로 **새로 쓴다**.
  2. `packspec.txt` 에 한 줄 → `bundles/pack.unity3d` 다시 굽기
  3. CarDataBase 에 항목 한 줄 (`trimcars` 가 비워 둔 공백 자리에)
  4. 이름표 `CarName_Troy = 트로이`
  5. `newcars.json` · `chacnserver.py` 의 차 표

## 판본이 달라서 손봐야 했던 것

초기판은 **유니티 3.5.6f4**, 지금 빌드는 **4.1.5f1** 이다. 직렬화 배치가
달라 파일을 그대로 옮길 수 없다. 그래서 값만 읽어 4.1 쪽 그릇에 옮긴다.

  · 메시의 인덱스가 **삼각형 띠(strip)** 다. 4.1 의 이 게임 메시는 전부
    삼각형 목록(topology 0)이라 띠를 풀어 목록으로 바꾼다. 풀어 보면
    2675개 띠 인덱스가 삼각형 1157개 — 원본이 적어 둔 수와 정확히 맞는다.
  · 정점 배치도 3.5 는 한 줄기(stride 20)에 좌표+UV 를 섞어 담는데,
    이 빌드의 압축 없는 메시는 두 줄기(좌표 12 · UV 8, 16바이트 경계)다.
    그쪽에 맞춘다.
  · 뼈 가중치(3개 · 몸통/바퀴/그림자)와 bindpose 는 **그대로 옮긴다.**
    프리팹을 빌려 오는 피닉스와 뼈 계층이 값까지 똑같아서(실측) 그대로
    맞아떨어진다. 트로이가 작게 나오지 않는 것도 bindpose 안에 0.189배가
    이미 들어 있기 때문이다.

## 이름을 정할 때 조심한 것

번들에서 자산을 찾는 길은 **오브젝트 이름**이다(경로의 마지막 조각을
소문자로 만들어 찾는다). 그래서 빌려 온 프리팹 안의 `Phoenix_C` 를 그대로
두면 진짜 피닉스를 가릴 수 있다. 겉껍데기 이름은 전부 트로이 것으로
바꾸고, **뼈 이름(`Bone_body` 등)만 그대로 둔다** — 스크립트가 그 이름으로
찾기 때문이다.

**효과 오브젝트를 빠뜨리면 주행이 멈춘다.** `EffectManager.Setting` 이
`Instantiate(Load("Car/Troy/Troy_Effect"))` 를 부르는데 유니티의
`Instantiate(null)` 은 예외를 던지고, 그 예외가 `Player.Init` 의 준비
사슬을 끊는다. 차의 **충돌 상자도 그 효과 오브젝트 안에** 들어 있다.
실기에서 한 번 겪었다 — 자세한 것은 `docs/TROY.md`.

    python tools/addtroy.py --scan     무엇이 있고 무엇을 만들지 본다
    python tools/addtroy.py            넣는다
    python tools/addtroy.py --remove   뺀다
"""
import argparse
import io
import json
import os
import shutil
import struct
import sys

CODE = os.path.dirname(os.path.abspath(__file__))
HERE = os.path.dirname(CODE)
sys.path.insert(0, CODE)

DATA = os.path.join('assets', 'bin', 'Data')
TREE = os.path.join(HERE, 'x77')
XD = os.path.join(TREE, DATA)
KR8 = os.path.join(HERE, '_scratch', 'kr8', DATA)
OUT = os.path.join(HERE, 'troy.assets')
SPEC = os.path.join(HERE, 'packspec.txt')
NEWCARS = os.path.join(HERE, 'newcars.json')
CARDB = os.path.join(XD, 'ade64ecd8944d9640bb1438deb4f6fe3')
TEXTDB = os.path.join(XD, '50295c6b20ff907439e2ef8aa05f9ea7')
SERVER = os.path.join(CODE, 'chacnserver.py')
BUNDLE = os.path.join(HERE, 'bundles', 'pack.unity3d')
PACKDAT = os.path.join(HERE, 'pack.dat')
BAKDIR = os.path.join(HERE, 'backup', 'bundle')

# --- 초기판에서 가져오는 것 ---
KR_MODEL = 'f09e79b963a331d4194226e1b0bb8c89'      # Mesh:Troy + 본 + 애니메이션
KR_TEX = '52903eebf4acf7c4db1c6e2d85237785'        # Texture2D:Troy 256x256 ETC
KR_LOCKTEX = 'fb120465817a5fe4baa1e98c60b1508e'    # Texture2D:Troy_Lock

# --- 지금 빌드에서 그릇으로 빌리는 것 ---
D_MESH = '8db5b1e1c0838ef4fa20394f98e7d44e'        # Mesh:Phoenix_C (압축 없음)
D_TEX = 'fcbdea69c77d91f45ba387ed1ef3671f'         # Texture2D:Lamborghini 256 DXT1
D_MAT = 'c2fd032f46dd7904388207b4d0cface3'         # Material:Phoenix_C
D_PREFAB = '3bac2141e3f3c42fa94cc14e0b06c2ab'      # player_phoenix_c
D_LOCKMAT = 'f58417c5d48bb1a47957a1754fd99afc'     # Material:Lock (잠긴 차)
D_LAND = '0dc2540d2d75a465b855ebe6f842cdd5'        # AudioClip:jump landing
D_EFFECT = 'b03891a19a8514111a11ab126df0853f'      # Phoenix_Effect (미등 · 충돌상자)
SHADER = '0000000000000000f000000000000000'        # 재질이 가리키는 셰이더 파일

NAME = 'Troy'
LABEL = '트로이'
CAR_INDEX = 18                    # 서버 carNo 19. 비어 있는 자리다.
KLASSES = ('C', 'B', 'A', 'S', 'R')
ICON_ATLAS = 'Atlas_SpecialCarIcon'

# 등급 사다리. 이 게임 자신의 증가폭을 그대로 따른다 —
# 최고속 +28(R 은 +36) · 가속 +7(+9) · 다음단 +7(+9) · 가속2 +0.7(+0.9)
# · 연비 +1.4(+1.8). AVEO 와 피닉스에서 확인한 규칙이다.
# 트로이 자체의 수치는 어디에도 남아 있지 않다. 목마답게 **무겁고
# 조금 느리되 연비가 좋은** 쪽으로 잡았다.
BASE = dict(MaxSpeed=291, CarWeight=1500, SpeedPerSecond=51,
            NextStepSpeed=155, NextSpeedPerSecond=8.0, OilMileage=12.0)
STEP = dict(MaxSpeed=(28, 36), CarWeight=(100, 0), SpeedPerSecond=(7, 9),
            NextStepSpeed=(7, 9), NextSpeedPerSecond=(0.7, 0.9),
            OilMileage=(1.4, 1.8))

# 프리팹 안에서 바꿀 이름. 뼈 이름은 건드리지 않는다.
INNER = 'Phoenix_C'
INNER_NEW = 'Troy_Body'
ROOT = 'Player_Phoenix_C'


# ------------------------------------------------------------------ 읽기
def _sf(p):
    from UnityPy.streams import EndianBinaryReader
    from UnityPy.files.SerializedFile import SerializedFile
    return SerializedFile(EndianBinaryReader(io.open(p, 'rb').read()), None)


def _load(p):
    from sfparse import parse
    return _sf(p), parse(p), io.open(p, 'rb').read()


def read_troy():
    """초기판 메시를 (정점, UV, 삼각형목록, 스킨, bindpose) 로 읽는다."""
    sf = _sf(os.path.join(KR8, KR_MODEL))
    o = [x for x in sf.objects.values() if x.type.name == 'Mesh'][0]
    t = o.read_typetree()
    vd = t['m_VertexData']
    n = vd['m_VertexCount']
    blob = bytes(vd['m_DataSize'])
    stride = vd['m_Streams[0]']['stride']
    v = [struct.unpack_from('<3f', blob, i * stride) for i in range(n)]
    uv = [struct.unpack_from('<2f', blob, i * stride + 12) for i in range(n)]
    ib = bytes(t['m_IndexBuffer'])
    idx = struct.unpack('<%dH' % (len(ib) // 2), ib)
    # 삼각형 띠를 목록으로 푼다. 짝수 번째는 감기를 뒤집어 준다.
    tri = []
    for i in range(len(idx) - 2):
        a, b, c = idx[i], idx[i + 1], idx[i + 2]
        if a == b or b == c or a == c:
            continue
        tri += [a, b, c] if i % 2 == 0 else [a, c, b]
    want = t['m_SubMeshes'][0].get('triangleCount')
    if want and len(tri) // 3 != want:
        raise SystemExit('띠를 푼 삼각형 수가 안 맞습니다 (%d != %d)'
                         % (len(tri) // 3, want))
    return v, uv, tri, t['m_Skin'], t['m_BindPose']


def troy_image(fn):
    import UnityPy
    env = UnityPy.load(os.path.join(KR8, fn))
    o = [x for x in env.objects if x.type.name == 'Texture2D'][0]
    return o.read().image.convert('RGB')


# ------------------------------------------------------------------ 자산 짓기
def build_mesh(v, uv, tri, skin, bindpose):
    """유니티 4.1 의 압축 없는 메시 하나를 만든다.

    배치는 이 빌드 자신의 압축 없는 차 메시(`Phoenix_A` 등)를 그대로 본떴다 —
    줄기0 에 좌표(float32x3), 줄기1 에 UV(float32x2), 줄기 사이는 16바이트
    경계에 맞춘다."""
    sf, _m, _r = _load(os.path.join(XD, D_MESH))
    o = [x for x in sf.objects.values() if x.type.name == 'Mesh'][0]
    t = dict(o.read_typetree())

    lo = [min(p[i] for p in v) for i in range(3)]
    hi = [max(p[i] for p in v) for i in range(3)]
    aabb = {'m_Center': dict(zip('xyz', [(a + b) / 2.0 for a, b in zip(lo, hi)])),
            'm_Extent': dict(zip('xyz', [(b - a) / 2.0 for a, b in zip(lo, hi)]))}

    s0 = struct.pack('<%df' % (len(v) * 3), *[c for p in v for c in p])
    off1 = (len(s0) + 15) // 16 * 16
    s1 = struct.pack('<%df' % (len(uv) * 2), *[c for p in uv for c in p])

    ch = lambda st, of, dim: {'stream': st, 'offset': of,
                              'format': 0, 'dimension': dim}
    stream = lambda mask, of, stride: {'channelMask': mask, 'offset': of,
                                       'stride': stride, 'dividerOp': 0,
                                       'frequency': 0}
    t.update({
        # 번들에서 자산을 찾는 열쇠가 이름이다. `troy` 는 **재질**이 써야
        # 하므로(게임이 `Car/Troy/Materials/Troy` 로 다시 찾아 덮어쓴다)
        # 메시는 이름을 비켜 준다.
        'm_Name': '%s_Mesh' % NAME,
        'm_MeshCompression': 0,
        'm_SubMeshes': [{'firstByte': 0, 'indexCount': len(tri), 'topology': 0,
                         'firstVertex': 0, 'vertexCount': len(v),
                         'localAABB': aabb}],
        'm_LocalAABB': aabb,
        'm_IndexBuffer': list(struct.pack('<%dH' % len(tri), *tri)),
        'm_Skin': [dict(s) for s in skin],
        'm_BindPose': [dict(b) for b in bindpose],
        'm_VertexData': {
            'm_CurrentChannels': 9, 'm_VertexCount': len(v),
            'm_Channels': [ch(0, 0, 3), ch(0, 0, 0), ch(0, 0, 0),
                           ch(1, 0, 2), ch(0, 0, 0), ch(0, 0, 0)],
            'm_Streams': [stream(1, 0, 12), stream(8, off1, 8),
                          stream(0, 0, 0), stream(0, 0, 0)],
            'm_DataSize': s0 + b'\0' * (off1 - len(s0)) + s1,
        },
    })
    return bytes(o.save_typetree(t)), int(o.class_id)


def build_texture(img, name):
    from UnityPy.enums import TextureFormat
    from UnityPy.export import Texture2DConverter as T2C
    sf, _m, _r = _load(os.path.join(XD, D_TEX))
    o = [x for x in sf.objects.values() if x.type.name == 'Texture2D'][0]
    t = dict(o.read_typetree())
    if (img.width, img.height) != (t['m_Width'], t['m_Height']):
        from PIL import Image
        img = img.resize((t['m_Width'], t['m_Height']), Image.LANCZOS)
    blob, fmt = T2C.image_to_texture2d(img, TextureFormat.DXT1)
    t.update({'m_Name': name, 'm_TextureFormat': int(fmt), 'm_MipMap': False,
              'm_MipCount': 1, 'm_CompleteImageSize': len(blob),
              'image data': bytes(blob)})
    if 'm_ImageCount' in t:
        t['m_ImageCount'] = 1
    return bytes(o.save_typetree(t)), int(o.class_id)


def mat_names():
    """게임이 재질을 찾을 만한 이름을 모두 만든다.

    코드에 박힌 서식이 `Car/{0}/Materials/{1}` 과 `Car/{0}/Materials/{1}_{2}`
    두 가지다. 번들에서는 **경로의 마지막 조각**으로 찾으므로 그 조각이 될
    수 있는 이름을 다 만들어 둔다. 재질 하나는 200바이트 남짓이라 싸다."""
    out = [NAME]
    out += ['%s_%s' % (NAME, k) for k in KLASSES]
    return out + [n + '_Low' for n in list(out)]


def build_material(name, tex_pid, shader_idx, donor=None):
    sf, _m, _r = _load(donor or os.path.join(XD, D_MAT))
    o = [x for x in sf.objects.values() if x.type.name == 'Material'][0]
    t = dict(o.read_typetree())
    t['m_Name'] = name
    t['m_Shader'] = {'m_FileID': shader_idx, 'm_PathID': 1}
    for _k, val in t['m_SavedProperties']['m_TexEnvs']:
        val['m_Texture'] = {'m_FileID': 0, 'm_PathID': tex_pid}
    return bytes(o.save_typetree(t)), int(o.class_id)


# 프리팹에 붙은 스크립트. `sharedassets0.assets` 안의 pathID 로 가른다.
# (MonoScript 를 읽어 확인했다)
S_CHANGETEX = 60        # ChangeTextureMaterial — 재질 두 개(본 재질 · 잠금)
S_BASEDATA = 253        # BaseData            — 차 이름 · 무게 · 최고속
S_EFFECT = 306          # EffectManager       — 전부 비어 있다
S_CARDATA = 314         # PlayerCarData       — 연비 · 가속 · 다음단
S_CARLINK = 492         # CarDataLinker       — **CarIndex 를 글로 들고 있다**
S_JUMP = 616            # JumpLanding         — 착지 소리

# eCarClassType. 실제 차 프리팹 60여 개를 전수로 읽어 확인한 값이다.
# S 와 R 이 둘 다 0 인 것은 원판이 그렇게 굽혀 있어서다.
CLASS_ENUM = {'C': 3, 'B': 2, 'A': 1, 'S': 0, 'R': 0}


def _mbstr(s):
    """MonoBehaviour 안의 문자열 — 길이(int32) + 바이트 + 4바이트 정렬."""
    b = s.encode('utf-8')
    return struct.pack('<i', len(b)) + b + b'\0' * ((-len(b)) % 4)


def _skipstr(b, i):
    """i 자리의 문자열을 건너뛴 다음 자리."""
    n = struct.unpack_from('<i', b, i)[0]
    return i + 4 + n + ((-n) % 4)


def _fields(script, body, cls, pid_of):
    """스크립트별로 **값을 트로이 것으로 다시 채운다.**

    빌려 온 프리팹을 그대로 두면 트로이가 피닉스의 무게 · 최고속을 쓰고,
    `CarDataLinker` 가 들고 있는 CarIndex 도 피닉스(27) 그대로라 차 표를
    엉뚱하게 물어 온다. 그래서 이 넷은 손으로 다시 쓴다.

    돌려주는 것은 (필드 바이트, 그 안의 내부 PPtr 자리 목록)."""
    d = _sk = None
    if script == S_CHANGETEX:
        out = body[:8] + struct.pack('<i', 2)              # 랜덤여부 · 번호 · 배열 2
        out += struct.pack('<ii', 0, pid_of('mat'))        # 본 재질
        out += struct.pack('<ii', 0, pid_of('lock'))       # 잠겼을 때 재질
        return out, [12, 20]
    if script == S_JUMP:
        return struct.pack('<iiii', 0, pid_of('land'), 0, 0), [0]
    if script == S_BASEDATA:
        i = _skipstr(body, 0)
        return _mbstr(NAME) + struct.pack('<ii', cls['CarWeight'],
                                          cls['MaxSpeed']) + body[i + 8:], []
    if script == S_CARDATA:
        return struct.pack('<4f', cls['OilMileage'], cls['SpeedPerSecond'],
                           cls['NextStepSpeed'],
                           cls['NextSpeedPerSecond']) + body[16:], []
    if script == S_CARLINK:
        i = _skipstr(body, 8)
        return (body[:8] + _mbstr(str(CAR_INDEX))
                + struct.pack('<i', CLASS_ENUM[cls['CarClassType']])
                + body[i + 4:]), []
    return body, []                                        # EffectManager 등


def clone_prefab(base, klass, low, pids_of, cls):
    """빌려 온 차 프리팹을 통째로 베껴 새 pathID 로 옮긴다.

    본 · 애니메이션 · 스크립트가 그대로 붙어 있어야 차고에서도 주행에서도
    제대로 선다. 타입트리가 없는 MonoBehaviour 는 머리(오브젝트 · 스크립트
    · 이름)만 그대로 두고 **값은 다시 채운다** — `_fields` 를 보라."""
    from mktaegeuk import walk_pptr
    sf, meta, raw = _load(os.path.join(XD, D_PREFAB))
    src_ext = [os.path.basename(e) for e in meta['externals']]
    recs = dict((o['path_id'], o) for o in meta['objects'])
    pids = sorted(sf.objects)
    pmap = dict((pid, base + i) for i, pid in enumerate(pids))
    objs, mbptr, root_pid = [], [], None
    label = klass + low

    def newptr(f, p):
        """빌려 온 파일의 참조를 우리 것으로 옮긴다.

        외부 목록은 빌려 온 것 그대로 쓰므로 번호를 바꿀 일이 없다.
        메시와 재질만 우리 파일 안으로 끌어온다."""
        if f == 0:
            return 0, pmap.get(p, p)
        nm = src_ext[f - 1]
        if nm == D_MAT:
            return 0, pids_of('mat')
        if nm == D_MESH and p == 1:
            return 0, pids_of('mesh')
        return f, p

    for pid in pids:
        o = sf.objects[pid]
        cid = int(o.class_id)
        if o.type.name == 'MonoBehaviour':
            r = recs[pid]
            st = meta['data_offset'] + r['start']
            b = bytearray(raw[st:st + r['size']])
            script = struct.unpack_from('<i', b, 16)[0]
            struct.pack_into('<ii', b, 0, 0,
                             pmap[struct.unpack_from('<ii', b, 0)[1]])
            body, ptrs = _fields(script, bytes(b[24:]), cls, pids_of)
            objs.append((pmap[pid], cid, bytes(b[:24]) + body))
            mbptr += [(pmap[pid], 24 + off) for off in ptrs]
            continue

        t = o.read_typetree()
        if o.type.name == 'GameObject':
            nm = t['m_Name']
            if nm == ROOT:
                t['m_Name'] = 'Player_%s_%s' % (NAME, label)
                root_pid = pmap[pid]
            elif nm == INNER:
                t['m_Name'] = INNER_NEW
        walk_pptr(t, lambda p: p.update(
            dict(zip(('m_FileID', 'm_PathID'),
                     newptr(p['m_FileID'], p['m_PathID'])))))
        if o.type.name == 'SkinnedMeshRenderer':
            t['m_Mesh'] = {'m_FileID': 0, 'm_PathID': pids_of('mesh')}
            t['m_Materials'] = [{'m_FileID': 0, 'm_PathID': pids_of('mat')}]
        objs.append((pmap[pid], cid, bytes(o.save_typetree(t))))

    if root_pid is None:
        raise SystemExit('빌려 온 프리팹에서 %s 를 못 찾았습니다' % ROOT)
    return objs, root_pid, mbptr, len(pids)


def copy_object(path, want, rename=None):
    """다른 파일의 오브젝트 하나를 타입트리 왕복으로 그대로 떠 온다."""
    sf, _m, _r = _load(path)
    o = [x for x in sf.objects.values() if x.type.name == want][0]
    t = dict(o.read_typetree())
    if rename:
        t['m_Name'] = rename
    return bytes(o.save_typetree(t)), int(o.class_id)


def clone_file(path, base, rename, my_ext):
    """파일 하나를 통째로 베껴 새 pathID 로 옮긴다.

    타입트리가 다 있는 파일 전용이다(효과 오브젝트가 그렇다). 외부 참조는
    **이름으로** 우리 목록의 번호를 다시 찾는다 — 빌려 온 파일마다 번호가
    제 나름이라 그대로 두면 엉뚱한 곳을 가리킨다."""
    from mktaegeuk import walk_pptr
    sf, meta, _raw = _load(path)
    src_ext = [os.path.basename(e) for e in meta['externals']]
    pids = sorted(sf.objects)
    pmap = dict((p, base + i) for i, p in enumerate(pids))
    objs, root = [], None
    for pid in pids:
        o = sf.objects[pid]
        t = o.read_typetree()
        nm = t.get('m_Name')
        if nm in rename:
            t['m_Name'] = rename[nm]
            if o.type.name == 'GameObject':
                root = pmap[pid]
        walk_pptr(t, lambda p: p.update(
            {'m_FileID': 0, 'm_PathID': pmap.get(p['m_PathID'], p['m_PathID'])}
            if p['m_FileID'] == 0 else
            {'m_FileID': my_ext.index(src_ext[p['m_FileID'] - 1]) + 1}))
        objs.append((pmap[pid], int(o.class_id), bytes(o.save_typetree(t))))
    if root is None:
        raise SystemExit('%s 에서 %s 를 못 찾았습니다'
                         % (os.path.basename(path), list(rename)))
    return objs, root, len(pids)


def build_assets(say):
    from mktaegeuk import write_serialized
    from sfparse import parse

    v, uv, tri, skin, bindpose = read_troy()
    say('메시: 정점 %d · 삼각형 %d · 뼈 %d' % (len(v), len(tri) // 3, len(bindpose)))

    # 외부 파일 목록은 **빌려 온 프리팹 것을 그대로** 쓴다. 스크립트가 든
    # MonoBehaviour 는 타입트리가 없어 그 안의 참조 번호를 우리가 다 알
    # 수 없다. 번호를 그대로 두면 안 건드린 참조도 계속 맞는다.
    # 셰이더 파일만 뒤에 붙인다(재질이 가리킨다).
    my_ext = [os.path.basename(e)
              for e in parse(os.path.join(XD, D_PREFAB))['externals']]
    if SHADER not in my_ext:
        my_ext.append(SHADER)
    shader_idx = my_ext.index(SHADER) + 1
    # 효과 오브젝트가 쓰는 재질·메시도 목록에 더한다.
    for e in parse(os.path.join(XD, D_EFFECT))['externals']:
        e = os.path.basename(e)
        if e not in my_ext:
            my_ext.append(e)

    P = {'mesh': 1, 'tex': 2, 'locktex': 3, 'lock': 4, 'land': 5}
    objs = []
    blob, cid = build_mesh(v, uv, tri, skin, bindpose)
    objs.append((P['mesh'], cid, blob))
    blob, cid = build_texture(troy_image(KR_TEX), '%s_Tex' % NAME)
    objs.append((P['tex'], cid, blob))
    say('텍스처: 256x256 DXT1 (%d바이트)' % len(blob))

    # 잠금 그림도 초기판에 트로이 것이 남아 있다. 자동차 샵에서 아직 못 산
    # 차를 그릴 때 쓰는 재질이다.
    blob, cid = build_texture(troy_image(KR_LOCKTEX), '%s_Lock_Tex' % NAME)
    objs.append((P['locktex'], cid, blob))
    blob, cid = build_material('%s_Lock' % NAME, P['locktex'], shader_idx,
                               os.path.join(XD, D_LOCKMAT))
    objs.append((P['lock'], cid, blob))
    say('잠금 재질: %s_Lock (초기판 그림)' % NAME)

    # 착지 소리는 프리팹 스크립트가 들고 있다. 번들 안으로 들여와야
    # 합칠 때 참조가 어긋나지 않는다.
    blob, cid = copy_object(os.path.join(XD, D_LAND), 'AudioClip')
    objs.append((P['land'], cid, blob))

    mats = {}
    pid = 10
    for nm in mat_names():
        blob, cid = build_material(nm, P['tex'], shader_idx)
        objs.append((pid, cid, blob))
        mats[nm.lower()] = pid
        pid += 1
    say('재질 %d개 (%s …)' % (len(mats), ' · '.join(sorted(mats)[:3])))

    # 효과 오브젝트. **없으면 주행이 통째로 멈춘다.**
    # `EffectManager.Setting` 이 `Instantiate(Load("Car/Troy/Troy_Effect"))`
    # 를 부르는데, 유니티의 `Instantiate(null)` 은 예외를 던진다. 그 예외가
    # 주행 준비 사슬을 끊어 맵이 한 걸음도 안 나간다(실기에서 겪었다).
    # 미등 두 개와 충돌 상자뿐인 작은 오브젝트라 피닉스 것을 그대로 베낀다.
    got, fx_root, n = clone_file(os.path.join(XD, D_EFFECT), 50,
                                 {'Phoenix_Effect': '%s_Effect' % NAME}, my_ext)
    objs += got
    say('효과: %s_Effect (오브젝트 %d개)' % (NAME, n))

    # 프리팹은 등급마다 하나씩. 번들에서 찾는 열쇠가 오브젝트 이름이라
    # 이름 하나에 오브젝트 하나가 있어야 한다.
    base = 100
    roots, mbptr = {}, []
    ladder = dict((c['CarClassType'], c) for c in entry()['CarClassDataArray'])
    for k in KLASSES:
        for low in ('', '_Low'):
            label = k + low
            mat = mats.get(('%s_%s' % (NAME, label)).lower())
            here = dict(P, mat=mat)
            got, root, mb, n = clone_prefab(base, k, low, here.get, ladder[k])
            objs += got
            roots['player_%s_%s' % (NAME.lower(), label.lower())] = root
            mbptr += mb
            base += n + 10
    say('프리팹 %d벌 (%s)' % (len(roots), ' · '.join(sorted(roots))))

    size = write_serialized(OUT, parse(os.path.join(XD, D_PREFAB)),
                            objs, my_ext)
    say('%s — 오브젝트 %d개 · %.1fKB'
        % (os.path.basename(OUT), len(objs), size / 1024.0))
    return roots, mats, mbptr, P['lock'], fx_root


def spec_line(roots, mats, mbptr, lock_pid=None, fx_pid=None):
    low = NAME.lower()
    first = 'player_%s_c' % low
    parts = ['%s:car/%s/%s:%d:0:keepscript'
             % (os.path.basename(OUT), low, first, roots[first])]
    for nm, pid in sorted(roots.items()):
        if nm != first:
            parts.append('also=car/%s/%s@%d' % (low, nm, pid))
    for nm, pid in sorted(mats.items()):
        parts.append('also=car/%s/materials/%s@%d' % (low, nm, pid))
    if lock_pid:
        # 잠긴 차를 그릴 때 쓰는 재질. 원판은 차마다 이름이 갈리므로
        # (`materials/lock` · `materials/aveo_lock`) 둘 다 걸어 둔다.
        parts.append('also=car/%s/materials/%s_lock@%d' % (low, low, lock_pid))
        parts.append('also=car/%s/materials/lock@%d' % (low, lock_pid))
    if fx_pid:
        parts.append('also=car/%s/%s_effect@%d' % (low, low, fx_pid))
    for pid, off in mbptr:
        parts.append('mbptr=%d@%d' % (pid, off))
    return ':'.join(parts)


# ------------------------------------------------------------------ 등록
def _textasset(raw, meta, pid=1):
    rec = [o for o in meta['objects'] if o['path_id'] == pid][0]
    st = meta['data_offset'] + rec['start']
    b = bytes(raw[st:st + rec['size']])
    n = struct.unpack_from('<i', b, 0)[0]
    off = 4 + n
    off += (-off) % 4
    return st, off, struct.unpack_from('<i', b, off)[0]


def entry():
    arr = []
    for i, k in enumerate(KLASSES):
        d = {'CarClassType': k}
        for f, b in BASE.items():
            lo, hi = STEP[f]
            val = b + lo * min(i, 3) + (hi if i == 4 else 0)
            d[f] = round(val, 1) if isinstance(b, float) else int(val)
        arr.append(d)
    return {
        'CarName': NAME, 'CarIndex': CAR_INDEX, 'StartCarClassType': KLASSES[0],
        'CostGold': 0, 'UnlockTrophy': 15, 'Preminum': True, 'NewCar': True,
        'EventCar': False, 'RivalCar': False, 'IsRobot': False,
        'HasMission': False, 'MissionType': 'none', 'IsGotyaEvent': False,
        'GotyaCost': 15, 'GotyaRetryCost': 10, 'CarIconAtlas': ICON_ATLAS,
        'CarClassDataArray': arr,
    }


def register_cardb(say):
    from sfparse import parse
    raw = bytearray(io.open(CARDB, 'rb').read())
    meta = parse(CARDB)
    st, off, tlen = _textasset(raw, meta)
    tst = st + off + 4
    text = raw[tst:tst + tlen].decode('utf-8')
    arr = json.loads(text)['CarDataBase']['CarInfoDB']['CarDataArray']
    if any(c['CarName'] == NAME for c in arr):
        say('CarDataBase 에 이미 있습니다')
        return
    if any(c['CarIndex'] == CAR_INDEX for c in arr):
        raise SystemExit('CarIndex %d 가 이미 쓰이고 있습니다' % CAR_INDEX)
    piece = json.dumps(entry(), ensure_ascii=False, separators=(',', ':')) + ','
    gap = ' ' * (len(piece) + 40)
    i = text.find(gap)
    if i < 0:
        raise SystemExit('CarDataBase 에 빈 자리가 모자랍니다'
                         ' (%d바이트 필요). trimcars.py 를 먼저 돌리세요.'
                         % len(piece))
    out = text[:i] + piece + text[i + len(piece):]
    assert len(out) == len(text)
    json.loads(out)
    raw[tst:tst + tlen] = out.encode('utf-8')
    io.open(CARDB, 'wb').write(bytes(raw))
    say('CarDataBase: %s (CarIndex %d · 서버 carNo %d · %d대)'
        % (NAME, CAR_INDEX, CAR_INDEX + 1, len(arr) + 1))


def register_label(say):
    from sfparse import parse
    from mktaegeuk import write_serialized
    raw = bytearray(io.open(TEXTDB, 'rb').read())
    meta = parse(TEXTDB)
    st, off, tlen = _textasset(raw, meta)
    tst = st + off + 4
    text = raw[tst:tst + tlen].decode('utf-8')
    key = 'CarName_%s' % NAME
    if key + ' ' in text:
        say('이름표가 이미 있습니다')
        return
    i = text.index('CarName_AVEO')
    nl = '\r\n' if '\r\n' in text else '\n'
    text = text[:i] + ('%s = %s%s' % (key, LABEL, nl)) + text[i:]
    sf = _sf(TEXTDB)
    o = sf.objects[1]
    t = o.read_typetree()
    t['m_Script'] = text
    write_serialized(TEXTDB, meta, [(1, 49, bytes(o.save_typetree(t)))],
                     [os.path.basename(e) for e in meta['externals']])
    say('이름표: %s = %s' % (key, LABEL))


def register_tables(say):
    cars = []
    if os.path.exists(NEWCARS):
        cars = json.load(io.open(NEWCARS, encoding='utf-8'))
    cars = [c for c in cars if c['name'] != NAME]
    cars.append({'carNo': CAR_INDEX + 1, 'name': NAME, 'label': LABEL,
                 'class': KLASSES[0], 'gold': 0, 'trophy': 15})
    cars.sort(key=lambda c: c['carNo'])
    io.open(NEWCARS, 'w', encoding='utf-8').write(
        json.dumps(cars, ensure_ascii=False, indent=1))
    say('newcars.json (새 차 %d대)' % len(cars))
    patch_server(say)


def patch_server(say, undo=False):
    """사설 서버 표에 차를 얹는다. 없는 것만 더하고 있으면 손대지 않는다.

    표는 셋이다 — `CAR_CLASS`(시작 등급) · `CAR_COST`(값) · `SHOP_CARS`
    (자동차 샵 매물). 셋 다 한 줄짜리 리터럴이라 닫는 괄호 앞에 끼워
    넣으면 된다. `mkskel.py` 가 이 표를 떠서 `ChaLocalData.cs` 로 굽기
    때문에, 로컬 전용 APK 도 여기만 고치면 따라온다."""
    no = CAR_INDEX + 1
    s = io.open(SERVER, encoding='utf-8').read()
    orig = s
    # (변수, 넣을 조각, 이미 있는지 보는 표시)
    todo = [('CAR_CLASS', '%d: "%s"' % (no, KLASSES[0]), '%d:' % no),
            ('CAR_COST', '%d: (0, 15)' % no, '%d:' % no),
            ('SHOP_CARS', '%d' % no, '%d' % no)]
    for var, piece, probe in todo:
        i = s.index('\n%s = {' % var)
        j = s.index('}', i)
        block = s[i:j]
        has = any(x.strip().startswith(probe)
                  for x in block[block.index('{') + 1:].split(','))
        if undo and has:
            s = s[:i] + block.replace(', ' + piece, '') + s[j:]
        elif not undo and not has:
            s = s[:j] + ', ' + piece + s[j:]
    if s == orig:
        say('서버 표는 이미 맞습니다')
        return
    io.open(SERVER, 'w', encoding='utf-8', newline='').write(s)
    say('서버 표: carNo %d %s' % (no, '뺐습니다' if undo else '얹었습니다'))


def add_spec(line, say):
    lines = []
    if os.path.exists(SPEC):
        lines = [x for x in io.open(SPEC, encoding='utf-8').read().splitlines()
                 if x.strip()]
    tag = 'car/%s/' % NAME.lower()
    lines = [x for x in lines if tag not in x]
    lines.append(line)
    io.open(SPEC, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    say('packspec.txt (자산 %d개)' % len(lines))


# ------------------------------------------------------------------ 빼기
def unregister_cardb(say):
    from sfparse import parse
    raw = bytearray(io.open(CARDB, 'rb').read())
    meta = parse(CARDB)
    st, off, tlen = _textasset(raw, meta)
    tst = st + off + 4
    text = raw[tst:tst + tlen].decode('utf-8')
    arr = json.loads(text)['CarDataBase']['CarInfoDB']['CarDataArray']
    hit = [c for c in arr if c['CarName'] == NAME]
    if not hit:
        say('CarDataBase 에 없습니다')
        return
    piece = json.dumps(hit[0], ensure_ascii=False, separators=(',', ':')) + ','
    i = text.find(piece)
    if i < 0:
        raise SystemExit('CarDataBase 에서 자리를 못 찾았습니다')
    out = text[:i] + ' ' * len(piece) + text[i + len(piece):]
    json.loads(out)
    raw[tst:tst + tlen] = out.encode('utf-8')
    io.open(CARDB, 'wb').write(bytes(raw))
    say('CarDataBase 에서 뺐습니다 (자리는 공백으로)')


def unregister_label(say):
    from sfparse import parse
    from mktaegeuk import write_serialized
    raw = bytearray(io.open(TEXTDB, 'rb').read())
    meta = parse(TEXTDB)
    st, off, tlen = _textasset(raw, meta)
    tst = st + off + 4
    text = raw[tst:tst + tlen].decode('utf-8')
    key = 'CarName_%s ' % NAME
    lines = text.splitlines(True)
    keep = [l for l in lines if not l.startswith(key)]
    if len(keep) == len(lines):
        say('이름표가 없습니다')
        return
    sf = _sf(TEXTDB)
    o = sf.objects[1]
    t = o.read_typetree()
    t['m_Script'] = ''.join(keep)
    write_serialized(TEXTDB, meta, [(1, 49, bytes(o.save_typetree(t)))],
                     [os.path.basename(e) for e in meta['externals']])
    say('이름표를 지웠습니다')


def remove(say=print):
    unregister_cardb(say)
    unregister_label(say)
    if os.path.exists(SPEC):
        lines = [x for x in io.open(SPEC, encoding='utf-8').read().splitlines()
                 if x.strip()]
        keep = [x for x in lines if 'car/%s/' % NAME.lower() not in x]
        if len(keep) != len(lines):
            io.open(SPEC, 'w', encoding='utf-8').write('\n'.join(keep) + '\n')
    for p in (PACKDAT, BUNDLE):
        b = os.path.join(BAKDIR, os.path.basename(p))
        if os.path.exists(b):
            shutil.copy2(b, p)
            say('%s 를 되돌렸습니다' % os.path.basename(p))
    if os.path.exists(NEWCARS):
        cars = [c for c in json.load(io.open(NEWCARS, encoding='utf-8'))
                if c['name'] != NAME]
        if cars:
            io.open(NEWCARS, 'w', encoding='utf-8').write(
                json.dumps(cars, ensure_ascii=False, indent=1))
        else:
            os.remove(NEWCARS)
        say('newcars.json 정리')
    patch_server(say, undo=True)
    if os.path.exists(OUT):
        os.remove(OUT)
        say('%s 를 지웠습니다' % os.path.basename(OUT))
    say('')
    say('트로이를 뺐습니다. APK 를 다시 만드세요.')


# ------------------------------------------------------------------ 보기
def scan(say=print):
    ok = True
    for tag, p in (('초기판 메시', os.path.join(KR8, KR_MODEL)),
                   ('초기판 텍스처', os.path.join(KR8, KR_TEX)),
                   ('그릇 메시', os.path.join(XD, D_MESH)),
                   ('그릇 텍스처', os.path.join(XD, D_TEX)),
                   ('그릇 재질', os.path.join(XD, D_MAT)),
                   ('그릇 프리팹', os.path.join(XD, D_PREFAB))):
        have = os.path.exists(p)
        ok = ok and have
        say('  %-12s %s  %s' % (tag, '있음' if have else '없음',
                                os.path.basename(p)))
    if not ok:
        say('\n초기판 트리가 없으면 8.apk 의 assets/bin/Data 를 _scratch/kr8 에 푸세요.')
        return 1
    v, uv, tri, skin, _bp = read_troy()
    say('\n  트로이 메시  정점 %d · 삼각형 %d' % (len(v), len(tri) // 3))
    import collections
    c = collections.Counter(s['boneIndex[0]'] for s in skin)
    say('  뼈별 정점    %s' % ' · '.join('%d번 %d개' % (k, n)
                                     for k, n in sorted(c.items())))
    say('  만들 재질    %d개' % len(mat_names()))
    say('  만들 프리팹  %d벌 (%s)'
        % (len(KLASSES) * 2, ' · '.join('Player_%s_%s' % (NAME, k)
                                        for k in KLASSES)))
    say('  차 표        CarIndex %d · 서버 carNo %d · %s급 · 트로피 15'
        % (CAR_INDEX, CAR_INDEX + 1, KLASSES[0]))
    for d in entry()['CarClassDataArray']:
        say('    %-2s 최고속 %3d · 무게 %4d · 가속 %2d · 연비 %.1f'
            % (d['CarClassType'], d['MaxSpeed'], d['CarWeight'],
               d['SpeedPerSecond'], d['OilMileage']))
    return 0


def bundle_baseline(say):
    """번들을 손대기 전 모습으로 되돌린다 (없으면 지금 것을 남겨 둔다).

    `packadd` 는 있는 번들에 **덧붙이는** 도구라 두 번 돌리면 두 번 붙는다.
    붙이기 전에 늘 원래 자리로 돌려놓아 몇 번을 돌려도 같게 만든다.
    번들을 처음부터 다시 굽는 길은 없다 — `packadd` 의 설명을 보라."""
    os.makedirs(BAKDIR, exist_ok=True)
    fresh = True
    for p in (PACKDAT, BUNDLE):
        b = os.path.join(BAKDIR, os.path.basename(p))
        if os.path.exists(b):
            shutil.copy2(b, p)
            fresh = False
        elif os.path.exists(p):
            shutil.copy2(p, b)
    say('번들 원본을 %s' % ('backup/bundle 에 남겼습니다' if fresh
                        else 'backup/bundle 에서 되살렸습니다'))


def add(say=print):
    roots, mats, mbptr, lock, fx = build_assets(say)
    line = spec_line(roots, mats, mbptr, lock, fx)
    add_spec(line, say)
    bundle_baseline(say)
    import packadd
    say('번들에 얹습니다…')
    packadd.add(OUT, [line.split(':', 1)[1]], say)
    packadd.wrap(say)
    register_cardb(say)
    register_label(say)
    register_tables(say)
    say('')
    say('트로이(carNo %d)를 넣었습니다. 자동차 샵에 트로피 15로 나옵니다.'
        % (CAR_INDEX + 1))
    say('이제 APK 를 다시 만드세요.')
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scan', action='store_true')
    ap.add_argument('--remove', action='store_true')
    a = ap.parse_args()
    if a.scan:
        return scan()
    if a.remove:
        remove()
        return 0
    return add()


if __name__ == '__main__':
    sys.exit(main())
