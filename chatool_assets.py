# -*- coding: utf-8 -*-
"""자산 도구의 백엔드. 런처 화면(자산 탭)과 CLI 가 **같은 함수**를 쓴다.

여기는 일만 하고, 화면은 chatool_page.py 가 그린다.
오래 걸리는 일(색인 만들기 · APK 빌드)은 작업(job)으로 돌려
런처가 진행 상황을 들여다본다.
"""
import base64
import io
import json
import os
import shutil
import threading
import time
import traceback

# UnityPy 는 **여기서 한 번** 들여온다.
#
# 런처는 요청마다 스레드를 띄운다. 자산 API 두 개가 동시에 처음 들어오면
# 두 스레드가 UnityPy 안의 순환 임포트를 함께 밟아
#   AttributeError: type object 'File' has no attribute 'File'
# 로 깨진다. 모듈 본문에서 들여오면 파이선의 모듈별 임포트 잠금이
# 나머지 스레드를 붙잡아 주므로 그 경합이 없어진다.
try:
    import UnityPy                                       # noqa: F401
except Exception:                                        # 없으면 세이브 기능만
    UnityPy = None

def _L(src, **kw):
    """화면에 뜨는 말. 지금 고른 언어로 옮긴다.

    열쇠는 한국어 원문 그대로다 — 번역이 없으면 한국어가 나온다."""
    import chalang
    return chalang.t(src, **kw)


# ------------------------------------------------------------------ 작업(job)
JOBS = {}
_JOBLOCK = threading.Lock()


def _new_job(title):
    jid = '%d' % int(time.time() * 1000)
    with _JOBLOCK:
        JOBS[jid] = {'title': title, 'log': [], 'done': False, 'ok': None}
    return jid


def job_say(jid, line):
    with _JOBLOCK:
        j = JOBS.get(jid)
        if j is not None:
            j['log'].append(line)
            del j['log'][:-400]


def run_job(title, fn):
    """fn(say) 를 딴 실 위에서 돌린다. 화면은 /api/job 으로 들여다본다."""
    jid = _new_job(title)

    def go():
        try:
            fn(lambda s: job_say(jid, s))
            ok = True
        except Exception as e:
            job_say(jid, _L('[실패] %s: %s') % (type(e).__name__, e))
            tb = traceback.format_exc().splitlines()
            for ln in tb[-4:]:
                job_say(jid, '   ' + ln)
            ok = False
        with _JOBLOCK:
            JOBS[jid]['done'] = True
            JOBS[jid]['ok'] = ok

    threading.Thread(target=go, daemon=True).start()
    return jid


def job_state(jid):
    with _JOBLOCK:
        j = JOBS.get(jid)
        if j is None:
            return {'ok': False, 'msg': _L('없는 작업입니다')}
        return {'ok': True, 'title': j['title'], 'log': list(j['log']),
                'done': j['done'], 'result': j['ok']}


# ------------------------------------------------------------------ 자리 찾기
def _env():
    import chatool
    return chatool


def extract_dir(car=None):
    base = os.path.join(_env().HERE, 'extract')
    return os.path.join(base, car) if car else base


def _index(say=None):
    import chaassets as A
    idx = A.load_index()
    if idx is None:
        if say:
            say(_L('자산 색인이 없습니다. 만드는 중입니다… (몇 분 걸립니다)'))
        idx = A.build_index(_env().TREE, progress=(
            (lambda i, n, f: (i % 40 == 0) and say('  %d/%d' % (i, n)))
            if say else None))
    return idx


def has_index():
    import chaassets as A
    return A.load_index() is not None


_CARS = [None]


def car_list():
    if _CARS[0] is None:
        import chaassets as A
        cars = A.car_list(_env().TREE)
        idx = A.load_index()
        for c in cars:
            c['variants'] = variants(idx, c['name']) if idx else []
        _CARS[0] = cars
    return _CARS[0]


# 자산 이름이 차 이름과 다른 것들. 모델러가 실제 차 이름을 그대로 썼다.
# (여기 없는 차는 아래 all_meshes() 의 전체 목록에서 고르면 된다)
ALIAS = {
    'PRIUS': 'CAR_Prius', 'Challenger': 'Dodge Challenger',
    'Evoque': 'RANGEROVER', 'GTR': 'nissan_GTR', 'McLaren': 'mp4-12c',
    'Boxster': 'SEED',                       # 게임 이름이 '시드' 다
}


def variants(idx, name):
    """`Meteor` -> ['Meteor_A', 'Meteor_A_LOW', 'Meteor_S', …]

    메시가 실제로 들어 있는 이름만 준다. 등급마다 모델이 따로라
    무엇을 고쳤는지 사람이 눈으로 알아야 한다."""
    out = []
    for base in {name, ALIAS.get(name, name)}:
        low = base.lower()
        for k, rows in idx.items():
            if k != low and not k.startswith(low + '_'):
                continue
            if k.startswith('player_') or k.startswith('sprite'):
                continue
            for r in rows:
                if r[2] == 'Mesh':
                    out.append(r[3])
                    break
    return sorted(set(out), key=lambda s: (s.endswith('_LOW'), s))


def resolve_asset(idx, name):
    """차 이름을 실제 자산 이름으로 바꿔 준다.

    모델러가 실제 차 이름을 쓴 차(에보크=RANGEROVER)는 이름만으로 못 찾는다.
    화면에서는 목록이 이미 자산 이름이라 안 걸리지만, '전부 내보내기' 처럼
    **차 이름으로** 들어오는 길에서는 여기를 거쳐야 한다."""
    ch = _env()
    m, t = ch._car_assets(idx, name)
    if m or t:
        return name
    vs = variants(idx, name)
    return vs[0] if vs else name


def resolve_pair(idx, name):
    """차 이름 -> (메시행, 텍스처행). **둘을 따로** 찾는다.

    한 이름에 둘 다 있는 차가 대부분이지만 아닌 것도 있다. 프리우스는
    메시가 `CAR_Prius`, 텍스처가 `PRIUS` 다. 이름 하나로만 찾으면
    둘 중 하나가 조용히 빠진다."""
    ch = _env()
    m, t = ch._car_assets(idx, name)
    if not m:
        for cand in variants(idx, name):
            m2, t2 = ch._car_assets(idx, cand)
            if m2:
                m, t = m2, (t or t2)
                break
    if not t:
        for cand in [name] + variants(idx, name):
            _m, t3 = ch._car_assets(idx, cand)
            if t3:
                t = t3
                break
    if not t and m:
        t = tex_via_material(m[0], m[1])
    if not m:
        # 스킨만 갈아입힌 차 — 제 이름의 메시가 없다(블링은 아베오 메시를
        # 그대로 쓴다). 같은 이름의 **머티리얼**에서 메시로 건너간다.
        m = mesh_via_material(idx, name)
    return m, t


def mesh_via_material(idx, name):
    """같은 이름의 머티리얼을 쓰는 렌더러의 메시를 돌려준다."""
    import chaanim as N
    import chaassets as A
    mats = N.load_mat_index()
    if not mats:
        return None
    for row in A.find(idx, name, 'Material'):
        hit = mats.get('%s:%d' % (row[0], row[1]))
        if hit:
            return [hit[0], hit[1], 'Mesh', _L('(머티리얼에서)')]
    return None


def tex_via_material(mesh_file, mesh_pid):
    """이름으로 못 찾을 때, **머티리얼을 따라가** 텍스처를 찾는다.

    프리우스처럼 메시(`CAR_Prius`)와 텍스처(`PRIUS`)의 이름이 다른 차가
    있다. 이름 짝맞추기는 거기서 진다. 메시 파일 안에는 렌더러가 함께
    들어 있으니 `m_Materials[0] -> _MainTex` 를 따라가면 확실하다."""
    import chaassets as A
    ch = _env()
    try:
        sf = A._sf(os.path.join(ch.TREE, A.DATA, mesh_file))
    except Exception:
        return None
    ext = [e.path for e in sf.externals]

    def deref(p, cur):
        f = p['m_FileID']
        return (cur if f == 0 else (ext[f - 1] if f - 1 < len(ext) else None),
                p['m_PathID'])

    mat = None
    for pid, o in sf.objects.items():
        if o.type.name not in ('SkinnedMeshRenderer', 'MeshRenderer'):
            continue
        try:
            t = o.read_typetree()
        except Exception:
            continue
        ms = t.get('m_Materials') or []
        if ms:
            mat = deref(ms[0], mesh_file)
            break
    if not mat or not mat[0]:
        return None
    try:
        msf = A._sf(os.path.join(ch.TREE, A.DATA, mat[0]))
        mt = msf.objects[mat[1]].read_typetree()
    except Exception:
        return None
    mext = [e.path for e in msf.externals]
    for te in (mt.get('m_SavedProperties') or {}).get('m_TexEnvs') or []:
        # [{'name': '_MainTex'}, {'m_Texture': …}] 꼴로 들어 있다
        pair = te if isinstance(te, (list, tuple)) else [te]
        nm = None
        ptr = None
        for x in pair:
            if isinstance(x, dict) and 'name' in x:
                nm = x['name']
            if isinstance(x, dict) and 'm_Texture' in x:
                ptr = x['m_Texture']
        if nm != '_MainTex' or not ptr or not ptr['m_PathID']:
            continue
        f = ptr['m_FileID']
        tf = mat[0] if f == 0 else (mext[f - 1] if f - 1 < len(mext) else None)
        if not tf:
            return None
        return [tf, ptr['m_PathID'], 'Texture2D', _L('(머티리얼에서)')]
    return None


def all_meshes(idx):
    """번들 안의 모든 메시 이름. 차 이름으로 못 찾는 것도 여기서 고른다."""
    return sorted({r[3] for rows in idx.values() for r in rows
                   if r[2] == 'Mesh'})


# ------------------------------------------------------------------ 갈래
# 번들 안 메시 202개를 통째로 늘어놓으면 고르기가 고약하다. 이름 규칙이
# 뚜렷해서 갈래로 나눌 수 있다(실측한 이름들을 보고 정했다).
# 이름은 **원문으로** 둡니다. 여기서 옮기면 모듈이 실릴 때 굳어 버려
# 언어를 바꿔도 안 따라옵니다 — 쓰는 자리(catalog)에서 옮깁니다.
CATS = [
    ('car', '자동차 (차고에 있는 것)'),
    ('npc', '상대 차 · NPC'),
    ('map', '배경 · 맵'),
    ('item', '아이템 · 소품'),
    ('etc', '그 밖'),
]
_MAP_PRE = ('data_g', 'gcity', 'gtunnel', 'sand', 'aqua', 'bbeach', 'bbridge',
            'bcity', 'beach', 'bfield', 'bridge', 'btunnel', 'city', 'field',
            'tunnel')
_ITEM_PRE = ('item', 'coin', 'gold', 'box', 'object', 'objobject', 'eff',
             'check')
_NPC_PRE = ('car_0', 'car_1', 'car_6', 'car_stellar', 'car_npc', '86',
            'beetle', 'orc', 's_aston')
_GRADES = ('_a', '_b', '_c', '_s', '_r')


def base_of(name):
    """`Thunder_A_LOW` -> `Thunder`. 등급과 LOD 꼬리를 뗀다."""
    n = name
    low = n.lower()
    if low.endswith('_low'):
        n = n[:-4]
        low = n.lower()
    for g in _GRADES:
        if low.endswith(g):
            n = n[:-2]
            break
    return n


def classify(base):
    b = base.lower()
    if b.startswith(_MAP_PRE):
        return 'map'
    if b.startswith(_ITEM_PRE):
        return 'item'
    if b.startswith(_NPC_PRE):
        return 'npc'
    return 'etc'


_LABELS = [None]


def car_labels():
    """`CarName_AVEO` -> `가루다`. 화면에 게임 이름으로 보여 주려고 읽는다."""
    if _LABELS[0] is not None:
        return _LABELS[0]
    out = {}
    try:
        import freetext as F
        from sfparse import parse
        p = os.path.join(_env().HERE, 'x77', F.ASSET)
        raw = bytearray(io.open(p, 'rb').read())
        text, _st, _n = F.textasset(raw, parse(p), 1)
        for ln in text.splitlines():
            if not ln.startswith('CarName_') or '=' not in ln:
                continue
            k, v = ln.split('=', 1)
            out[k.strip()[8:]] = v.strip()
    except Exception:
        pass
    _LABELS[0] = out
    return out


def catalog():
    """세 단짜리 고르기 표 — 갈래 -> 대상 -> 모델."""
    import chaassets as A
    idx = _index()
    names = car_labels()
    cars, used = [], set()
    for c in car_list():
        vs = variants(idx, c['name'])
        if not vs:
            m = resolve_pair(idx, c['name'])[0]
            vs = [m[3]] if m else []
        used.update(vs)
        ko = names.get(c['name'])
        cars.append({'name': c['name'],
                     'label': '%d. %s%s' % (c['carNo'], ko or c['name'],
                                            (' (%s)' % c['name']) if ko else ''),
                     'models': vs or [c['name']]})
    groups = {}
    for m in all_meshes(idx):
        if m in used:
            continue
        b = base_of(m)
        groups.setdefault((classify(b), b), []).append(m)
    out = []
    for key, label in CATS:
        label = _L(label)
        if key == 'car':
            out.append({'key': key, 'label': label, 'items': cars})
            continue
        items = [{'name': b, 'label': b, 'models': sorted(v)}
                 for (k, b), v in sorted(groups.items()) if k == key]
        out.append({'key': key, 'label': label, 'items': items})
    return out


# ------------------------------------------------------------------ 뽑기
def extract(car, say=None):
    """텍스처 PNG · 메시 OBJ · UV 안내선을 extract/<차>/ 에 만든다."""
    import chaassets as A
    ch = _env()
    idx = _index(say)
    out = extract_dir(car)
    os.makedirs(out, exist_ok=True)
    mesh, tex = resolve_pair(idx, car)
    res = {'car': car, 'tex': None, 'uv': None, 'obj': None, 'mesh': None}
    png = None
    if tex:
        png = os.path.join(out, car + '.png')
        w, h = A.export_texture(ch.TREE, tex[0], tex[1], png)
        res['tex'] = '%s/%s.png' % (car, car)
        res['texSize'] = [w, h]
        if say:
            say(_L('텍스처 %dx%d') % (w, h))
    if mesh:
        v, uv, tri, nm = A.read_mesh(ch.TREE, mesh[0], mesh[1])
        obj = os.path.join(out, car + '.obj')
        A.write_obj(obj, v, uv, tri, nm)
        c, e = A.bounds(v)
        res['obj'] = '%s/%s.obj' % (car, car)
        res['mesh'] = {'name': nm, 'verts': len(v), 'tris': len(tri) // 3,
                       'size': [round(e[0] * 2, 3), round(e[1] * 2, 3),
                                round(e[2] * 2, 3)]}
        if say:
            say(_L('메시 %s — 정점 %d · 삼각형 %d') % (nm, len(v), len(tri) // 3))
        if png:
            g = os.path.join(out, car + '_uv.png')
            A.uv_guide(png, uv, tri, g)
            res['uv'] = '%s/%s_uv.png' % (car, car)
    if not mesh and not tex:
        raise RuntimeError(_L('그런 이름의 자산이 없습니다: %s') % car)
    return res


def mesh_json(car):
    """화면의 3D 미리보기가 쓸 기하 자료. 평평한 배열로 준다."""
    import chaassets as A
    ch = _env()
    idx = _index()
    mesh, tex = resolve_pair(idx, car)
    if not mesh:
        return {'ok': False, 'msg': _L('메시가 없습니다: %s') % car}
    v, uv, tri, nm = A.read_mesh(ch.TREE, mesh[0], mesh[1])
    ctr, ext = A.bounds(v)
    flat = []
    for p in v:
        flat += [round(p[0], 4), round(p[1], 4), round(p[2], 4)]
    fuv = []
    for t in (uv or []):
        fuv += [round(t[0], 4), round(t[1], 4)]
    tp = os.path.join(extract_dir(car), car + '.png')
    return {'ok': True, 'name': nm, 'v': flat, 'uv': fuv, 'tri': list(tri),
            'center': [round(x, 4) for x in ctr],
            'extent': [round(x, 4) for x in ext],
            'tex': ('%s/%s.png' % (car, car)) if os.path.exists(tp) else None}


# ------------------------------------------------------------------ 다시 칠하기
def repaint(car, png_bytes, say=None):
    import chaassets as A
    ch = _env()
    idx = _index(say)
    _, tex = resolve_pair(idx, car)
    if not tex:
        raise RuntimeError(_L('텍스처를 찾지 못했습니다: %s') % car)
    d = extract_dir(car)
    os.makedirs(d, exist_ok=True)
    tmp = os.path.join(d, '_new.png')
    io.open(tmp, 'wb').write(png_bytes)
    n = A.import_texture(ch.TREE, tex[0], tex[1], tmp)
    import chalog
    chalog.add('asset', _L('텍스처를 다시 칠했습니다: %s') % car,
               {'바이트': n, '파일': tex[0]})
    if say:
        say(_L('다시 칠했습니다: %s (%d바이트, 길이 보존)') % (car, n))
        say(_L('`APK 만들기` 로 다시 빌드해야 기기에 반영됩니다.'))
    return n


# ------------------------------------------------------------------ 들여오기
def import_obj(like, obj_text, winding='keep', fit=True, say=None):
    import chaassets as A
    ch = _env()
    idx = _index(say)
    mesh, _ = ch._car_assets(idx, like)
    if not mesh:
        raise RuntimeError(_L('기준 차의 메시를 찾지 못했습니다: %s') % like)
    d = extract_dir(like)
    os.makedirs(d, exist_ok=True)
    tmp = os.path.join(d, '_in.obj')
    io.open(tmp, 'w', encoding='utf-8').write(obj_text)
    v, uv, tri = A.read_obj(tmp)
    if not v:
        raise RuntimeError(_L('OBJ 에 면이 없습니다'))
    old_v, old_uv, old_tri, old_name = A.read_mesh(ch.TREE, mesh[0], mesh[1])
    ctr, ext = A.bounds(old_v)
    if fit:
        v = A.fit_to(v, ctr, ext)
    note = _L('감기 그대로')
    if winding == 'flip':
        A.flip_winding(tri)
        note = _L('감기를 통째로 뒤집었습니다')
    elif winding == 'auto':
        note = _L('감기 %d개를 바깥쪽으로 맞췄습니다') % A.orient(v, tri)
    if say:
        say(_L('정점 %d · 삼각형 %d · %s') % (len(v), len(tri) // 3, note))
    p = os.path.join(ch.TREE, A.DATA, mesh[0])
    sf = A._sf(p)
    o = sf.objects[mesh[1]]
    blob = bytes(o.save_typetree(
        A.pack_mesh(o.read_typetree(), v, uv, tri, old_name)))
    bdir = os.path.join(ch.HERE, 'backup')
    os.makedirs(bdir, exist_ok=True)
    bak = os.path.join(bdir, mesh[0] + '.bak')
    if not os.path.exists(bak):
        shutil.copyfile(p, bak)
    size = A.replace_object(ch.TREE, mesh[0], mesh[1], blob)
    import chalog
    chalog.add('asset', _L('메시를 갈아 끼웠습니다: %s') % like,
               {'정점': len(v), '삼각형': len(tri) // 3, '파일': mesh[0]})
    if say:
        say(_L('교체했습니다 (%d바이트). 원본은 backup/ 에 남아 있습니다.') % size)
        say(_L('차고에서 멀쩡해 보여도 **주행 화면**을 꼭 확인하세요.'))
    return size


# ------------------------------------------------------------------ 새 차 추가
def add_car(name, label, klass, obj_text, png_bytes, gold, trophy,
            winding='keep', fit=True, say=None):
    """모델을 **새 차로** 넣습니다. 기존 차를 덮어쓰지 않습니다."""
    import newcar
    ch = _env()
    d = os.path.join(extract_dir(), '_new')
    os.makedirs(d, exist_ok=True)
    obj = os.path.join(d, '%s.obj' % name)
    png = os.path.join(d, '%s.png' % name)
    io.open(obj, 'w', encoding='utf-8').write(obj_text)
    io.open(png, 'wb').write(png_bytes)
    say = say or (lambda x: None)
    no = newcar.add(name, obj, png, label, klass, gold, trophy,
                    winding, fit, say)
    _CARS[0] = None                      # 차 목록을 다시 읽게 한다
    import chalog
    chalog.add('asset', _L('새 차를 넣었습니다: %s (%s)') % (label, name),
               {'차 번호': no, '등급': klass, '골드': gold, '트로피': trophy})
    return no


# ------------------------------------------------------------------ 동작
def _rig_index(say=None):
    import chaanim as N
    ridx = N.load_rig_index()
    if ridx is None:
        if say:
            say(_L('뼈대 색인이 없습니다. 만드는 중입니다… (몇 분 걸립니다)'))
        ridx = N.build_rig_index(_env().TREE, progress=(
            (lambda i, n, f: (i % 60 == 0) and say('  %d/%d' % (i, n)))
            if say else None))
    return ridx


def has_rig_index():
    import chaanim as N
    return N.load_rig_index() is not None


def rig_of(name, say=None):
    """자산 이름 -> 뼈대. 스키닝 메시가 아니면 None."""
    import chaanim as N
    ch = _env()
    idx = _index(say)
    mesh, _tex = resolve_pair(idx, name)
    if not mesh:
        return None
    return N.rig(ch.TREE, mesh[0], mesh[1], _rig_index(say))


def anim_info(name):
    """화면이 쓸 뼈대 요약 — 뼈 이름 · 정점별 가중치 · 클립 목록."""
    import chaanim as N
    ch = _env()
    if not has_rig_index():
        return {'ok': False, 'need': 'index',
                'msg': _L('뼈대 색인이 아직 없습니다.')}
    r = rig_of(name)
    if not r:
        return {'ok': False, 'msg': _L('%s 는 뼈대가 없습니다') % name}
    w, b = [], []
    for s in r['skin']:
        for k in range(4):
            w.append(round(s['weight[%d]' % k], 4))
            b.append(s['boneIndex[%d]' % k])
    clips = []
    for c in r['clips']:
        try:
            cl = N.clip_of(c)
        except Exception:
            continue
        clips.append({'name': cl['name'], 'length': round(cl['length'], 3),
                      'fps': cl['fps'], 'file': c['file'], 'pid': c['pid']})
    return {'ok': True, 'name': name, 'meshName': r['meshName'],
            'bones': [r['paths'].get(x, '?') for x in r['bones']],
            'w': w, 'b': b, 'verts': len(r['skin']), 'clips': clips}


def anim_bake(name, clip_name, fps=30.0):
    import chaanim as N
    ch = _env()
    r = rig_of(name)
    if not r:
        return {'ok': False, 'msg': _L('뼈대가 없습니다')}
    for c in r['clips']:
        cl = N.clip_of(c)
        if cl['name'] != clip_name:
            continue
        bk = N.bake(r, cl, fps)
        flat = []
        for fr in bk['frames']:
            for m in fr:
                flat += m
        return {'ok': True, 'name': cl['name'], 'fps': bk['fps'],
                'count': bk['count'], 'bones': len(r['bones']), 'm': flat,
                'length': round(cl['length'], 3)}
    return {'ok': False, 'msg': _L('그런 동작이 없습니다: %s') % clip_name}


# ------------------------------------------------------------------ 내보내기
# 형식 이름 -> (설명, 확장자). 화면의 체크상자와 여기가 짝이다.
FORMATS = [
    ('obj', 'OBJ + MTL — 블렌더·3ds맥스에서 고치기 좋습니다', '.obj'),
    ('glb', 'glTF (.glb) — 텍스처까지 한 파일. 윈도우 3D 뷰어가 바로 엽니다', '.glb'),
    ('stl', 'STL — 3D 프린터·조형용(색과 UV 는 못 담습니다)', '.stl'),
    ('png', '텍스처 PNG — 그대로 칠해서 되돌려 넣으면 됩니다', '.png'),
    ('uv', 'UV 안내선 PNG — 어디가 보닛인지 선으로 보여 줍니다', '_uv.png'),
    ('json', '자산 정보 JSON — 어느 파일 몇 번인지까지 적어 둡니다', '.json'),
    ('anim', '동작 glTF (.glb) — 뼈대와 동작까지 넣습니다. 블렌더에서 재생됩니다',
     '_anim.glb'),
    ('animjson', '동작 JSON — 뼈마다 프레임별 행렬을 그대로 적습니다', '_anim.json'),
]
FORMAT_KEYS = [f[0] for f in FORMATS]
NL = '\n'


def export_dir():
    return os.path.join(_env().HERE, 'export')


def open_folder(path):
    """탐색기로 폴더를 엽니다. 창 런처는 내려받기를 못 하니 이 길로 줍니다."""
    p = os.path.abspath(path)
    if not os.path.isdir(p):
        return {'ok': False, 'msg': _L('그런 폴더가 없습니다: %s') % p}
    try:
        os.startfile(p)                              # 윈도우
    except AttributeError:
        import subprocess
        subprocess.Popen(['xdg-open', p])
    return {'ok': True, 'path': p}


def export_one(name, fmts, root, say=None):
    """자산 하나를 고른 형식들로 내보냅니다. 만든 파일 목록을 돌려줍니다."""
    import chaassets as A
    ch = _env()
    idx = _index(say)
    mesh, tex = resolve_pair(idx, name)
    if not mesh and not tex:
        raise RuntimeError(_L('그런 이름의 자산이 없습니다: %s') % name)
    if mesh and say and mesh[3] != name:
        say(_L('  %s 의 메시 이름은 %s 입니다') % (name, mesh[3]))
    d = os.path.join(root, name)
    os.makedirs(d, exist_ok=True)
    made = []

    png = os.path.join(d, name + '.png')
    size = None
    # 텍스처는 glTF · UV 안내선 · MTL 이 다 같이 쓰므로 필요하면 먼저 굽습니다.
    need_png = bool(tex) and bool({'png', 'uv', 'glb', 'obj', 'json'} & set(fmts))
    if need_png:
        size = A.export_texture(ch.TREE, tex[0], tex[1], png)
        if 'png' in fmts:
            made.append(png)

    v = uv = tri = nm = None
    if mesh and ({'obj', 'glb', 'stl', 'uv', 'json', 'anim', 'animjson'}
                 & set(fmts)):
        v, uv, tri, nm = A.read_mesh(ch.TREE, mesh[0], mesh[1])

    if v and 'obj' in fmts:
        obj = os.path.join(d, name + '.obj')
        A.write_obj(obj, v, uv, tri, nm)
        # OBJ 는 스스로 MTL 을 불러야 텍스처가 따라옵니다.
        lines = io.open(obj, encoding='utf-8').read().splitlines()
        head = [ln for ln in lines if ln.startswith('#')]
        rest = [ln for ln in lines if not ln.startswith('#')]
        io.open(obj, 'w', encoding='utf-8').write(
            NL.join(head + ['mtllib %s.mtl' % name,
                            'usemtl %s' % name] + rest) + NL)
        mtl = os.path.join(d, name + '.mtl')
        A.write_mtl(mtl, name, (name + '.png') if need_png else None)
        made += [obj, mtl]

    if v and 'glb' in fmts:
        glb = os.path.join(d, name + '.glb')
        A.write_glb(glb, v, uv, tri, nm, png if need_png else None)
        made.append(glb)

    if v and 'stl' in fmts:
        stl = os.path.join(d, name + '.stl')
        A.write_stl(stl, v, tri, nm)
        made.append(stl)

    if v and 'uv' in fmts and need_png:
        g = os.path.join(d, name + '_uv.png')
        A.uv_guide(png, uv, tri, g)
        made.append(g)

    if 'json' in fmts:
        info = {'name': name, 'mesh': None, 'texture': None}
        if mesh:
            ctr, ext = A.bounds(v) if v else ((0, 0, 0), (0, 0, 0))
            info['mesh'] = {'assetName': nm, 'file': mesh[0], 'pathId': mesh[1],
                            'verts': len(v or []), 'tris': len(tri or []) // 3,
                            'size': [round(ext[0] * 2, 4), round(ext[1] * 2, 4),
                                     round(ext[2] * 2, 4)],
                            'center': [round(x, 4) for x in ctr]}
        if tex:
            info['texture'] = {'file': tex[0], 'pathId': tex[1],
                               'size': list(size) if size else None}
        info['note'] = _L('좌표계: x 좌우 · y 앞뒤 · z 높이(Z-up). '
                          'glb 만 규격에 맞춰 Y-up 으로 눕혀 두었습니다.')
        j = os.path.join(d, name + '.json')
        io.open(j, 'w', encoding='utf-8').write(
            json.dumps(info, ensure_ascii=False, indent=2))
        made.append(j)

    if v and ({'anim', 'animjson'} & set(fmts)):
        import chaanim as N
        r = N.rig(ch.TREE, mesh[0], mesh[1], _rig_index(say))
        if not r:
            if say:
                say(_L('  %s — 뼈대가 없어 동작은 건너뜁니다') % name)
        else:
            clips = []
            for c in r['clips']:
                try:
                    clips.append(N.clip_of(c))
                except Exception:
                    pass
            if not clips and say:
                say(_L('  %s — 붙어 있는 동작이 없습니다') % name)
            if clips and 'anim' in fmts:
                import chaanimglb as GB
                g = os.path.join(d, name + '_anim.glb')
                _sz, na = GB.write(g, r, v, uv, tri, clips,
                                   png if need_png else None)
                made.append(g)
                if say:
                    say(_L('  %s — 동작 %d개를 glTF 에 담았습니다') % (name, na))
            if clips and 'animjson' in fmts:
                out = {'mesh': r['meshName'],
                       'bones': [r['paths'].get(x, '?') for x in r['bones']],
                       'note': _L('프레임마다 뼈별 스키닝 행렬(행 우선 4x4). '
                                  '정점에 가중치로 섞어 쓰면 됩니다.'),
                       'clips': []}
                for cl in clips:
                    bk = N.bake(r, cl, 30.0)
                    out['clips'].append({
                        'name': cl['name'], 'length': round(cl['length'], 3),
                        'fps': bk['fps'], 'frames': bk['count'],
                        'matrices': bk['frames']})
                j = os.path.join(d, name + '_anim.json')
                io.open(j, 'w', encoding='utf-8').write(
                    json.dumps(out, ensure_ascii=False))
                made.append(j)

    if not need_png and ({'png', 'uv'} & set(fmts)) and say:
        say(_L('  %s — 텍스처가 없어 PNG 는 건너뜁니다') % name)
    if not v and ({'obj', 'glb', 'stl'} & set(fmts)) and say:
        say(_L('  %s — 메시가 없어 모델은 건너뜁니다') % name)
    return made


def export_many(names, fmts, say, root=None):
    root = root or export_dir()
    os.makedirs(root, exist_ok=True)
    fmts = [f for f in fmts if f in FORMAT_KEYS]
    if not fmts:
        raise RuntimeError(_L('내보낼 형식을 하나는 골라야 합니다'))
    say(_L('%s 로 내보냅니다') % root)
    say(_L('형식: %s') % ' · '.join(fmts))
    total, bad = 0, 0
    for i, nm in enumerate(names, 1):
        try:
            made = export_one(nm, fmts, root, say)
            total += len(made)
            say(_L('[%d/%d] %s — 파일 %d개') % (i, len(names), nm, len(made)))
        except Exception as e:
            bad += 1
            say(_L('[%d/%d] %s — 실패: %s') % (i, len(names), nm, e))
    import chalog
    chalog.add('asset', _L('자산을 내보냈습니다 (%d개 대상 · 파일 %d개)')
               % (len(names), total), {'형식': fmts, '자리': root})
    say(_L('끝났습니다. 파일 %d개%s') % (total, (_L(' · 실패 %d개') % bad) if bad else ''))
    say('@@' + json.dumps({'dir': root, 'files': total}, ensure_ascii=False))
    return {'dir': root, 'files': total}


# ------------------------------------------------------------------ 파일 내주기
SAFE_EXT = {'.png': 'image/png', '.jpg': 'image/jpeg',
            '.obj': 'text/plain; charset=utf-8'}


def serve_file(rel):
    """extract/ 아래 것만 내준다."""
    rel = rel.replace('\\', '/').lstrip('/')
    if '..' in rel.split('/'):
        return None, None
    ext = os.path.splitext(rel)[1].lower()
    if ext not in SAFE_EXT:
        return None, None
    p = os.path.join(extract_dir(), *rel.split('/'))
    if not os.path.exists(p):
        return None, None
    return io.open(p, 'rb').read(), SAFE_EXT[ext]


# ------------------------------------------------------------------ 긴 작업
def _reindex(say):
    import chaassets as A
    A.build_index(_env().TREE, progress=lambda i, n, f:
                  (i % 40 == 0) and say('  %d/%d' % (i, n)))
    _CARS[0] = None
    say(_L('색인을 다 만들었습니다'))


def _build(say, mode, install, slot=None, opts=None):
    """굽기. 속은 `chabuild` 에 있고 창 런처도 같은 것을 부릅니다."""
    import chabuild
    o = opts or {}
    try:
        r = chabuild.run(say, mode=mode, slot=slot, install=install,
                         way=o.get('way') or 'usb', host=o.get('host') or '',
                         port=o.get('port') or '8888',
                         server_save=o.get('server_save') or 'use',
                         bundle=bool(o.get('bundle')))
    except Exception as e:
        import chalog
        chalog.add('build', _L('APK 굽기 실패 (%s)') % mode, str(e))
        say('■ %s' % e)
        raise
    say(_L('끝났습니다 (%d초)') % r['secs'])
    say('@@' + json.dumps(r, ensure_ascii=False))


def _extract_job(say, car):
    r = extract(car, say)
    say('@@' + json.dumps(r, ensure_ascii=False))
    return r


# ------------------------------------------------------------------ 요청 처리
def api(path, body):
    if path == '/api/assets/list':
        import chaassets as A
        idx = A.load_index()
        return {'ok': True, 'cars': car_list(), 'indexed': idx is not None,
                'meshes': all_meshes(idx) if idx else [],
                'cats': catalog() if idx else []}

    if path == '/api/assets/index':
        return {'ok': True, 'job': run_job(_L('자산 색인'), _reindex),
                'msg': _L('색인을 만드는 중입니다. 몇 분 걸립니다.')}

    if path == '/api/assets/get':
        car = body['car']
        return {'ok': True,
                'job': run_job(_L('%s 뽑기') % car,
                               lambda say: _extract_job(say, car))}

    if path == '/api/assets/mesh':
        return mesh_json(body['car'])

    if path == '/api/assets/anim':
        return anim_info(body.get('car') or '')

    if path == '/api/assets/anim/bake':
        return anim_bake(body.get('car') or '', body.get('clip') or '',
                         float(body.get('fps') or 30))

    if path == '/api/assets/anim/index':
        return {'ok': True,
                'job': run_job(_L('뼈대 색인'), lambda say: _rig_index(say)),
                'msg': _L('뼈대 색인을 만드는 중입니다. 몇 분 걸립니다.')}

    if path == '/api/assets/formats':
        # 설명은 **여기서** 옮긴다. 표 자체는 원문으로 둬야 언어를 바꿀 때
        # 같이 따라온다(모듈이 실릴 때 옮기면 그대로 굳는다).
        return {'ok': True, 'formats': [{'key': k, 'desc': _L(d), 'ext': e}
                                        for k, d, e in FORMATS],
                'dir': export_dir()}

    if path == '/api/assets/export':
        import chapick
        root = body.get('dir') or chapick.folder(
            _L('자산을 어디에 내보낼까요'), chapick.default_dir(_env().HERE))
        if not root:
            return {'ok': False, 'msg': _L('취소했습니다')}
        scope = body.get('scope') or 'one'
        fmts = body.get('formats') or ['obj']
        if scope == 'all':
            names = [c['name'] for c in car_list()]
        elif scope == 'pick':
            names = [n for n in (body.get('names') or []) if n]
        else:
            names = [body.get('car') or '']
        names = [n for n in names if n]
        if not names:
            return {'ok': False, 'msg': _L('내보낼 자산을 하나는 골라야 합니다')}
        title = (_L('%s 내보내기') % names[0]) if len(names) == 1 else \
                (_L('자산 %d개 내보내기') % len(names))
        return {'ok': True, 'count': len(names),
                'job': run_job(title,
                               lambda say: export_many(names, fmts, say, root))}

    if path == '/api/assets/openfolder':
        return open_folder(body.get('path') or export_dir())

    if path == '/api/assets/repaint':
        car = body['car']
        raw = base64.b64decode((body['png'] or '').split(',')[-1])
        return {'ok': True,
                'job': run_job(_L('%s 다시 칠하기') % car,
                               lambda say: repaint(car, raw, say))}

    if path == '/api/assets/import':
        like, txt = body['like'], body['obj']
        wd = body.get('winding') or 'keep'
        fit = bool(body.get('fit', True))
        return {'ok': True,
                'job': run_job(_L('%s 자리에 넣기') % like,
                               lambda say: import_obj(like, txt, wd, fit, say))}

    if path == '/api/assets/newcar':
        name = (body.get('name') or '').strip()
        label = (body.get('label') or '').strip() or name
        klass = (body.get('class') or 'S').upper()
        gold = int(body.get('gold') or 0)
        trophy = int(body.get('trophy') or 0)
        wd = body.get('winding') or 'keep'
        fit = bool(body.get('fit', True))
        obj = body.get('obj') or ''
        png = base64.b64decode((body.get('png') or '').split(',')[-1])
        if not name or not obj or not png:
            return {'ok': False, 'msg': _L('이름 · OBJ · PNG 가 모두 있어야 합니다')}
        return {'ok': True,
                'job': run_job(_L('새 차 %s 추가') % label,
                               lambda say: add_car(name, label, klass, obj,
                                                   png, gold, trophy, wd,
                                                   fit, say))}

    if path == '/api/build':
        import chabuild
        mode = body.get('mode') or 'local'
        inst = bool(body.get('install'))
        slot = (body.get('slot') or '').strip() or None
        opts = {k: body.get(k) for k in
                ('way', 'host', 'port', 'server_save', 'bundle')}
        stop = chabuild.check(mode, opts.get('way') or 'usb',
                              opts.get('host') or '', opts.get('port'),
                              _env()._msg)
        if stop:
            return {'ok': False, 'msg': stop}
        chabuild.save_conf(dict(opts, mode=mode))
        return {'ok': True,
                'job': run_job(_L('APK 굽기(%s)') % mode,
                               lambda say: _build(say, mode, inst, slot,
                                                  opts))}

    if path == '/api/build/presets':
        ch = _env()
        return {'ok': True, 'pkg': ch.PKG, 'app': ch.APP_LABEL}

    if path == '/api/job':
        return job_state(body.get('id') or '')

    return {'ok': False, 'msg': _L('모르는 자산 요청입니다: %s') % path}
