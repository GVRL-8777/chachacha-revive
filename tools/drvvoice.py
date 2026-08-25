# -*- coding: utf-8 -*-
"""캐릭터 카드에서 **기본 4인방만 소리가 나던 것**을 고친다.

## 무엇이 잘못돼 있었나

드라이버 카드 프리팹에는 카드마다 소리 자리가 **둘** 있다.

    카드 GameObject   N_Driver_XXX   UIButtonSound  → 누를 때   (CHOICE)
    카드 GameObject   N_Driver_XXX   AudioSource    → 장착될 때 (EQUIP)

`UIButtonSound` 는 `NGUITools.PlaySound(audioClip, …)` 를 부를 뿐이고,
`AudioSource` 쪽은 `DriverUnit::SelectDriverCompleteServer` 가 서버 응답을
받고 재생한다. **둘 다 스크립트가 클립을 고르지 않는다** — 프리팹에 물려
있는 것을 그대로 낸다.

그런데 열두 칸 중 **넷만** 물려 있다.

    5_Driver_Normal   DOKANG    2_Driver_Chasara  SARA
    4_Driver_Bin      BIN       3_Driver_Na       NAYOUBI

까닭은 자산 쪽이다. 중국판 APK 안에는 VOX 가 **이 넷의 것 80개뿐**이고,
나머지 열 명의 목소리는 우리가 나중에 **번들**에 넣은 것이다. 프리팹은
APK 안 자산만 PPtr 로 가리킬 수 있어 번들 쪽을 못 본다.

## 어떻게 고치나

번들에 든 클립을 **APK 트리로 옮겨** 놓고 빈 자리를 채운다. IL 은 한 줄도
안 건드린다 — 원판이 짜 둔 자리에 값만 넣는 것이다.

    1. 번들에서 CHOICE · EQUIP 클립 12개를 오려 새 자산 파일 하나로 묶는다
       (AudioClip 은 가리키는 것이 없어 그냥 옮겨도 된다)
    2. 프리팹 외부 목록 **뒤에** 그 파일을 더한다 (앞을 건드리면 기존
       참조가 어긋난다)
    3. 빈 `UIButtonSound` 여섯과 빈 `AudioSource` 여섯의 PPtr 을 적는다

## 채워지는 카드

    0_Driver_Garu     GYARU      갸루상
    1_Driver_Pig      PIG        김준현
    6_Driver_Angry    ANGRY      앵그리성호
    7_Driver_Mental   ROPE       정신이
    8_Driver_Jeongbi  NAJUNGBI   나정비
    9_Driver_Byul     AHNBYULE   안별이

쌈바여인(10) · 한이 가희(11)는 **목소리가 어느 판에도 없어** 계속 조용하다
(`docs/DORMANT.md`).

정식판이 나정비 · 안별이의 장착 클립 이름을 `_VOX_EQUIPT` 로 오타 냈다.
여기서는 이름이 아니라 PPtr 로 가리키므로 그대로 쓴다.

    python tools/drvvoice.py --scan     어디가 비어 있나
    python tools/drvvoice.py            채운다
    python tools/drvvoice.py --restore  backup/drvvoice 에서 되돌린다
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

XD = os.path.join(HERE, 'x77', 'assets', 'bin', 'Data')
BAK = os.path.join(HERE, 'backup', 'drvvoice')
PACKDAT = os.path.join(HERE, 'pack.dat')

PREFAB = '51161fc3df9f94087a76edf2817d987a'      # UI/Prefabs/DriverUnit
# 새로 만드는 자산. 이름은 아무 것이나 되지만 다른 것과 겹치면 안 된다.
VOXFILE = 'c8a97e3f1b2d4e5a6b7c8d9e0f112233'

AUDIOCLIP, AUDIOSOURCE, MONOBEHAVIOUR = 83, 82, 114

# UIButtonSound: 머리 24(오브젝트 8 · 켜짐 4 · 스크립트 8 · 이름 4) 뒤가 본문.
# 첫 필드가 `audioClip` 이다.
BTN_CLIP = 24
# AudioSource: 오브젝트 8 · 켜짐 4 뒤가 `m_audioClip`.
SRC_CLIP = 12

# 카드 GameObject 이름 → 보이스 이름
CARDS = [
    ('0_Driver_Garu', 'GYARU'),
    ('1_Driver_Pig', 'PIG'),
    ('6_Driver_Angry', 'ANGRY'),
    ('7_Driver_Mental', 'ROPE'),
    ('8_Driver_Jeongbi', 'NAJUNGBI'),
    ('9_Driver_Byul', 'AHNBYULE'),
]


def _sf(path):
    from UnityPy.streams import EndianBinaryReader
    from UnityPy.files.SerializedFile import SerializedFile
    return SerializedFile(EndianBinaryReader(io.open(path, 'rb').read()), None)


def _clipname(blob):
    n = struct.unpack_from('<i', blob, 0)[0]
    if not (0 < n < 80):
        return None
    try:
        return blob[4:4 + n].decode('utf-8')
    except UnicodeDecodeError:
        return None


def pull(say=lambda *a: None):
    """번들에서 클립 12개를 오려 온다. {이름: 날바이트}"""
    from sfparse import parse
    meta = parse(PACKDAT)
    raw = io.open(PACKDAT, 'rb').read()
    want = {}
    for _card, who in CARDS:
        # 정식판이 EQUIP 을 EQUIPT 로 오타 낸 자리가 있다.
        want['%s_VOX_CHOICE' % who] = None
        want['%s_VOX_EQUIP' % who] = None
    got = {}
    for o in meta['objects']:
        if o['class_id'] != AUDIOCLIP:
            continue
        b = raw[meta['data_offset'] + o['start']:][:o['size']]
        nm = _clipname(b)
        if nm is None:
            continue
        key = nm[:-1] if nm.endswith('EQUIPT') else nm
        if key in want:
            got[key] = bytes(b)
    miss = [k for k in want if k not in got]
    if miss:
        raise SystemExit('번들에 없는 클립: %s' % ', '.join(sorted(miss)))
    say('  번들에서 클립 %d개를 오렸습니다' % len(got))
    return got


def build(got, say=lambda *a: None):
    """클립들을 자산 파일 하나로 묶는다. {이름: pathID}"""
    from mktaegeuk import write_serialized
    from sfparse import parse
    order = []
    for _card, who in CARDS:
        order.append('%s_VOX_CHOICE' % who)
        order.append('%s_VOX_EQUIP' % who)
    objs = [(i + 1, AUDIOCLIP, got[nm]) for i, nm in enumerate(order)]
    out = os.path.join(XD, VOXFILE)
    write_serialized(out, parse(os.path.join(XD, PREFAB)), objs, [])
    say('  %s %.2f MB · 소리 %d개'
        % (VOXFILE[:12], os.path.getsize(out) / 1048576.0, len(objs)))
    return dict((nm, i + 1) for i, nm in enumerate(order))


# ------------------------------------------------------------ 프리팹
def _slots(path):
    """[(자리종류, pathID, 오브젝트이름, 지금 PPtr)] — 카드의 소리 자리."""
    import addcars5
    from sfparse import parse
    meta = parse(path)
    raw = io.open(path, 'rb').read()
    sf = _sf(path)
    ext = [os.path.basename(e) for e in meta['externals']]
    names = addcars5.ourscripts()
    gname = {}
    for pid, o in sf.objects.items():
        if o.type.name == 'GameObject':
            try:
                gname[pid] = o.read_typetree()['m_Name']
            except Exception:
                pass
    out = []
    for o in meta['objects']:
        b = raw[meta['data_offset'] + o['start']:][:o['size']]
        if o['class_id'] == AUDIOSOURCE:
            kind, at = 'EQUIP', SRC_CLIP
        elif o['class_id'] == MONOBEHAVIOUR and o['size'] >= BTN_CLIP + 8:
            fid, spid = struct.unpack_from('<ii', b, 12)
            ok = (not fid) or (fid <= len(ext)
                               and ext[fid - 1] == 'sharedassets0.assets')
            if not ok or names.get(spid) != 'UIButtonSound':
                continue
            kind, at = 'CHOICE', BTN_CLIP
        else:
            continue
        go = struct.unpack_from('<ii', b, 0)[1]
        out.append((kind, o['path_id'], gname.get(go, '?'), at,
                    struct.unpack_from('<ii', b, at)))
    return out


def fill(pathids, say=print):
    """프리팹의 빈 자리를 채운다. 외부 목록에 새 파일을 더한다."""
    from sfparse import parse
    p = os.path.join(XD, PREFAB)
    meta = parse(p)
    raw = bytearray(io.open(p, 'rb').read())
    ext = [os.path.basename(e) for e in meta['externals']]
    if VOXFILE in ext:
        fid = ext.index(VOXFILE) + 1
    else:
        ext.append(VOXFILE)
        fid = len(ext)
        say('  외부 목록 %d → %d개 (새 파일은 **뒤에만** 더한다)'
            % (len(ext) - 1, len(ext)))
    want = dict((c, w) for c, w in CARDS)
    n = bad = 0
    # 나중에 복제해 넣은 카드 넷(8~11)은 **단추 클릭음의 fileID 가 망가져**
    # 있다. 외부가 아홉인데 456 · 518 · 580 · 642 를 가리킨다 — 복제 도구가
    # 그 프리팹 안 pathID 를 fileID 자리에 적은 것으로 보인다. 범위 밖이라
    # 유니티는 널로 읽고, 그래서 그 넷은 눌러도 딸깍 소리조차 안 난다.
    # 멀쩡한 단추들이 쓰는 값으로 맞춰 준다.
    good = None
    for kind, pid, gname, at, cur in _slots(p):
        if (kind == 'CHOICE' and gname.endswith('_Button')
                and 0 < cur[0] <= len(ext)):
            good = cur
            break
    for kind, pid, gname, at, cur in _slots(p):
        if (kind == 'CHOICE' and gname.endswith('_Button')
                and cur[0] > len(ext) and good):
            rec = [o for o in meta['objects'] if o['path_id'] == pid][0]
            struct.pack_into('<ii', raw,
                             meta['data_offset'] + rec['start'] + at, *good)
            say('    %-18s 단추 클릭음 {%d,%d} → {%d,%d} (망가져 있었다)'
                % (gname, cur[0], cur[1], good[0], good[1]))
            bad += 1
    for kind, pid, gname, at, _cur in _slots(p):
        who = want.get(gname)
        if who is None:
            continue
        clip = pathids['%s_VOX_%s' % (who, kind)]
        rec = [o for o in meta['objects'] if o['path_id'] == pid][0]
        struct.pack_into('<ii', raw, meta['data_offset'] + rec['start'] + at,
                         fid, clip)
        say('    %-18s %-6s → %s_VOX_%s' % (gname, kind, who, kind))
        n += 1
    say('  자리 %d곳을 채웠습니다%s'
        % (n, ' · 망가진 단추 %d개를 고쳤습니다' % bad if bad else ''))
    _rewrite(p, meta, bytes(raw), ext, say)
    return n


def _rewrite(path, meta, raw, ext, say):
    """외부 목록만 늘려 다시 쓴다. 오브젝트는 **날바이트 그대로** 옮긴다.

    타입트리를 왕복시키지 않는다 — 이 프리팹에는 우리가 못 읽는 오브젝트가
    섞여 있고, 어차피 바꾼 것은 PPtr 몇 자리뿐이다. 오브젝트 표는
    **pathID 오름차순**으로 적는다(원본이 그렇고, 자료 순서로 적었다가
    레이스 장면에서 앱이 죽은 적이 있다 — `tools/cutin5.py`)."""
    data = raw[meta['data_offset']:]
    m = meta['unity'].encode('utf-8') + b'\0'
    m += struct.pack('<i', meta['platform'])
    m += struct.pack('<i', 0)
    m += struct.pack('<i', meta['big_id'])
    m += struct.pack('<i', len(meta['objects']))
    for o in sorted(meta['objects'], key=lambda x: x['path_id']):
        m += struct.pack('<iIIiHh', o['path_id'], o['start'], o['size'],
                         o['type_id'], o['class_id'], o['destroyed'])
    m += struct.pack('<i', len(ext))
    for nm in ext:
        m += (b'\0' + b'\0' * 16 + struct.pack('<i', 0)
              + nm.encode('utf-8') + b'\0')
    m += b'\0'
    doff = max(meta['data_offset'], (20 + len(m) + 64 + 15) & ~15)
    head = struct.pack('>IIII', len(m), doff + len(data), 9, doff)
    head += bytes([1 if meta['endian'] == '>' else 0, 0, 0, 0])
    out = bytearray(head + m)
    while len(out) < doff:
        out += b'\0'
    out += data
    io.open(path, 'wb').write(bytes(out))
    say('  %s %d → %d바이트' % (PREFAB[:12], len(raw), len(out)))


# ------------------------------------------------------------ 손잡이
def baseline(say):
    os.makedirs(BAK, exist_ok=True)
    b = os.path.join(BAK, PREFAB)
    if os.path.exists(b):
        shutil.copy2(b, os.path.join(XD, PREFAB))
        say('프리팹을 backup/drvvoice 에서 되살렸습니다')
    else:
        shutil.copy2(os.path.join(XD, PREFAB), b)
        say('프리팹 원본을 backup/drvvoice 에 남겼습니다')


def scan(say=print):
    p = os.path.join(XD, PREFAB)
    rows = _slots(p)
    who = dict((c, w) for c, w in CARDS)
    say('카드 소리 자리 %d곳' % len(rows))
    for kind, pid, gname, _at, (f, q) in sorted(rows, key=lambda r: r[2]):
        if not gname.startswith(tuple('0123456789')):
            continue
        cur = '비어 있음' if not (f or q) else '{%d,%d}' % (f, q)
        plan = ''
        if not (f or q):
            plan = ('→ %s' % who[gname]) if gname in who else '→ (목소리 없음)'
        say('  %-18s %-6s %-12s %s' % (gname, kind, cur, plan))
    return 0


def add(say=print):
    baseline(say)
    got = pull(say)
    ids = build(got, say)
    fill(ids, say)
    say('')
    say('카드 여섯에 CHOICE · EQUIP 을 물렸습니다. 이제 APK 를 다시 만드세요.')
    return 0


def restore(say=print):
    if not os.path.isdir(BAK):
        raise SystemExit('남겨 둔 원본이 없습니다: %s' % BAK)
    shutil.copy2(os.path.join(BAK, PREFAB), os.path.join(XD, PREFAB))
    v = os.path.join(XD, VOXFILE)
    if os.path.exists(v):
        os.remove(v)
    say('프리팹을 되돌리고 새 자산을 지웠습니다')
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
    return add()


if __name__ == '__main__':
    sys.exit(main())
