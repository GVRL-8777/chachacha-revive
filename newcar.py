# -*- coding: utf-8 -*-
"""내 모델을 **새 차로 추가합니다**. 기존 차를 덮어쓰지 않습니다.

`chatool import` 는 기존 차의 메시를 갈아 끼우는 도구라 차 대수가 늘지
않습니다. 이쪽은 차 한 대를 통째로 새로 만들어 넣습니다.

만드는 것
  1. `<이름>.assets`  — 메시(압축) · 텍스처(DXT1) · 재질 · 프리팹 한 벌
     프리팹은 기존 S급 차에서 통째로 베낍니다. 본·애니메이션·스크립트가
     그대로 붙어 있어야 차고에서도 주행에서도 제대로 섭니다.
  2. CarDataBase 에 항목 한 줄 (빈 자리에 써 넣어 파일 길이를 지킵니다)
  3. 이름표 `CarName_<이름>`
  4. `packspec.txt` 에 한 줄 → 번들(pack.unity3d) 다시 굽기
  5. `newcars.json` — 서버와 세이브가 읽는 표

  python newcar.py <영문이름> --obj my.obj --png my.png
                   [--label 표시이름] [--class S] [--trophy 150] [--gold 0]
                   [--winding keep|flip|auto] [--no-fit]

넣은 뒤에는 `chatool build` 로 APK 를 다시 만들고, 서버판이면
`carfix.py` 가 다시 돌아야 서버 표에도 반영됩니다(relaunch2.sh 가 합니다).
"""
import argparse
import io
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import chaassets as A
from sfparse import parse
import mktaegeuk
from mktaegeuk import write_serialized, walk_pptr, load

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.join(HERE, 'x77')
D = os.path.join(TREE, 'assets', 'bin', 'Data')
# mktaegeuk.load 는 자기 모듈의 상대경로를 씁니다. 어느 폴더에서 부르든
# 같게 돌도록 절대경로로 바꿔 둡니다.
mktaegeuk.D = D

DONOR_PREFAB = '6af067f63f19ae84eb93fdee6c07f0e1'   # player_lamborghini_s
DONOR_MODEL = 'e9929419738592541aade46bf0cf3a4e'    # Lamborghini 모델(메시+본)
DONOR_MAT = 'd7dae3647564ca94798f0b5c2bba2a6f'
DONOR_TEX = 'fcbdea69c77d91f45ba387ed1ef3671f'
OLD = 'Lamborghini'
# 프리팹 안 스크립트가 가리키는 '차 재질' 파일들
MAT_FILES = {'d7dae3647564ca94798f0b5c2bba2a6f',
             '471d72379d3479c44968ed0acb52efad'}

CARDB = os.path.join('assets', 'bin', 'Data',
                     'ade64ecd8944d9640bb1438deb4f6fe3')
TEXTDB = os.path.join('assets', 'bin', 'Data',
                      '50295c6b20ff907439e2ef8aa05f9ea7')
NEWCARS = os.path.join(HERE, 'newcars.json')
SPEC = os.path.join(HERE, 'packspec.txt')

# 등급별 기본 성능. 원본 S급 차들의 값을 그대로 씁니다.
PERF = {
    'C': dict(MaxSpeed=250, CarWeight=1100, SpeedPerSecond=52,
              NextStepSpeed=120, NextSpeedPerSecond=6.0, OilMileage=11),
    'B': dict(MaxSpeed=290, CarWeight=1250, SpeedPerSecond=58,
              NextStepSpeed=138, NextSpeedPerSecond=6.6, OilMileage=12),
    'A': dict(MaxSpeed=330, CarWeight=1450, SpeedPerSecond=65,
              NextStepSpeed=156, NextSpeedPerSecond=7.3, OilMileage=13),
    'S': dict(MaxSpeed=388, CarWeight=1650, SpeedPerSecond=74,
              NextStepSpeed=179, NextSpeedPerSecond=8.2, OilMileage=15),
}


# ------------------------------------------------------------------ 자산 만들기
def build_assets(name, v, uv, tri, png, out_path, say):
    from PIL import Image
    from UnityPy.enums import TextureFormat
    from UnityPy.export import Texture2DConverter as T2C

    model, model_meta, _ = load(DONOR_MODEL)
    prefab, prefab_meta, prefab_raw = load(DONOR_PREFAB)
    matf, mat_meta, _ = load(DONOR_MAT)

    my_ext = [os.path.basename(e) for e in prefab_meta['externals']]
    shader_ext = [os.path.basename(e) for e in mat_meta['externals']][0]
    if shader_ext not in my_ext:
        my_ext.append(shader_ext)
    idx = dict((n, i + 1) for i, n in enumerate(my_ext))

    MESH_PID, TEX_PID, MAT_PID = 1, 2, 3
    objs = []

    # ---- 메시 ---------------------------------------------------------
    mo = model.objects[1]
    mtree = A.pack_mesh(mo.read_typetree(), v, uv, tri, name)
    objs.append((MESH_PID, 43, bytes(mo.save_typetree(mtree))))
    say('메시: 정점 %d · 삼각형 %d' % (len(v), len(tri) // 3))

    # ---- 텍스처 -------------------------------------------------------
    texf, _, _ = load(DONOR_TEX)
    tex_obj = [o for o in texf.objects.values()
               if o.type.name == 'Texture2D'][0]
    ttree = dict(tex_obj.read_typetree())
    im = Image.open(png).convert('RGB')
    side = ttree['m_Width']
    if (im.width, im.height) != (side, ttree['m_Height']):
        im = im.resize((side, ttree['m_Height']), Image.LANCZOS)
    blob, fmt = T2C.image_to_texture2d(im, TextureFormat.DXT1)
    ttree.update({'m_Name': name, 'm_TextureFormat': int(fmt),
                  'm_MipMap': False, 'm_MipCount': 1,
                  'm_CompleteImageSize': len(blob), 'image data': bytes(blob)})
    if 'm_ImageCount' in ttree:
        ttree['m_ImageCount'] = 1
    objs.append((TEX_PID, 28, bytes(tex_obj.save_typetree(ttree))))
    say('텍스처: %dx%d DXT1' % (side, ttree['m_Height']))

    # ---- 재질 ---------------------------------------------------------
    mo2 = matf.objects[1]
    mt = dict(mo2.read_typetree())
    mt['m_Name'] = name
    mt['m_Shader'] = {'m_FileID': idx[shader_ext], 'm_PathID': 1}
    for _k, val in mt['m_SavedProperties']['m_TexEnvs']:
        val['m_Texture'] = {'m_FileID': 0, 'm_PathID': TEX_PID}
    objs.append((MAT_PID, 21, bytes(mo2.save_typetree(mt))))

    # ---- 프리팹 통째로 베끼기 -----------------------------------------
    src_ext = [os.path.basename(e) for e in prefab_meta['externals']]
    pmap = dict((pid, 10 + i) for i, pid in enumerate(sorted(prefab.objects)))
    recs = dict((o['path_id'], o) for o in prefab_meta['objects'])

    def fix(p):
        f, q = p['m_FileID'], p['m_PathID']
        if f == 0:
            p['m_PathID'] = pmap.get(q, q)
        else:
            p['m_FileID'] = idx.get(src_ext[f - 1], 0)

    mbptr = []
    for pid in sorted(prefab.objects):
        o = prefab.objects[pid]
        cid = int(o.class_id)
        if o.type.name == 'MonoBehaviour':
            # 타입트리가 없습니다. 원시 바이트로 옮기고 PPtr 만 고칩니다.
            r = recs[pid]
            st = prefab_meta['data_offset'] + r['start']
            b = bytearray(prefab_raw[st:st + r['size']])
            gf, gp = struct.unpack_from('<ii', b, 0)
            if gf == 0:
                struct.pack_into('<ii', b, 0, 0, pmap.get(gp, gp))
            sf_, sp_ = struct.unpack_from('<ii', b, 12)
            if sf_:
                struct.pack_into('<ii', b, 12, idx.get(src_ext[sf_ - 1], 0), sp_)
            # ChangeTextureMaterial 이 Start() 에서 renderer.material 을
            # 자기가 든 Material[] 로 덮어씁니다. 그 배열도 돌려놓습니다.
            for j in range(20, len(b) - 7, 4):
                f2, p2 = struct.unpack_from('<ii', b, j)
                if 0 < f2 <= len(src_ext) and p2 == 1 and \
                        src_ext[f2 - 1] in MAT_FILES:
                    struct.pack_into('<ii', b, j, 0, MAT_PID)
                    mbptr.append((pmap[pid], j))
            objs.append((pmap[pid], cid, bytes(b)))
            continue

        t = o.read_typetree()
        if o.type.name == 'GameObject' and t['m_Name'].startswith('Player'):
            # 루트 이름만 바꿉니다. 안쪽 이름을 건드리면 애니메이션 경로가
            # 어긋납니다.
            t['m_Name'] = t['m_Name'].replace(OLD, name)
        walk_pptr(t, fix)
        if o.type.name == 'SkinnedMeshRenderer':
            t['m_Mesh'] = {'m_FileID': 0, 'm_PathID': MESH_PID}
            t['m_Materials'] = [{'m_FileID': 0, 'm_PathID': MAT_PID}]
        objs.append((pmap[pid], cid, bytes(o.save_typetree(t))))

    root = [pid for pid in sorted(prefab.objects)
            if prefab.objects[pid].type.name == 'GameObject'
            and prefab.objects[pid].read_typetree()['m_Name'].startswith('Player')]
    root_pid = pmap[root[0]] if root else pmap[sorted(prefab.objects)[0]]
    size = write_serialized(out_path, model_meta, objs, my_ext)
    say('%s (%d바이트) · 프리팹 %d개 복제'
        % (os.path.basename(out_path), size, len(prefab.objects)))
    return root_pid, MAT_PID, mbptr


def spec_line(name, fn, root_pid, mat_pid, mbptr, klass):
    low = name.lower()
    parts = ['%s:car/%s/player_%s_%s:%d:0:keepscript'
             % (fn, low, low, klass.lower(), root_pid)]
    for nm, pid in (('materials/%s' % low, mat_pid),
                    ('materials/%s_low' % low, mat_pid),
                    ('%s' % low, root_pid),
                    ('%s_low' % low, root_pid),
                    ('player_%s_%s_low' % (low, klass.lower()), root_pid)):
        parts.append('also=car/%s/%s@%d' % (low, nm, pid))
    for pid, off in mbptr:
        parts.append('mbptr=%d@%d' % (pid, off))
    return ':'.join(parts)


# ------------------------------------------------------------------ 등록
def _textasset(raw, meta, pid=1):
    rec = [o for o in meta['objects'] if o['path_id'] == pid][0]
    st = meta['data_offset'] + rec['start']
    blob = bytes(raw[st:st + rec['size']])
    n = struct.unpack_from('<i', blob, 0)[0]
    off = 4 + n
    off += (-off) % 4
    tlen = struct.unpack_from('<i', blob, off)[0]
    return st, off, tlen


def register_cardb(name, klass, gold, trophy, say):
    p = os.path.join(TREE, CARDB)
    raw = bytearray(io.open(p, 'rb').read())
    meta = parse(p)
    st, off, tlen = _textasset(raw, meta)
    tst = st + off + 4
    text = raw[tst:tst + tlen].decode('utf-8')
    db = json.loads(text)
    arr = db['CarDataBase']['CarInfoDB']['CarDataArray']
    for c in arr:
        if c['CarName'] == name:
            say('이미 등록돼 있습니다 (CarIndex %d)' % c['CarIndex'])
            return c['CarIndex']
    used = set(c['CarIndex'] for c in arr)
    car_index = next(i for i in range(0, 64) if i not in used)

    entry = {
        'CarName': name, 'CarIndex': car_index, 'StartCarClassType': klass,
        'CostGold': gold, 'UnlockTrophy': trophy,
        'Preminum': trophy > 0, 'NewCar': True, 'EventCar': False,
        'RivalCar': False, 'IsRobot': False, 'HasMission': False,
        'MissionType': 'none', 'IsGotyaEvent': False,
        'GotyaCost': 15, 'GotyaRetryCost': 10,
        'CarIconAtlas': 'Atlas_CarIcon',
        'CarClassDataArray': [dict(CarClassType=klass, **PERF[klass])],
    }
    piece = json.dumps(entry, ensure_ascii=False, separators=(',', ':')) + ','
    gap = ' ' * (len(piece) + 40)
    i = text.find(gap)
    if i < 0:
        raise SystemExit('CarDataBase 에 빈 자리가 모자랍니다.'
                         ' trimcars.py 를 먼저 돌려야 합니다.')
    out = text[:i] + piece + text[i + len(piece):]
    assert len(out) == len(text)
    json.loads(out)
    raw[tst:tst + tlen] = out.encode('utf-8')
    io.open(p, 'wb').write(bytes(raw))
    say('CarDataBase 등록: %s (CarIndex %d, 서버 carNo %d)'
        % (name, car_index, car_index + 1))
    return car_index


def register_label(name, label, say):
    p = os.path.join(TREE, TEXTDB)
    raw = bytearray(io.open(p, 'rb').read())
    meta = parse(p)
    st, off, tlen = _textasset(raw, meta)
    tst = st + off + 4
    text = raw[tst:tst + tlen].decode('utf-8')
    key = 'CarName_%s' % name
    if key in text:
        say('이름표가 이미 있습니다')
        return
    i = text.index('CarName_AVEO')
    nl = '\r\n' if '\r\n' in text else '\n'
    text = text[:i] + ('%s = %s%s' % (key, label, nl)) + text[i:]
    from UnityPy.streams import EndianBinaryReader
    from UnityPy.files.SerializedFile import SerializedFile
    sf = SerializedFile(EndianBinaryReader(bytes(raw)), None)
    o = sf.objects[1]
    tree = o.read_typetree()
    tree['m_Script'] = text
    write_serialized(p, meta, [(1, 49, bytes(o.save_typetree(tree)))],
                     [os.path.basename(e) for e in meta['externals']])
    say('이름표: %s = %s' % (key, label))


def register_tables(car_no, name, label, klass, gold, trophy, say):
    cars = []
    if os.path.exists(NEWCARS):
        cars = json.load(io.open(NEWCARS, encoding='utf-8'))
    cars = [c for c in cars if c['name'] != name]
    cars.append({'carNo': car_no, 'name': name, 'label': label,
                 'class': klass, 'gold': gold, 'trophy': trophy})
    cars.sort(key=lambda c: c['carNo'])
    io.open(NEWCARS, 'w', encoding='utf-8').write(
        json.dumps(cars, ensure_ascii=False, indent=1))
    say('newcars.json 갱신 (새 차 %d대)' % len(cars))


def add_spec(line, name, say):
    lines = []
    if os.path.exists(SPEC):
        lines = [x for x in io.open(SPEC, encoding='utf-8').read().splitlines()
                 if x.strip()]
    tag = 'car/%s/' % name.lower()
    lines = [x for x in lines if tag not in x]
    lines.append(line)
    io.open(SPEC, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    say('packspec.txt 갱신 (자산 %d개)' % len(lines))


# ------------------------------------------------------------------ 빼기
def unregister_cardb(name, say):
    """CarDataBase 에서 항목을 빼고 **그 자리를 다시 공백으로** 돌려놓습니다.

    넣을 때 공백 자리에 같은 길이로 밀어 넣었으니, 뺄 때도 같은 길이의
    공백으로 되돌려야 파일 길이가 유지됩니다."""
    p = os.path.join(TREE, CARDB)
    raw = bytearray(io.open(p, 'rb').read())
    meta = parse(p)
    st, off, tlen = _textasset(raw, meta)
    tst = st + off + 4
    text = raw[tst:tst + tlen].decode('utf-8')
    db = json.loads(text)
    arr = db['CarDataBase']['CarInfoDB']['CarDataArray']
    hit = [c for c in arr if c['CarName'] == name]
    if not hit:
        say('CarDataBase 에 %s 가 없습니다' % name)
        return None
    entry = hit[0]
    piece = json.dumps(entry, ensure_ascii=False, separators=(',', ':')) + ','
    i = text.find(piece)
    if i < 0:
        raise SystemExit('CarDataBase 에서 항목 자리를 못 찾았습니다.'
                         ' 손으로 고친 적이 있으면 이 방법으로는 못 뺍니다.')
    out = text[:i] + ' ' * len(piece) + text[i + len(piece):]
    assert len(out) == len(text)
    json.loads(out)
    raw[tst:tst + tlen] = out.encode('utf-8')
    io.open(p, 'wb').write(bytes(raw))
    say('CarDataBase 에서 뺐습니다 (%s, CarIndex %d — 자리는 공백으로)'
        % (name, entry['CarIndex']))
    return entry['CarIndex']


def unregister_label(name, say):
    p = os.path.join(TREE, TEXTDB)
    raw = bytearray(io.open(p, 'rb').read())
    meta = parse(p)
    st, off, tlen = _textasset(raw, meta)
    tst = st + off + 4
    text = raw[tst:tst + tlen].decode('utf-8')
    key = 'CarName_%s' % name
    lines = text.splitlines(True)
    keep = [l for l in lines if not l.startswith(key + ' ')]
    if len(keep) == len(lines):
        say('이름표가 없습니다')
        return
    text = ''.join(keep)
    from UnityPy.streams import EndianBinaryReader
    from UnityPy.files.SerializedFile import SerializedFile
    sf = SerializedFile(EndianBinaryReader(bytes(raw)), None)
    o = sf.objects[1]
    tree = o.read_typetree()
    tree['m_Script'] = text
    write_serialized(p, meta, [(1, 49, bytes(o.save_typetree(tree)))],
                     [os.path.basename(e) for e in meta['externals']])
    say('이름표를 지웠습니다: %s' % key)


def remove(name, say=print):
    """새로 넣었던 차를 도로 뺍니다."""
    name = name.strip()
    unregister_cardb(name, say)
    unregister_label(name, say)

    # packspec 에서 그 차 줄을 빼고 번들을 다시 굽습니다
    tag = 'car/%s/' % name.lower()
    if os.path.exists(SPEC):
        lines = [x for x in io.open(SPEC, encoding='utf-8').read().splitlines()
                 if x.strip()]
        keep = [x for x in lines if tag not in x]
        if len(keep) != len(lines):
            io.open(SPEC, 'w', encoding='utf-8').write(
                '\n'.join(keep) + '\n')
            say('packspec 에서 %d줄을 뺐습니다 (남은 자산 %d개)'
                % (len(lines) - len(keep), len(keep)))
            import mkpack
            say('번들을 다시 굽습니다…')
            say('pack.unity3d %.1f MB' % (mkpack.build(quiet=True) / 1048576.0))

    # 표에서 빼기
    if os.path.exists(NEWCARS):
        cars = json.load(io.open(NEWCARS, encoding='utf-8'))
        left = [c for c in cars if c['name'] != name]
        if left:
            io.open(NEWCARS, 'w', encoding='utf-8').write(
                json.dumps(left, ensure_ascii=False, indent=1))
        else:
            os.remove(NEWCARS)
        say('newcars.json: 새 차 %d대 남았습니다' % len(left))

    f = os.path.join(HERE, '%s.assets' % name.lower())
    if os.path.exists(f):
        os.remove(f)
        say('%s 를 지웠습니다' % os.path.basename(f))
    say('')
    say('"%s" 를 뺐습니다. 서버 표를 다시 만들고 APK 를 다시 만드세요.' % name)


# ------------------------------------------------------------------ 본체
def add(name, obj_path, png_path, label=None, klass='S', gold=0, trophy=150,
        winding='keep', fit=True, say=print):
    name = name.strip()
    if not name or not name[0].isalpha():
        raise SystemExit('이름은 영문으로 시작해야 합니다')
    label = label or name
    klass = klass.upper()
    if klass not in PERF:
        raise SystemExit('등급은 C·B·A·S 중 하나여야 합니다')

    v, uv, tri = A.read_obj(obj_path)
    if not v:
        raise SystemExit('OBJ 에 면이 없습니다')
    if fit:
        idx = A.load_index()
        mesh = A.find(idx, OLD, 'Mesh') if idx else None
        if mesh:
            ov, _ouv, _ot, _n = A.read_mesh(TREE, mesh[0][0], mesh[0][1])
            ctr, ext = A.bounds(ov)
            v = A.fit_to(v, ctr, ext)
    if winding == 'flip':
        A.flip_winding(tri)
        say('감기를 통째로 뒤집었습니다')
    elif winding == 'auto':
        say('감기 %d개를 바깥쪽으로 맞췄습니다' % A.orient(v, tri))

    out = os.path.join(HERE, '%s.assets' % name.lower())
    root_pid, mat_pid, mbptr = build_assets(name, v, uv, tri, png_path,
                                            out, say)
    car_index = register_cardb(name, klass, gold, trophy, say)
    register_label(name, label, say)
    add_spec(spec_line(name, os.path.basename(out), root_pid, mat_pid,
                       mbptr, klass), name, say)
    import mkpack
    say('번들을 다시 굽습니다…')
    size = mkpack.build(quiet=True)
    say('pack.unity3d %.1f MB' % (size / 1048576.0))
    register_tables(car_index + 1, name, label, klass, gold, trophy, say)
    say('')
    say('새 차 "%s"(%s급)를 넣었습니다. carNo %d.'
        % (label, klass, car_index + 1))
    say('이제 APK 를 다시 만드세요. 서버판은 서버도 다시 띄워야 표가 맞습니다.')
    return car_index + 1


def main():
    ap = argparse.ArgumentParser(prog='newcar',
                                 description='내 모델을 새 차로 추가합니다')
    ap.add_argument('name', help='영문 이름 (자산·DB 에 쓰입니다)')
    ap.add_argument('--remove', action='store_true',
                    help='넣었던 차를 도로 뺍니다')
    ap.add_argument('--obj')
    ap.add_argument('--png')
    ap.add_argument('--label', help='게임에 보일 이름 (없으면 영문 이름)')
    ap.add_argument('--class', dest='klass', default='S',
                    choices=['C', 'B', 'A', 'S'])
    ap.add_argument('--gold', type=int, default=0)
    ap.add_argument('--trophy', type=int, default=150)
    ap.add_argument('--winding', default='keep',
                    choices=['keep', 'flip', 'auto'])
    ap.add_argument('--no-fit', action='store_true')
    a = ap.parse_args()
    if a.remove:
        remove(a.name)
        return 0
    if not a.obj or not a.png:
        ap.error('--obj 와 --png 가 있어야 합니다')
    add(a.name, a.obj, a.png, a.label, a.klass, a.gold, a.trophy,
        a.winding, not a.no_fit)
    return 0


if __name__ == '__main__':
    sys.exit(main())
