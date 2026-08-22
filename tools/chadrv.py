# -*- coding: utf-8 -*-
"""드라이버 프로필 — 초상화 · 이름 · 능력 · 값 · 보이스.

드라이버 열둘은 **슬롯이 고정**입니다. 카드 배열이 프리팹에 열둘로 박혀
있어서 열셋째를 만들려면 UI 프리팹을 수술해야 합니다. 그래서 여기서는
있는 열둘을 제대로 보여 주고 고치는 데까지만 합니다.

자료가 흩어져 있는 자리 (실측)

  · 이름 · 능력글   `tb_systemtext` 의 `Char<번호>` · `Char<번호>Exp`
  · 값(트로피)      드라이버 창 프리팹의 카드 라벨 글자
                    (클라이언트가 `Int32.TryParse(라벨.text)` 로 읽습니다)
  · 초상화          UI 아틀라스 `Atlas_MainMenu` 의 스프라이트
                    `PTDriverPc`(1번) · `PTDriverPc1`~`PTDriverPc11`
  · 보이스          `Character VOX/<폴더>/<폴더>_VOX_<동작>` 오디오 클립

보이스 폴더는 이름이 아니라 **`Cutin/eCutinModelType` 열거형**이 정합니다.
`Player::_GetCutinModel` 의 switch 를 뜯어 보고 짝을 맞췄습니다. 이름만
보고 짐작하면 틀립니다 — 앵그리성호는 7번인데 열거형에서는 10번입니다.
"""
import io
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chaassets as A                                     # noqa: E402

CODE = os.path.dirname(os.path.abspath(__file__))
# 도구는 tools/ 안에 있고, 작업 트리(x77 · saves · lang …)는 그 위에 있다.
HERE = os.path.dirname(CODE)
DATA = os.path.join('assets', 'bin', 'Data')
ATLAS_PID = 645                     # sharedassets0 안 UIAtlas(MonoBehaviour)
ATLAS_TEX = 20                      # 같은 파일 안 Atlas_MainMenu 텍스처
COUNT = 12                          # 슬롯은 열둘로 고정입니다
BASE_DRIVER = 1                     # 도 강현. 지울 수 없습니다.

# 드라이버 번호 -> 보이스 폴더. `Player::_GetCutinModel` 의 switch 그대로.
# 9~12 번은 나중에 슬롯을 늘리며 붙인 자리라 보이스가 없습니다.
VOICE = {1: 'DOKANG', 2: 'SARA', 3: 'BIN', 4: 'NAYOUBI', 5: 'PIG',
         6: 'GYARU', 7: 'ANGRY', 8: 'ROPE'}


def sprite_name(no):
    return 'PTDriverPc' if no == 1 else 'PTDriverPc%d' % (no - 1)


# ------------------------------------------------------------------ 붙인 자산
_SA0 = [None]


def shared0(tree):
    """`sharedassets0` 는 `.splitN` 으로 쪼개져 있습니다. 이어 붙여 읽습니다."""
    if _SA0[0] is not None:
        return _SA0[0]
    from UnityPy.streams import EndianBinaryReader
    from UnityPy.files.SerializedFile import SerializedFile
    d = os.path.join(tree, DATA)
    parts = sorted([f for f in os.listdir(d)
                    if f.startswith('sharedassets0.assets.split')],
                   key=lambda x: int(x.rsplit('split', 1)[1]))
    blob = b''.join(io.open(os.path.join(d, p), 'rb').read() for p in parts)
    _SA0[0] = SerializedFile(EndianBinaryReader(blob), None)
    return _SA0[0]


def portrait(tree, no, out_png):
    """아틀라스에서 초상화 한 칸을 잘라 PNG 로 냅니다."""
    import uiatlas
    from PIL import Image
    sf = shared0(tree)
    tb = uiatlas.table(sf.objects[ATLAS_PID].get_raw_data())
    hit = tb.get(sprite_name(no))
    if not hit:
        return None
    x, y, w, h = (int(round(v)) for v in hit[1])
    tex = sf.objects[ATLAS_TEX].read()
    im = tex.image.convert('RGBA')
    # NGUI 는 왼쪽 위가 원점이고 PIL 도 그렇습니다. 유니티 텍스처는 아래에서
    # 위로 담기므로 UnityPy 가 이미 뒤집어 줍니다.
    box = (x, y, x + w, y + h)
    im.crop(box).save(out_png)
    return (w, h)


# ------------------------------------------------------------------ 글
def _systext(tree):
    import freetext as F
    from sfparse import parse
    p = os.path.join(tree, F.ASSET)
    raw = bytearray(io.open(p, 'rb').read())
    text, tst, tlen = F.textasset(raw, parse(p), 1)
    return p, raw, text, tst, tlen


def texts(tree):
    """`Char1` · `Char1Exp` … 를 읽어 옵니다."""
    _p, _raw, text, _t, _l = _systext(tree)
    out = {}
    for ln in text.splitlines():
        if '=' not in ln:
            continue
        k, v = ln.split('=', 1)
        k = k.strip()
        if k.startswith('Char'):
            out[k] = v.strip()
    return out


def set_text(tree, key, value):
    """표의 한 줄을 **길이를 지키며** 고칩니다.

    짧아지면 뒤에 공백을 답니다 — 표를 읽는 쪽이 '=' 로 자른 뒤 양쪽을
    Trim 하므로 공백은 사라집니다. 길어지면 못 씁니다."""
    import re
    p, raw, text, tst, tlen = _systext(tree)
    m = re.search('^(' + re.escape(key) + r'[ \t]*=[ \t]*)([^\r\n]*)',
                  text, re.M)
    if not m:
        raise KeyError('그런 항목이 없습니다: %s' % key)
    cur = m.group(2)
    pad = len(cur.encode('utf-8')) - len(value.encode('utf-8'))
    if pad < 0:
        raise ValueError('원래 글보다 %d바이트 깁니다. 표 길이를 지켜야 합니다.'
                         % -pad)
    out = text[:m.start(2)] + value + ' ' * pad + text[m.end(2):]
    blob = out.encode('utf-8')
    assert len(blob) == tlen, (len(blob), tlen)
    raw[tst:tst + tlen] = blob
    io.open(p, 'wb').write(bytes(raw))
    return cur.strip()


# ------------------------------------------------------------------ 값
def _prefab(tree):
    import drvprice as dp
    names = dp.script_names()
    return dp.find_prefab(names)


def prices(tree):
    """카드에 박힌 트로피 값. 없으면 None."""
    import drvprice as dp
    try:
        p, du = _prefab(tree)
        if p is None:
            return {}
        from UnityPy.streams import EndianBinaryReader
        from UnityPy.files.SerializedFile import SerializedFile
        sf = SerializedFile(EndianBinaryReader(io.open(p, 'rb').read()), None)
        arrs = dp.arrays_of(sf.objects[du].get_raw_data())
    except Exception:
        return {}
    if len(arrs) < 3:
        return {}
    return {}


# ------------------------------------------------------------------ 보이스
def voices(tree, no):
    """그 드라이버의 보이스 클립 (이름, 파일, pathID)."""
    folder = VOICE.get(no)
    if not folder:
        return []
    idx = A.load_index() or {}
    out = []
    want = folder.upper() + '_VOX_'
    for _k, rows in idx.items():
        for r in rows:
            if r[2] == 'AudioClip' and r[3].upper().startswith(want):
                out.append({'name': r[3], 'file': r[0], 'pid': r[1]})
    return sorted(out, key=lambda x: x['name'])


def bundled_voices(no):
    """번들에 담아 넣은 보이스. 색인에 없는 것들이라 목록에서 찾습니다."""
    folder = VOICE.get(no)
    if not folder:
        return []
    spec = os.path.join(HERE, 'packspec.txt')
    if not os.path.exists(spec):
        return []
    out = []
    tag = 'Character VOX/%s/' % folder
    for ln in io.open(spec, encoding='utf-8'):
        ln = ln.strip()
        if tag not in ln:
            continue
        bits = ln.split(':')
        out.append({'name': bits[1].rsplit('/', 1)[-1],
                    'path': bits[0], 'pid': int(bits[2]) if len(bits) > 2
                    else 1})
    return sorted(out, key=lambda x: x['name'])


def _sniff(b):
    """소리 파일의 머리만 보고 확장자를 정합니다."""
    if b[:4] == b'RIFF':
        return '.wav'
    if b[:4] == b'OggS':
        return '.ogg'
    if b[:3] == b'ID3' or (len(b) > 1 and b[0] == 0xFF
                           and b[1] in (0xFB, 0xF3, 0xF2)):
        return '.mp3'
    if b[:4] in (b'FSB3', b'FSB4', b'FSB5'):
        return '.fsb'
    return '.bin'


def _clips(path):
    """파일 하나에서 오디오 클립을 (이름, 바이트, 확장자) 로 꺼냅니다.

    UnityPy 디코더가 되면 그걸 쓰고, 안 되면 **원본 바이트 그대로** 냅니다.
    이 게임 클립은 MPEG 라 그대로도 재생됩니다."""
    out = []
    try:
        import UnityPy
        env = UnityPy.load(path)
    except Exception:
        return out
    for obj in env.objects:
        if obj.type.name != 'AudioClip':
            continue
        try:
            c = obj.read()
        except Exception:
            continue
        nm = getattr(c, 'm_Name', None) or 'clip'
        got = False
        try:
            for _sn, sd in (c.samples or {}).items():
                out.append((nm, sd, '.wav'))
                got = True
                break
        except Exception:
            pass
        if got:
            continue
        raw = None
        for attr in ('m_AudioData', 'm_Resource'):
            v = getattr(c, attr, None)
            # UnityPy 는 이걸 **정수 리스트**로 줍니다(바이트가 아닙니다).
            # 이걸 놓치면 클립이 조용히 하나도 안 나옵니다.
            if isinstance(v, (bytes, bytearray, list)) and len(v) > 64:
                raw = bytes(bytearray(v))
                break
            if v is not None and hasattr(v, 'get_data'):
                try:
                    raw = v.get_data()
                except Exception:
                    raw = None
                if raw:
                    break
        if raw:
            out.append((nm, raw, _sniff(raw)))
    return out


# ------------------------------------------------------------------ 프로필
def profiles(tree):
    t = texts(tree)
    out = []
    for no in range(1, COUNT + 1):
        vs = bundled_voices(no)
        out.append({
            'no': no,
            'name': t.get('Char%d' % no) or ('드라이버%d' % no),
            'exp': t.get('Char%dExp' % no) or '',
            'sprite': sprite_name(no),
            'voice': VOICE.get(no),
            'voices': len(vs),
            'base': no == BASE_DRIVER,
        })
    return out


def export(tree, no, root, say=None):
    """초상화 · 보이스 · 프로필 JSON 을 폴더에 냅니다."""
    p = profiles(tree)[no - 1]
    d = os.path.join(root, '드라이버%02d_%s' % (no, p['name']))
    os.makedirs(d, exist_ok=True)
    made = []
    png = os.path.join(d, 'portrait.png')
    if portrait(tree, no, png):
        made.append(png)
    n = 0
    for v in bundled_voices(no):
        src = os.path.join(HERE, v['path'])
        if not os.path.exists(src):
            continue
        for nm, blob, ext in _clips(src):
            q = os.path.join(d, nm + ext)
            io.open(q, 'wb').write(blob)
            made.append(q)
            n += 1
    io.open(os.path.join(d, 'profile.json'), 'w', encoding='utf-8').write(
        json.dumps(p, ensure_ascii=False, indent=2))
    made.append(os.path.join(d, 'profile.json'))
    if say:
        say('  %d번 %s — 초상화 %s · 보이스 %d개'
            % (no, p['name'], '있음' if png in made else '없음', n))
    return made
