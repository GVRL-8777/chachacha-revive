# -*- coding: utf-8 -*-
"""한국 정식판 5.1.0 에서 **정품 차 8대**를 지금 빌드로 옮긴다.

    폴리(17) 로이(18) 엠버(19) 헬리(21) 태극호(23)
    아크엔젤(34) W3(35) 블리츠(36)

이 차들은 중국판 7.7 에 자원이 아예 없어 `trimcars.py` 로 표에서 지워 뒀거나
(아크엔젤·W3·블리츠), 공여판에서 빌려 온 임시 사본으로 때워 뒀다(헬리).
5.1.0 에는 넷 다 원본이 그대로 있다.

## 왜 그냥 못 붙이나 — MonoScript 번호가 다르다

차 프리팹은 `CarDataLinker` 같은 스크립트를 달고 있어야 굴러간다. 그런데
스크립트를 가리키는 `m_Script` 는 `sharedassets0.assets` 안 **pathID** 이고,
그 번호는 빌드마다 다르다. 실측: 이름이 겹치는 스크립트 497개 중 번호가
같은 것은 **0개**였다.

    JumpLanding            우리 616   5.1.0 592
    CarDataLinker          우리 492   5.1.0 479
    ...

다행히 8대가 쓰는 스크립트는 여섯 갈래뿐이고 전부 우리 빌드에도 있다. 그래서
원본을 스크래치로 뜬 뒤 MonoBehaviour 의 `m_Script` pathID 를 **이름으로 찾아
우리 번호로 바꿔 적는다.** 길이가 같아 제자리에서 고칠 수 있다.

## 헬리는 갈아 끼운다

번들은 오브젝트를 **이름으로** 찾는다(`Generic_Title.__ChaFromBundle`).
공여판 헬리와 정품 헬리는 이름이 똑같아 그냥 더하면 둘 중 하나가 이긴다.
그래서 붙이기 전에 지금 번들의 `car/helly/*` 를 `old_` 로 개명하고 매니페스트
에서 뺀다. 자원은 남지만 아무도 못 찾으므로 부딪히지 않는다.

## 차 표는 정식판 것을 통째로 쓴다

우리 표(31대)는 중국판에서 온 것이라 헬리 값이 우리가 지어낸 것이고 등급도
17번에 얹혀 있었다. 5.1.0 표(37대)가 정답이므로 통째로 바꾼다. 겹치는 30대
중 값이 다른 것은 다섯뿐이다(CAT·Challenger·Choper·Falcon·helly).
`--scan` 이 그 차이를 보여 준다.

트로이는 로이의 자리(18)를 쓰고 있었으므로 여기서 **빠진다.** 사용자 지시대로
정품 차가 다 안정된 뒤 빈 번호로 다시 넣는다. 그 자리를 위해 표 안에 빈칸을
넉넉히 남겨 둔다(`addtroy.register_cardb` 가 빈칸을 찾아 끼운다).

    python tools/addcars5.py --scan     무엇을 가져오나
    python tools/addcars5.py            넣는다
    python tools/addcars5.py --remove   backup/bundle 로 되돌린다
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

V510 = os.path.join(HERE, '_scratch', 'v5', 'v510')
SRC = os.path.join(V510, 'assets', 'bin', 'Data')
XD = os.path.join(HERE, 'x77', 'assets', 'bin', 'Data')
WORK = os.path.join(HERE, '_scratch', 'cars5')
OUT = os.path.join(HERE, 'cars5.assets')
PACKDAT = os.path.join(HERE, 'pack.dat')
BUNDLE = os.path.join(HERE, 'bundles', 'pack.unity3d')
BAKDIR = os.path.join(HERE, 'backup', 'bundle')
CARDB = os.path.join(XD, 'ade64ecd8944d9640bb1438deb4f6fe3')
NEWCARS = os.path.join(HERE, 'newcars.json')
SERVER = os.path.join(CODE, 'chacnserver.py')
S0 = 'sharedassets0.assets'

CARS = ('Poli', 'Roy', 'Amber', 'Taegeuk', 'Archangel', 'W3', 'Blitz', 'helly')

# 번들 덧붙이기 차례에서 이 도구의 자리 (`tools/bundlechain.py`)
STAGE = 'bundle5'

# 트로이가 나중에 끼어들 빈칸. `addtroy.register_cardb` 가 자기 조각 길이
# +40 만큼 이어진 공백을 찾는다. 한 대 분량이 900바이트 안쪽이라 넉넉하다.
PAD = 2000


def _sf(path):
    from UnityPy.streams import EndianBinaryReader
    from UnityPy.files.SerializedFile import SerializedFile
    return SerializedFile(EndianBinaryReader(io.open(path, 'rb').read()), None)


def joined(path):
    """통짜 파일이 없으면 `.splitN` 을 이어 스크래치에 만들어 준다.

    우리 트리의 `sharedassets0.assets` 는 조각으로만 있다. 엔진도 조각을
    읽으므로 통짜를 만들 일이 없었다 (`docs/HIRES.md`)."""
    if os.path.exists(path):
        return path
    d, base = os.path.dirname(path), os.path.basename(path)
    n = 0
    parts = []
    while os.path.exists(os.path.join(d, '%s.split%d' % (base, n))):
        parts.append(os.path.join(d, '%s.split%d' % (base, n)))
        n += 1
    if not parts:
        raise SystemExit('없는 파일: %s' % path)
    jd = os.path.join(HERE, '_scratch', 'join')
    os.makedirs(jd, exist_ok=True)
    out = os.path.join(jd, base)
    if not os.path.exists(out):
        with io.open(out, 'wb') as f:
            for p in parts:
                f.write(io.open(p, 'rb').read())
    return out


# ------------------------------------------------------------ 스크립트 번호
def script_map(path):
    """{pathID: 클래스이름} — MonoScript 의 첫 필드가 클래스 이름이다."""
    out = {}
    for pid, o in _sf(path).objects.items():
        if o.type.name != 'MonoScript':
            continue
        d = bytes(o.get_raw_data())
        n = struct.unpack_from('<i', d, 0)[0]
        if 0 < n < 200:
            try:
                out[pid] = d[4:4 + n].decode('utf-8')
            except UnicodeDecodeError:
                pass
    return out


def remap():
    """({5.1.0 pathID: 우리 pathID}, {5.1.0 pathID: 이름})."""
    theirs = script_map(os.path.join(SRC, S0))
    ours = script_map(joined(os.path.join(XD, S0)))
    back = {}
    for pid, nm in sorted(ours.items()):
        back.setdefault(nm, pid)
    return dict((p, back[n]) for p, n in theirs.items() if n in back), theirs


# ------------------------------------------------------------ 가져올 것 모으기
def collect():
    """{원본파일: [(번들안이름, pathID)]}"""
    import UnityPy
    from sfparse import parse
    md = os.path.join(SRC, 'mainData')
    ext = [os.path.basename(e) for e in parse(md)['externals']]
    rm = [o for o in UnityPy.load(md).objects
          if o.type.name == 'ResourceManager'][0]
    low = tuple('car/%s/' % c.lower() for c in CARS)
    out = {}
    for k, v in rm.read_typetree()['m_Container']:
        if not k.startswith(low):
            continue
        fn = ext[v['m_FileID'] - 1] if v['m_FileID'] else 'mainData'
        out.setdefault(fn, []).append((k, v['m_PathID']))
    return out


# ------------------------------------------------------------ 스크립트 다시 적기
def restamp(say):
    """원본을 스크래치로 뜨면서 `m_Script` pathID 를 우리 번호로 고친다."""
    from sfparse import parse
    smap, theirs = remap()
    if os.path.isdir(WORK):
        shutil.rmtree(WORK)
    os.makedirs(WORK)
    files = sorted(collect())
    fixed = missing = 0
    used = {}
    for fn in files:
        p = os.path.join(SRC, fn)
        raw = bytearray(io.open(p, 'rb').read())
        meta = parse(p)
        ext = [os.path.basename(e) for e in meta['externals']]
        doff = meta['data_offset']
        for o in meta['objects']:
            if o['class_id'] != 114 or o['size'] < 20:
                continue
            at = doff + o['start'] + 12
            fid, pid = struct.unpack_from('<ii', raw, at)
            if not fid or ext[fid - 1] != S0:
                continue
            nm = theirs.get(pid)
            used[nm] = used.get(nm, 0) + 1
            if pid in smap:
                struct.pack_into('<ii', raw, at, fid, smap[pid])
                fixed += 1
            else:
                missing += 1
        io.open(os.path.join(WORK, fn), 'wb').write(bytes(raw))
    say('  원본 %d개를 뜨고 스크립트 참조 %d개를 우리 번호로 고쳤습니다'
        % (len(files), fixed))
    if missing:
        raise SystemExit('우리 빌드에 없는 스크립트를 가리키는 곳 %d군데' % missing)
    say('  쓰는 스크립트: %s'
        % ' · '.join('%s %d' % (k, v) for k, v in sorted(used.items())))
    return files


# 스크립트가 들고 있는 PPtr 자리. MonoBehaviour 는 타입트리가 없어 엔진도
# 우리도 필드를 바이트로 세야 한다. 머리 24바이트(오브젝트 8 · 켜짐 4 ·
# 스크립트 8 · 이름 4) 뒤가 본문이다. 실측으로 여섯 갈래 중 둘만 참조를 든다.
#
#   JumpLanding            +24 landingClip · +32 stepClip   (AudioClip)
#   ChangeTextureMaterial  +32 개수, 그 뒤로 Material 배열
#
# EffectManager 는 자리가 다 0 이다 — `Car/{0}/{0}_Effect` 를 실행 중에 찾아
# 채운다. CarDataLinker · BaseData · PlayerCarData 는 값만 든다.
def mb_sites(path, names):
    """[(pathID, 바이트오프셋)] — 이 파일 안 스크립트가 든 PPtr 자리."""
    from sfparse import parse
    meta = parse(path)
    raw = io.open(path, 'rb').read()
    ext = [os.path.basename(e) for e in meta['externals']]
    out = []
    for o in meta['objects']:
        if o['class_id'] != 114 or o['size'] < 24:
            continue
        b = raw[meta['data_offset'] + o['start']:][:o['size']]
        fid, pid = struct.unpack_from('<ii', b, 12)
        cls = names.get(pid) if (not fid or ext[fid - 1] == S0) else None
        if cls == 'JumpLanding':
            offs = [24, 32]
        elif cls == 'ChangeTextureMaterial':
            n = struct.unpack_from('<i', b, 32)[0]
            if 36 + 8 * n != len(b):
                raise SystemExit('%s pathID %d: Material 배열이 안 맞습니다'
                                 % (os.path.basename(path), o['path_id']))
            offs = [36 + 8 * i for i in range(n)]
        else:
            continue
        for i in offs:
            if struct.unpack_from('<ii', b, i) != (0, 0):
                out.append((o['path_id'], i))
    return out


def ourscripts():
    return dict((p, n) for p, n in
                script_map(joined(os.path.join(XD, S0))).items())


def specs():
    """sfmerge 스펙 줄. 한 파일에 이름이 여럿이면 also= 로 잇는다."""
    names = ourscripts()
    out = []
    for fn, ents in sorted(collect().items()):
        ents = sorted(ents)
        p = os.path.join(WORK, fn)
        # 스펙은 ':' 로 가르므로 윈도우 드라이브 문자가 들어가면 안 된다.
        line = '%s:%s:%d:0:keepscript' % (os.path.relpath(p, os.getcwd()),
                                          ents[0][0], ents[0][1])
        for nm, pid in ents[1:]:
            line += ':also=%s@%d' % (nm, pid)
        for pid, off in mb_sites(p, names):
            line += ':mbptr=%d@%d' % (pid, off)
        out.append(line)
    return out


# ------------------------------------------------------------ 헬리 물러나기
# 공여판 헬리에 딸려 온 로보카 소리들. **정식 5.1.0 에는 없다**(그 판은
# 소리를 다른 자리에 둔다). 변신 차의 전용 BGM 이 이 안에 있어서 물리면
# 안 된다 — `patch/robotbgm.cs` 가 `Car/Helly/Sound/Roboca_BGM` 을 찾는다.
KEEP = 'car/helly/sound/'


def retire_helly(say):
    """지금 번들의 `car/helly/*` 를 개명하고 매니페스트에서 뺀다."""
    import packadd
    sf = _sf(PACKDAT)
    man = [o for o in sf.objects.values() if o.type.name == 'AssetBundle'][0]
    tree = man.read_typetree()
    hit = [c for c in tree['m_Container']
           if c[0].startswith('car/helly/') and not c[0].startswith(KEEP)]
    if not hit:
        say('  물러날 공여판 헬리가 없습니다')
        return
    pids = set(c[1]['asset']['m_PathID'] for c in hit)
    blobs = {}
    for pid in sorted(pids):
        o = sf.objects.get(pid)
        if o is None or o.type.name == 'MonoBehaviour':
            continue
        t = o.read_typetree()
        if not t.get('m_Name', '').startswith('old_'):
            t['m_Name'] = 'old_' + t['m_Name']
            blobs[pid] = bytes(o.save_typetree(t))
    tree['m_Container'] = [c for c in tree['m_Container']
                           if not c[0].startswith('car/helly/')
                           or c[0].startswith(KEEP)]
    blobs[man.path_id] = bytes(man.save_typetree(tree))
    say('  공여판 헬리 %d개를 old_ 로 물리고 색인 %d줄을 뺐습니다'
        ' (로보카 소리 %d줄은 그대로 둡니다)'
        % (len(blobs) - 1, len(hit),
           len([c for c in tree['m_Container'] if c[0].startswith(KEEP)])))
    packadd.replace(PACKDAT, blobs, say)


# ------------------------------------------------------------ 이름 가림 풀기
#
# 번들은 오브젝트를 **이름으로** 찾는다. `Generic_Title.__ChaFromBundle` 이
# `bundle.LoadAll()` 을 훑어 `obj.name.ToLower()` 를 열쇠로 표를 짜는데,
# 열쇠가 겹치면 **나중 것이 이긴다.** GameObject 를 마지막에 훑으므로
# GameObject 가 늘 이긴다.
#
# FBX 하나에서 나온 GameObject · Mesh · Texture2D · Material 은 **이름이 다
# 같다.** 그래서 `Car/Poli/Materials/Poli` 를 찾으면 재질이 아니라 프리팹 속
# GameObject 가 나온다. 실측: 재질 조회 36개 중 34개가 가려져 있었다.
# (트로이 때도 같은 함정을 만나 안쪽 GameObject 를 `Troy_Body` 로 고쳤다.)
#
# 게임이 이름으로 찾는 것은 다음뿐이다.
#
#     Car/{0}/Player_{0}_{1}    프리팹        Car/{0}/{0}_Effect      효과
#     Car/{0}/Materials/{1}     재질          Car/{0}/{0}@{1}         동작
#
# 이 자리만 지켜 주면 되므로, 같은 이름을 든 **다른** 오브젝트에 `_` 를 붙여
# 비켜 세운다. 그것들은 전부 PPtr 로만 참조되므로 이름이 바뀌어도 그만이다.
def _wanted(cont, kindof):
    """{찾을 이름: 나와야 하는 pathID} — car/ 색인에서 뽑는다.

    한 이름을 색인 두 줄이 다투는 일이 잦다. FBX 를 들여올 때 애니메이션
    클립과 그 뿌리 GameObject 가 **같은 이름**을 받기 때문이다
    (`Helly@Race` 가 클립이자 GameObject 다). 게임이 그 자리에서 무엇을
    기대하는지는 IL 로 확인했다(`cdump il CarDataLinker::Update`).

        Car/{0}/{0}@{1}          isinst GameObject
        Car/{0}/{0}_robot@{1}    isinst GameObject
        Car/{0}/Materials/…      isinst Material   ← 어긋나면 sharedMaterial 이
        Car/{0}/Player_{0}_{1}   isinst GameObject    null 이 되어 차가 안 보인다
        Car/{0}/{0}_Effect       isinst GameObject

    `Car/{0}/{1}`(맨이름 클립)은 `carName == "helly"` 일 때만 타는 가지인데,
    정품 프리팹의 `carName` 은 전부 숫자(CarIndex)라 걸리지 않는다. 그래서
    `race` · `damage` · `jump` 같은 맨이름은 다투게 두고 안 건드린다."""
    out, clash = {}, set()
    for k, pid in cont:
        if not k.startswith('car/'):
            continue
        seg = k.rsplit('/', 1)[-1]
        part = k.split('/')
        if len(part) > 3 and part[2] == 'materials':
            kind = 'Material'
        elif '@' in seg or seg.startswith('player_') or seg.endswith('_effect'):
            kind = 'GameObject'
        else:
            continue
        if kindof.get(pid) != kind:
            continue                                   # 갈래가 다르면 아니다
        if seg in out and out[seg] != pid:
            clash.add(seg)
        out[seg] = pid
    for seg in clash:
        out.pop(seg, None)
    return out, clash


def unshadow(say):
    import packadd
    sf = _sf(PACKDAT)
    man = [o for o in sf.objects.values() if o.type.name == 'AssetBundle'][0]
    cont = [(c[0], c[1]['asset']['m_PathID']) for c in
            man.read_typetree()['m_Container']]
    want, clash = _wanted(cont, dict((p, o.type.name)
                                     for p, o in sf.objects.items()))
    trees, names = {}, {}
    for pid, o in sf.objects.items():
        if o.type.name == 'MonoBehaviour':
            continue
        try:
            t = o.read_typetree()
        except Exception:
            continue
        n = t.get('m_Name')
        if n:
            trees[pid], names[pid] = t, n
    byname = {}
    for pid, n in names.items():
        byname.setdefault(n.lower(), []).append(pid)
    blobs = {}
    for seg, pid in sorted(want.items()):
        if pid not in names:
            continue
        for other in byname.get(seg, []):
            if other == pid or names[other].startswith('_'):
                continue
            t = trees[other]
            t['m_Name'] = '_' + t['m_Name']
            blobs[other] = bytes(sf.objects[other].save_typetree(t))
    say('  이름 조회 %d자리 · 비켜 세운 오브젝트 %d개%s'
        % (len(want), len(blobs),
           ' · 가릴 수 없는 이름 %d개' % len(clash) if clash else ''))
    if clash:
        say('    (%s — 게임이 이 이름으로 찾지 않으므로 둔다)'
            % ' '.join(sorted(clash)[:8]))
    if blobs:
        packadd.replace(PACKDAT, blobs, say)


# ------------------------------------------------------------ 번들
def build(say):
    import sfmerge
    import packadd
    restamp(say)
    sp = specs()
    say('자산 %d개를 하나로 합칩니다…' % len(sp))
    ents = sfmerge.merge(OUT, 'pack.dat', sp, nomanifest=True)
    say('  %s %.1f MB · 색인 %d줄'
        % (os.path.basename(OUT), os.path.getsize(OUT) / 1048576.0, len(ents)))
    import bundlechain
    bundlechain.start(STAGE, say)
    retire_helly(say)
    say('번들에 얹습니다…')
    line = ['%s:%d' % (n, p) for n, p in ents]
    line[0] += ':keepscript'
    for pid, off in mb_sites(OUT, ourscripts()):
        line[0] += ':mbptr=%d@%d' % (pid, off)
    packadd.add(OUT, line, say)
    unshadow(say)
    packadd.wrap(say)
    bundlechain.done(STAGE, say)


# ------------------------------------------------------------ 차 표
def _textasset(raw, meta, pid=1):
    rec = [o for o in meta['objects'] if o['path_id'] == pid][0]
    st = meta['data_offset'] + rec['start']
    n = struct.unpack_from('<i', raw, st)[0]
    off = 4 + n
    off += (-off) % 4
    tlen = struct.unpack_from('<i', raw, st + off)[0]
    return st, off, tlen


def _arr(text):
    return json.loads(text)['CarDataBase']['CarInfoDB']['CarDataArray']


def write_cardb(say):
    """정식판 표를 통째로 옮겨 적는다. 트로이 자리로 빈칸을 남긴다."""
    from sfedit import replace_object
    from sfparse import parse
    import cardb
    _fn, text = cardb.find(V510, 'CarInfoDB')
    j = text.index('[', text.index('"CarDataArray":')) + 1
    text = text[:j] + ' ' * PAD + text[j:]
    raw = bytearray(io.open(CARDB, 'rb').read())
    meta = parse(CARDB)
    st, off, tlen = _textasset(raw, meta)
    was = len(_arr(bytes(raw[st + off + 4:st + off + 4 + tlen]).decode('utf-8')))
    rec = [o for o in meta['objects'] if o['path_id'] == 1][0]
    b = text.encode('utf-8')
    blob = (bytes(raw[st:st + off]) + struct.pack('<i', len(b)) + b
            + b'\0' * ((-len(b)) % 4))
    replace_object(CARDB, 1, blob)
    say('CarDataBase: %d대 → %d대 (빈칸 %d바이트) · %d → %d바이트'
        % (was, len(_arr(text)), PAD, rec['size'], len(blob)))


def _items(body):
    """맨 바깥 쉼표로만 가른다. `CAR_COST` 의 값은 `(0, 15)` 라 안쪽에
    쉼표가 또 있다 — 그냥 `split(',')` 하면 표가 부서진다."""
    out, depth, cur = [], 0, ''
    for ch in body:
        if ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth -= 1
        if ch == ',' and depth == 0:
            out.append(cur)
            cur = ''
        else:
            cur += ch
    out.append(cur)
    return [x.strip() for x in out if x.strip()]


def _edit(s, var, pairs, isset=False):
    """한 줄짜리 dict/set 리터럴에서 항목을 더하거나 뺀다."""
    i = s.index('\n%s = {' % var)
    lo = i + s[i:].index('{') + 1
    hi = s.index('}', lo)
    cur, order = {}, []
    for x in _items(s[lo:hi]):
        k = x if isset else x.split(':')[0].strip()
        if k not in cur:
            order.append(k)
        cur[k] = x
    for k, v in pairs:
        k = str(k)
        if v is None:
            cur.pop(k, None)
            if k in order:
                order.remove(k)
        else:
            if k not in cur:
                order.append(k)
            cur[k] = v
    return s[:lo] + ', '.join(cur[k] for k in order) + s[hi:]


def patch_cars_table(say):
    """`chastate.py` 의 `CARS` 를 **차 표에서 떠서** 다시 적는다.

    이 표는 서버가 carNo ↔ 차 이름을 옮기는 데 쓰고, `mkskel.py` 가 로컬
    APK 용 `ChaLocalData.cs` 로 구워 넣는다. 세이브의 `carsOwned` 도 이
    이름을 쓴다. 차 표(CarDataBase)와 어긋나면 **그 차가 자동차 샵에 아예
    안 나온다** — 실기에서 폴리 하나가 그렇게 빠졌다(carNo 18 이 아직
    헬리로 적혀 있었다).

    그래서 손으로 맞추지 않고 우리가 싣는 CarDataBase 에서 뜬다."""
    import cardb
    arr = sorted(cardb.cars(os.path.join(HERE, 'x77')),
                 key=lambda c: c['CarIndex'])
    rows = [(c['CarIndex'] + 1, c['CarName'], c['StartCarClassType'])
            for c in arr]
    body = []
    line = '   '
    for no, nm, cl in rows:
        piece = ' (%d, "%s", "%s"),' % (no, nm, cl)
        if len(line) + len(piece) > 76:
            body.append(line)
            line = '   '
        line += piece
    body.append(line)
    nl = chr(10)
    txt = ('CARS = [' + nl
           + nl.join(x.rstrip() for x in body) + nl + ']')
    p = os.path.join(CODE, 'chastate.py')
    s = io.open(p, encoding='utf-8').read()
    i = s.index(nl + 'CARS = [')
    j = s.index(nl + ']', i) + 2
    if s[i + 1:j] == txt:
        say('chastate.py 의 차 표는 이미 맞습니다')
        return
    io.open(p, 'w', encoding='utf-8', newline='').write(
        s[:i + 1] + txt + s[j:])
    say('chastate.py: 차 표를 %d대로 다시 적었습니다 (CarDataBase 에서 뜸)'
        % len(rows))


def patch_server(say, undo=False):
    """사설 서버 표를 정식판 값으로 맞춘다 (carNo = CarIndex + 1)."""
    import cardb
    arr = dict((c['CarName'], c) for c in cardb.cars(V510))
    s = orig = io.open(SERVER, encoding='utf-8').read()
    cls, cost, shop = [], [], []
    for nm in CARS:
        c = arr[nm]
        no = c['CarIndex'] + 1
        cls.append((no, None if undo else '%d: "%s"'
                    % (no, c['StartCarClassType'])))
        cost.append((no, None if undo else '%d: (%d, %d)'
                     % (no, c['CostGold'], c['UnlockTrophy'])))
        shop.append((no, None if undo else '%d' % no))
    # 트로이가 로이의 번호(19)를 쓰고 있었다. 정품이 자리를 되찾는다.
    if not undo:
        for var in ('CAR_CLASS', 'CAR_COST'):
            s = _edit(s, var, [(19, None)])
        s = _edit(s, 'SHOP_CARS', [(19, None)], isset=True)
    s = _edit(s, 'CAR_CLASS', cls)
    s = _edit(s, 'CAR_COST', cost)
    s = _edit(s, 'SHOP_CARS', shop, isset=True)
    if s != orig:
        io.open(SERVER, 'w', encoding='utf-8', newline='').write(s)
        say('서버 표: carNo %s 를 %s'
            % (' '.join(str(arr[n]['CarIndex'] + 1) for n in CARS),
               '뺐습니다' if undo else '맞췄습니다'))
    else:
        say('서버 표는 이미 맞습니다')
    if not undo:
        patch_cars_table(say)
    if undo or not os.path.exists(NEWCARS):
        return
    left = [c for c in json.load(io.open(NEWCARS, encoding='utf-8'))
            if c['name'] != 'Troy']
    if left:
        io.open(NEWCARS, 'w', encoding='utf-8').write(
            json.dumps(left, ensure_ascii=False, indent=1))
    else:
        os.remove(NEWCARS)
    say('newcars.json 에서 트로이를 뺐습니다 (나중에 다시 넣습니다)')


# ------------------------------------------------------------ 보기
def scan(say=print):
    import cardb
    if not os.path.isdir(SRC):
        say('5.1.0 트리가 없습니다: %s' % SRC)
        return 1
    ent = collect()
    say('가져올 자산 파일 %d개 · 색인 %d줄'
        % (len(ent), sum(len(v) for v in ent.values())))
    smap, theirs = remap()
    say('스크립트 이름표: 5.1.0 %d개 중 우리와 이름이 겹치는 것 %d개'
        % (len(theirs), len(smap)))
    A = dict((c['CarName'], c) for c in cardb.cars('x77'))
    B = dict((c['CarName'], c) for c in cardb.cars(V510))
    say('')
    say('차 표 %d대 → %d대' % (len(A), len(B)))
    for nm in CARS:
        c, was = B[nm], A.get(nm)
        say('  %-10s CarIndex %-2d 서버 carNo %-2d %s급 트로피 %-3d %s'
            % (nm, c['CarIndex'], c['CarIndex'] + 1,
               c['StartCarClassType'], c['UnlockTrophy'],
               '(지금 %d번)' % was['CarIndex'] if was else '(새로)'))
    say('')
    say('값이 달라지는 기존 차: %s'
        % ', '.join(nm for nm in sorted(set(A) & set(B))
                    if json.dumps(A[nm], sort_keys=True)
                    != json.dumps(B[nm], sort_keys=True)))
    say('빠지는 차: %s' % ', '.join(sorted(set(A) - set(B))))
    return 0


def add(say=print):
    build(say)
    write_cardb(say)
    patch_server(say)
    say('')
    say('정품 차 8대를 넣었습니다. 트로이는 빠졌습니다 — 안정된 뒤 다시 넣으세요.')
    say('이제 APK 를 다시 만드세요.')
    return 0


def remove(say=print):
    import bundlechain
    bundlechain.start(STAGE, say)
    bundlechain.done(STAGE, say)
    patch_server(say, undo=True)
    if os.path.exists(OUT):
        os.remove(OUT)
    say('차 표는 x77 트리를 손수 되돌리세요.')
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scan', action='store_true')
    ap.add_argument('--remove', action='store_true')
    a = ap.parse_args()
    if a.scan:
        return scan()
    if a.remove:
        return remove()
    return add()


if __name__ == '__main__':
    sys.exit(main())
