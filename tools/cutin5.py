# -*- coding: utf-8 -*-
"""빠져 있던 **컷인 그림 열 장**을 5.1.0 에서 옮겨 온다.

주행 중 콤보를 이으면 운전자 얼굴이 큰 판으로 번쩍 지나간다(컷인). 그런데
지금 빌드에는 그 그림이 **넉 장뿐**이다.

    우리 Atlas_Cutin     PtCutinC1 ~ C4    (넷)
    5.1.0               PtCutinC1 ~ C14   (열넷)

`Cutin::SetCutin(type)` 은 `driverCutin[type]` 하나만 켜고 나머지를 끈다.
우리 배열이 넷이라 **갈래 4~11 은 아무것도 안 켜진다.** 실기로 확인했다 —
정신이(ROPE=11)를 끼고 달리니 배경과 속도선만 뜨고 얼굴 자리가 **하얀 판**
으로 남았다.

## 어느 그림이 누구인가

이름꼴이 곧 번호는 아니다. 5.1.0 의 `driverCutin` 배열을 그대로 읽었다.

    0 DOKANG  → C2      4 PIG    → C5     8  ROI      → C9
    1 SARA    → C1      5 GYARU  → C6     9  HELLY    → C10
    2 BIN     → C3      6 POLY   → C7     10 ANGRY    → C11
    3 NAYOUBI → C4      7 AMBER  → C8     11 ROPE     → C12
                                          12 NAJUNGBI → C13
                                          13 AHNBYULE → C14

앞의 넷은 우리 것과 짝이 이미 맞는다. 나머지 열 장을 가져온다. 13 · 14 번은
드라이버가 아직 없어 안 켜지지만, 나중에 붙일 때 또 프리팹을 째지 않도록
같이 넣고 배열도 열넷으로 늘려 둔다.

## 판을 다시 짠다 — 우리 것은 2배, 새 것은 원본 크기

우리 넉 장은 한국 초기판의 **진짜 2배 원화**에서 왔다(494x192, `docs/HIRES.md`).
5.1.0 것은 1배(247x96)다. 늘려 봐야 없는 결이 생기지는 않으므로 **원본 크기
그대로** 넣는다. NGUI 의 `Simple` 스프라이트는 위젯 트랜스폼 크기로 그리므로
(실측: 이 컷인들은 전부 `mType=0`), 조각이 작아도 화면에서는 같은 크기로
나온다 — 정식판이 보여 주던 것과 똑같이 보이고, 우리 넉 장만 더 또렷하다.

열일곱 장을 1024x1024 에 다시 담기엔 빠듯하다(80%). **2048x512** 로 다시
담으면 넉넉히 들어가면서 넓이가 같아 **텍스처 바이트 수가 그대로**다 —
`sharedassets1.assets` 도 안 커지고 조각(`.splitN`) 수도 그대로다.

## 차례

`hires.py` 가 이 파일(`sharedassets1.assets`)을 이미 손댔다. 그쪽은
`backup/hires` 에서 되살려 처음부터 다시 짓기 때문에, 이 도구는 **hires 뒤**에
돌아야 하고 자기 원본은 `backup/cutin` 에 따로 남긴다.

    python tools/cutin5.py --scan     무엇을 가져오나
    python tools/cutin5.py            넣는다
    python tools/cutin5.py --restore  backup/cutin 에서 되돌린다
"""
import argparse
import io
import os
import shutil
import struct
import sys

CODE = os.path.dirname(os.path.abspath(__file__))
HERE = os.path.dirname(CODE)
sys.path.insert(0, CODE)

import uiatlas                                          # noqa: E402

XD = os.path.join(HERE, 'x77', 'assets', 'bin', 'Data')
SRC = os.path.join(HERE, '_scratch', 'v5', 'v510', 'assets', 'bin', 'Data')
BAK = os.path.join(HERE, 'backup', 'cutin')

SA1 = 'sharedassets1.assets'
LEVEL = 'level0'
CUTIN_PID = 923                 # level0 안 Cutin(MonoBehaviour)
PARENT_TR = 487                 # 컷인 스프라이트들의 부모 Transform
SAMPLE = (214, 567, 1027)       # 본뜰 (GameObject, Transform, UISprite)

# 담아 볼 판 크기. 앞에서부터 되는 것을 쓴다. 2048x512 는 지금 판(1024x1024)
# 과 **넓이가 같아** 텍스처 바이트 수가 한 자리도 안 바뀐다.
SHEETS = ((2048, 512), (2048, 1024))
GAP = 2

# 열거자 차례대로의 조각 이름. 5.1.0 의 `driverCutin` 을 그대로 읽은 것이다.
ORDER = ['PtCutinC2', 'PtCutinC1', 'PtCutinC3', 'PtCutinC4',
         'PtCutinC5', 'PtCutinC6', 'PtCutinC7', 'PtCutinC8',
         'PtCutinC9', 'PtCutinC10', 'PtCutinC11', 'PtCutinC12',
         'PtCutinC13', 'PtCutinC14']
WHO = ['DOKANG', 'SARA', 'BIN', 'NAYOUBI', 'PIG', 'GYARU', 'POLY', 'AMBER',
       'ROI', 'HELLY', 'ANGRY', 'ROPE', 'NAJUNGBI', 'AHNBYULE']

# UISprite 의 `mSpriteName` 자리. 머리 24 + UIWidget 필드 48 = 72.
SPRNAME_OFF = 72


def _raw(path, pid):
    from UnityPy.streams import EndianBinaryReader
    from UnityPy.files.SerializedFile import SerializedFile
    sf = SerializedFile(EndianBinaryReader(io.open(path, 'rb').read()), None)
    return bytearray(sf.objects[pid].get_raw_data())


def find_atlas(path, name='Atlas_Cutin'):
    """(아틀라스 pathID, 텍스처 pathID) — 이름으로 찾는다."""
    import UnityPy
    env = UnityPy.load(path)
    go = {}
    for o in env.objects:
        if o.type.name == 'GameObject':
            try:
                go[o.path_id] = o.read_typetree()['m_Name']
            except Exception:
                pass
    atlas = tex = None
    for o in env.objects:
        if o.type.name == 'Texture2D':
            try:
                if o.read_typetree()['m_Name'] == name:
                    tex = o.path_id
            except Exception:
                pass
        elif o.type.name == 'MonoBehaviour':
            try:
                b = bytes(o.get_raw_data())
            except Exception:
                continue
            if len(b) < 200 or len(uiatlas.table(b)) < 4:
                continue
            if go.get(struct.unpack_from('<ii', b, 0)[1]) == name:
                atlas = o.path_id
    if atlas is None or tex is None:
        raise SystemExit('%s 에서 %s 를 못 찾았습니다' % (os.path.basename(path), name))
    return atlas, tex


def _sheet(path, name='Atlas_Cutin'):
    """(조각표, 판 그림, 아틀라스 pathID, 텍스처 pathID)"""
    import UnityPy
    apid, tpid = find_atlas(path, name)
    env = UnityPy.load(path)
    tex = [o for o in env.objects if o.path_id == tpid][0]
    return (uiatlas.table(bytes(_raw(path, apid))),
            tex.read().image.convert('RGBA'), apid, tpid)


def _base(fn):
    """손대기 전 파일. 한 번 바꾼 뒤에도 늘 원본에서 다시 짓는다."""
    b = os.path.join(BAK, fn)
    return b if os.path.exists(b) else os.path.join(XD, fn)


def plan(say=lambda *a: None):
    """새 판 그림과 {이름: (x, y, w, h)} 를 만든다."""
    from PIL import Image
    ours, osheet, _a, _t = _sheet(_base(SA1))
    theirs, tsheet, _a2, _t2 = _sheet(os.path.join(SRC, SA1))
    missing = [n for n in ORDER if n not in ours]
    have = [n for n in ours if n not in ORDER]          # Bg · Fx1 · Fx2
    pieces = []
    for nm in have + [n for n in ORDER if n in ours] + missing:
        if nm in ours:
            x, y, w, h = (int(round(v)) for v in ours[nm][1])
            pieces.append((nm, osheet.crop((x, y, x + w, y + h))))
        else:
            if nm not in theirs:
                raise SystemExit('5.1.0 에도 %s 가 없습니다' % nm)
            x, y, w, h = (int(round(v)) for v in theirs[nm][1])
            pieces.append((nm, tsheet.crop((x, y, x + w, y + h))))
    # 선반 담기 — 키 큰 것부터. 좌표는 4의 배수(DXT 칸 경계)로 맞춘다.
    pieces.sort(key=lambda p: (-p[1].height, -p[1].width))
    for sheet in SHEETS:
        rect = {}
        x = y = row = 0
        ok = True
        for nm, im in pieces:
            if x + im.width > sheet[0]:
                x = 0
                y = (y + row + GAP + 3) & ~3
                row = 0
            if y + im.height > sheet[1]:
                ok = False
                break
            rect[nm] = (x, y, im.width, im.height)
            x = (x + im.width + GAP + 3) & ~3
            row = max(row, im.height)
        if ok:
            break
    else:
        raise SystemExit('어느 판에도 안 들어갑니다')
    out = Image.new('RGBA', sheet, (0, 0, 0, 0))
    for nm, im in pieces:
        out.alpha_composite(im, rect[nm][:2])
    say('  조각 %d개 → %dx%d 판 (새로 온 것 %d개: %s)'
        % (len(pieces), sheet[0], sheet[1], len(missing),
           ' '.join(n[7:] for n in missing)))
    return out, rect, missing


# ------------------------------------------------------------------ 아틀라스
def _record(name, x, y, w, h, size):
    b = struct.pack('<i', len(name)) + name.encode('utf-8')
    b += b'\0' * ((-len(b)) % 4)
    b += struct.pack('<4f', x, y, w, h)          # outer
    b += struct.pack('<4f', x, y, w, h)          # inner
    b += struct.pack('<%di' % ((size - 32) // 4), *([0] * ((size - 32) // 4)))
    return b


def write_atlas(sheet, rect, say=print):
    import UnityPy
    from UnityPy.enums import TextureFormat
    from UnityPy.export import Texture2DConverter as T2C
    from sfparse import parse
    from sfedit import replace_object

    p = os.path.join(XD, SA1)
    apid, tpid = find_atlas(p)

    # --- 텍스처 ---
    env = UnityPy.load(p)
    o = [q for q in env.objects if q.path_id == tpid][0]
    t = dict(o.read_typetree())
    fmt = TextureFormat(int(t['m_TextureFormat']))
    blob, _f = T2C.image_to_texture2d(sheet, fmt)
    was = [q for q in parse(p)['objects'] if q['path_id'] == tpid][0]['size']
    t.update({'m_Width': sheet.width, 'm_Height': sheet.height,
              'm_CompleteImageSize': len(blob), 'image data': bytes(blob)})
    new = bytes(o.save_typetree(t))
    replace_object(p, tpid, new)
    say('  텍스처 %dx%d %s · %d → %d바이트'
        % (sheet.width, sheet.height, fmt.name, was, len(new)))

    # --- 조각표: 있는 것은 자리만 고치고, 없는 것은 뒤에 더한다 ---
    d = _raw(p, apid)
    size = uiatlas.layout(bytes(d))
    if size is None:
        raise SystemExit('아틀라스 레코드 길이를 못 읽었습니다')
    for nm, _no, off in uiatlas.records(bytes(d), size):
        if nm not in rect:
            continue
        x, y, w, h = rect[nm]
        _o, _i, ints = uiatlas.payload(bytes(d), off, size)
        uiatlas.set_payload(d, off, (x, y, w, h), (x, y, w, h), ints)
    have = set(uiatlas.table(bytes(d)))
    add = [n for n in ORDER if n not in have]
    if add:
        extra = b''.join(_record(n, *rect[n], size=size) for n in add)
        n0 = struct.unpack_from('<i', d, uiatlas.HDR_COUNT)[0]
        end = len(d) - uiatlas.TAIL      # 배열 뒤 꼬리 16바이트 **앞**에 넣는다
        d = d[:end] + extra + d[end:]
        struct.pack_into('<i', d, uiatlas.HDR_COUNT, n0 + len(add))
        say('  조각표 %d → %d개' % (n0, n0 + len(add)))
    replace_object(p, apid, bytes(d))
    return p


# ------------------------------------------------------------------ 프리팹
def _write_serialized(path, meta, objs, say):
    """오브젝트 표를 통째로 다시 적는다. objs = [(pathID, class_id, bytes)]"""
    data = bytearray()
    recs = []
    for pid, cid, blob in objs:
        while len(data) % 8:
            data.append(0)
        recs.append((pid, len(data), len(blob), cid))
        data += blob
    m = meta['unity'].encode('utf-8') + b'\0'
    m += struct.pack('<i', meta['platform'])
    m += struct.pack('<i', 0)
    m += struct.pack('<i', meta['big_id'])
    m += struct.pack('<i', len(recs))
    # 오브젝트 표는 **pathID 오름차순**이어야 한다. 자료 순서대로 적었더니
    # 레이스 장면(level0)을 읽다가 앱이 그냥 죽었다(실기). 원본 파일도 전부
    # 오름차순으로 적혀 있다 — 엔진이 이 표를 훑어 찾는 듯하다.
    for pid, st, sz, cid in sorted(recs):
        m += struct.pack('<iIIiHh', pid, st, sz, cid, cid, 0)
    ext = [os.path.basename(e) for e in meta['externals']]
    m += struct.pack('<i', len(ext))
    for nm in ext:
        m += b'\0' + b'\0' * 16 + struct.pack('<i', 0) + nm.encode('utf-8') + b'\0'
    m += b'\0'
    doff = max(meta['data_offset'], (20 + len(m) + 64 + 15) & ~15)
    head = struct.pack('>IIII', len(m), doff + len(data), 9, doff)
    head += bytes([1 if meta['endian'] == '>' else 0, 0, 0, 0])
    out = bytearray(head + m)
    while len(out) < doff:
        out += b'\0'
    out += data
    io.open(path, 'wb').write(bytes(out))
    say('  %s 오브젝트 %d개 · %d바이트'
        % (os.path.basename(path), len(recs), len(out)))


def write_prefab(say=print):
    """컷인 스프라이트를 열넷으로 늘리고 `driverCutin` 을 다시 적는다."""
    import UnityPy
    from sfparse import parse

    p = os.path.join(XD, LEVEL)
    src = _base(LEVEL)
    if src != p:
        shutil.copy2(src, p)
    meta = parse(p)
    raw = io.open(p, 'rb').read()
    env = UnityPy.load(p)
    objs = {o.path_id: o for o in env.objects}
    recs = dict((o['path_id'], o) for o in meta['objects'])

    def blob(pid):
        r = recs[pid]
        return bytearray(raw[meta['data_offset'] + r['start']:][:r['size']])

    cut = blob(CUTIN_PID)
    n = struct.unpack_from('<i', cut, 24)[0]
    cur = [struct.unpack_from('<ii', cut, 28 + 8 * i)[1] for i in range(n)]
    byname = {}
    for pid in cur:
        b = blob(pid)
        ln = struct.unpack_from('<i', b, SPRNAME_OFF)[0]
        byname[bytes(b[SPRNAME_OFF + 4:SPRNAME_OFF + 4 + ln]).decode()] = pid
    need = [nm for nm in ORDER if nm not in byname]
    if not need:
        say('  컷인 스프라이트가 이미 다 있습니다')
        return
    say('  스프라이트 %d개를 프리팹에 더합니다: %s'
        % (len(need), ' '.join(x[7:] for x in need)))

    gid, tid, sid = SAMPLE
    gblob, tblob, sblob = blob(gid), blob(tid), blob(sid)
    nxt = max(recs) + 1
    new = []
    for nm in need:
        ng, nt, ns = nxt, nxt + 1, nxt + 2
        nxt += 3
        # GameObject — 이름과 컴포넌트 참조를 새 번호로
        g = objs[gid].read_typetree()
        g['m_Name'] = 'Sprite (%s)' % nm
        for c in g['m_Component']:
            cid = recs[c[1]['m_PathID']]['class_id']
            c[1]['m_PathID'] = nt if cid == 4 else ns
        new.append((ng, 1, bytes(objs[gid].save_typetree(g))))
        # Transform — 같은 부모 · 같은 자리
        t = objs[tid].read_typetree()
        t['m_GameObject']['m_PathID'] = ng
        t['m_Children'] = []
        new.append((nt, 4, bytes(objs[tid].save_typetree(t))))
        # UISprite — 타입트리가 없다. 오브젝트 참조와 조각 이름만 갈아 끼운다.
        b = bytearray(sblob)
        struct.pack_into('<ii', b, 0, 0, ng)
        b[8] = 0                                   # 꺼 둔다. SetCutin 이 켠다.
        ln = struct.unpack_from('<i', b, SPRNAME_OFF)[0]
        end = SPRNAME_OFF + 4 + ln + ((-ln) % 4)
        nb = nm.encode('utf-8')
        mid = struct.pack('<i', len(nb)) + nb + b'\0' * ((-len(nb)) % 4)
        b = b[:SPRNAME_OFF] + mid + b[end:]
        new.append((ns, 114, bytes(b)))
        byname[nm] = ns

    # 부모 Transform 에 자식으로 단다
    f = objs[PARENT_TR].read_typetree()
    f['m_Children'] += [{'m_FileID': 0, 'm_PathID': pid}
                        for pid, cid, _b in new if cid == 4]
    fblob = bytes(objs[PARENT_TR].save_typetree(f))

    # driverCutin 을 열넷으로
    arr = b''.join(struct.pack('<ii', 0, byname[nm]) for nm in ORDER)
    head = bytes(cut[:24]) + struct.pack('<i', len(ORDER))
    tail = bytes(cut[28 + 8 * n:])
    cutnew = head + arr + tail

    out = []
    for o in sorted(meta['objects'], key=lambda x: x['start']):
        pid = o['path_id']
        if pid == CUTIN_PID:
            b = cutnew
        elif pid == PARENT_TR:
            b = fblob
        else:
            b = raw[meta['data_offset'] + o['start']:][:o['size']]
        out.append((pid, o['class_id'], bytes(b)))
    out += [(pid, cid, b) for pid, cid, b in new]
    _write_serialized(p, meta, out, say)
    say('  driverCutin %d → %d칸 (%s)'
        % (n, len(ORDER), ' '.join(WHO[:len(ORDER)])))


# ------------------------------------------------------------------ 손잡이
def baseline(say):
    os.makedirs(BAK, exist_ok=True)
    keep = [SA1, LEVEL] + [f for f in os.listdir(XD)
                           if f.startswith(SA1 + '.split')]
    fresh = not os.path.exists(os.path.join(BAK, SA1))
    if fresh:
        for f in keep:
            shutil.copy2(os.path.join(XD, f), os.path.join(BAK, f))
        say('원본을 backup/cutin 에 남겼습니다 (%d개)' % len(keep))
    else:
        for f in os.listdir(XD):
            if f.startswith(SA1 + '.split'):
                os.remove(os.path.join(XD, f))
        for f in os.listdir(BAK):
            shutil.copy2(os.path.join(BAK, f), os.path.join(XD, f))
        say('원본을 backup/cutin 에서 되살렸습니다')


def install(say=print):
    import hires
    if not os.path.isdir(SRC):
        raise SystemExit('5.1.0 트리가 없습니다: %s' % SRC)
    baseline(say)
    sheet, rect, _missing = plan(say)
    p = write_atlas(sheet, rect, say)
    hires.resplit(p, say)
    write_prefab(say)
    say('')
    say('컷인을 열넷으로 늘렸습니다. 이제 APK 를 다시 만드세요.')
    return 0


def scan(say=print):
    if not os.path.isdir(SRC):
        say('5.1.0 트리가 없습니다: %s' % SRC)
        return 1
    ours, _im, apid, tpid = _sheet(_base(SA1))
    theirs, _im2, _a, _t = _sheet(os.path.join(SRC, SA1))
    say('우리 Atlas_Cutin  조각 %d개 (아틀라스 pathID %d · 텍스처 %d)'
        % (len(ours), apid, tpid))
    say('5.1.0            조각 %d개' % len(theirs))
    say('')
    for i, nm in enumerate(ORDER):
        w = ours.get(nm) or theirs.get(nm)
        sz = '%dx%d' % tuple(int(round(v)) for v in w[1][2:]) if w else '없음'
        say('  %2d %-9s %-11s %-8s %s'
            % (i, WHO[i], nm, sz, '있음' if nm in ours else '**가져온다**'))
    _sh, _rect, missing = plan(say)
    return 0


def restore(say=print):
    if not os.path.isdir(BAK):
        raise SystemExit('남겨 둔 원본이 없습니다: %s' % BAK)
    for f in os.listdir(XD):
        if f.startswith(SA1 + '.split'):
            os.remove(os.path.join(XD, f))
    k = 0
    for f in sorted(os.listdir(BAK)):
        shutil.copy2(os.path.join(BAK, f), os.path.join(XD, f))
        k += 1
    say('되돌린 파일 %d개' % k)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scan', action='store_true')
    ap.add_argument('--restore', action='store_true')
    a = ap.parse_args()
    if a.scan:
        return scan()
    if a.restore:
        return restore()
    return install()


if __name__ == '__main__':
    sys.exit(main())
