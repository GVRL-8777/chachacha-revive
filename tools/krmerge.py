# -*- coding: utf-8 -*-
"""게임 안 한국어 표를 **한국 정식판 것으로** 바꾼다.

지금 빌드의 한국어는 LINE 1.0.3(일본)판에서 가져온 것이라 이름이 다르다.
차가 `가루다`인데 미션 문구는 `엠페러`를 말하는 식으로 앞뒤가 안 맞는다.
진짜 한국 서비스판의 표를 두 벌 손에 넣었으므로 그것으로 덮는다.

  · **한국 7.7.0** (`CCC_fK_v7.7.0.apk`, 2014-07, 유니티 4.1.5f1)
    한국 마지막 정식판. 표가 `tb_systemtext` + `tb_systemtext_basic` 둘로 나뉜다.
  · **한국 초기판** (`8.apk`, 2013-01, v1.2.3)
    7.7.0 에 없는 키를 메운다.

둘이 다르면 **7.7.0 을 따른다.**

## 지키는 규칙 네 가지

1. **열쇠 목록은 지금 것을 그대로 쓴다.** 원판에만 있는 키는 우리 코드가
   찾지 않으므로 넣어도 죽은 값이다.
2. **자리표시자 구성이 다르면 안 바꾼다.** `String.Format` 이 개수가 안 맞으면
   `FormatException` 을 던져 게임이 죽는다.
3. **값이 있는 것을 빈 값으로 덮지 않는다.** 원판 표에는 빈 칸이 꽤 있는데
   그대로 넣으면 화면의 라벨이 빈칸이 된다.
4. **`TrophyCount*` 는 실제 지급량에서 만든다.** 라벨과 실제가 어긋나면
   안 되기 때문이다. 지금 빌드의 라벨은 셋이 틀려 있었다
   (`×30 → 35`, `×210 → 130`, `×380 → 420`).

표는 `키 = 값` 한 줄마다 **CRLF 하나**로 끝난다. 두 번 넣으면 게임이 표를
통째로 못 읽어 모든 라벨이 빈칸이 된다.

    python tools/krmerge.py --dry       무엇이 바뀌는지만 본다
    python tools/krmerge.py             바꾼다
    python tools/krmerge.py --restore   backup/text 에서 되돌린다
"""
import argparse
import io
import json
import os
import re
import shutil
import sys

CODE = os.path.dirname(os.path.abspath(__file__))
HERE = os.path.dirname(CODE)
sys.path.insert(0, CODE)

DATA = os.path.join('assets', 'bin', 'Data')
TREE = os.path.join(HERE, 'x77')
BAK = os.path.join(HERE, 'backup', 'text')
KR77 = os.path.join(HERE, '_scratch', 'kr77', 'assets', 'bin', 'Data')
KR8 = os.path.join(HERE, '_scratch', 'kr8', 'assets', 'bin', 'Data')
DATAJSON = os.path.join(HERE, 'chalocal_data.json')

# 7.7.0 은 표가 둘이다. `tb_systemtext` 가 나중에 와서 겹치면 이긴다.
KR77_ORDER = ('tb_systemtext_basic', 'tb_systemtext')
PH = re.compile(r'\{\d+[^}]*\}')

# 덮으면 안 되는 것들.
#
#   mission9 · mission14
#     이 프로젝트가 직접 쓴 문구다. 원판에 없는 보상 안내가 들어 있다
#     (헬리 · 블럭스 해금은 이 프로젝트가 붙였다).
#   ResetRank
#     원판 문구("{0} 일 뒤에 초기화 됩니다.")는 로비 머리글에서 **타이어 아이콘을
#     침범한다.** 실기로 확인했다. 7.7.0 판은 자리표시자가 넷이라 애초에 못 쓴다.
#   Free
#     차 상점의 값 자리는 좁다. `tools/freetext.py` 가 **그 칸에 맞추려고**
#     '무료'로 줄여 놓은 것이라 '무료지급'으로 되돌리면 다시 넘친다.
KEEP = ('mission9', 'mission14', 'ResetRank', 'Free')

# 차 이름을 원판 것으로 되돌리면 **그 이름을 본문에 쓴 문구**도 따라가야 한다.
# 표를 훑어 확인한 세 곳뿐이고, 다른 말에 잘못 걸리는 자리는 없었다.
RENAME = {
    'mission14': [('스피드스터', '블럭스')],
    'Package4': [('앰버', '엠버')],
    'Package5': [('앰버', '엠버')],
}


def tables(root):
    """트리 안의 `tb_systemtext*` TextAsset 을 {이름: (파일, pathID, 글)} 로."""
    import UnityPy
    out = {}
    if not os.path.isdir(root):
        return out
    for name in sorted(os.listdir(root)):
        p = os.path.join(root, name)
        if '.' in name or not os.path.isfile(p) or os.path.getsize(p) < 512:
            continue
        try:
            env = UnityPy.load(p)
        except Exception:
            continue
        for o in env.objects:
            if o.type.name != 'TextAsset':
                continue
            try:
                t = o.read_typetree()
            except Exception:
                continue
            nm = t.get('m_Name') or ''
            if not nm.startswith('tb_systemtext'):
                continue
            s = t.get('m_Script') or ''
            b = s if isinstance(s, (bytes, bytearray)) else s.encode('utf-8')
            out[nm] = (name, o.path_id, bytes(b).decode('utf-8', 'replace'))
    return out


def parse(text):
    """`키 = 값` 을 순서를 지키며 읽는다."""
    out = []
    for line in text.replace('\r\n', '\n').split('\n'):
        if ' = ' in line:
            k, v = line.split(' = ', 1)
            out.append((k, v))
    return out


def trophy_labels():
    """실제 지급량에서 `TrophyCount*` 라벨을 만든다. 한국판 서식(`x 35`)."""
    try:
        d = json.load(io.open(DATAJSON, encoding='utf-8'))
        items = d['billingItems']
    except Exception:
        return {}
    out = {}
    for i in range(1, 7):
        v = items.get('chacha_CN_%03d' % i)
        if v is not None:
            out['TrophyCount%d' % i] = 'x %d' % v
    return out


def build(dry=False):
    from sfedit import replace_object

    cur_t = tables(os.path.join(TREE, DATA))
    if 'tb_systemtext' not in cur_t:
        raise SystemExit('작업 트리에서 tb_systemtext 를 못 찾았습니다')
    fname, pid, cur_text = cur_t['tb_systemtext']

    kr77 = {}
    t77 = tables(KR77)
    for nm in KR77_ORDER:
        if nm in t77:
            kr77.update(dict(parse(t77[nm][2])))
    kr8 = {}
    for nm, (_f, _p, s) in tables(KR8).items():
        kr8.update(dict(parse(s)))
    if not kr77 and not kr8:
        raise SystemExit(
            '원판 표가 없습니다. 먼저 풀어 두세요:\n'
            '  _scratch/kr77/  <- CCC_fK_v7.7.0.apk 의 assets/bin/Data\n'
            '  _scratch/kr8/   <- 8.apk 의 assets/bin/Data')

    fixed = trophy_labels()
    rows = parse(cur_text)
    out = []
    n77 = n8 = ntr = 0
    blocked_ph = []
    blocked_empty = []
    changed = []
    for k, v in rows:
        new = None
        src = ''
        if k in KEEP:
            pass
        elif k in fixed:
            new, src = fixed[k], '지급량'
        else:
            for cand, tag in ((kr77.get(k), '7.7'), (kr8.get(k), '초기')):
                if cand is None:
                    continue
                if sorted(PH.findall(cand)) != sorted(PH.findall(v)):
                    blocked_ph.append((k, v, cand))
                    continue
                if not cand.strip() and v.strip():
                    blocked_empty.append((k, v))
                    continue
                new, src = cand, tag
                break
        for old, rep in RENAME.get(k, ()):
            base = new if new is not None else v
            if old in base:
                new, src = base.replace(old, rep), (src or '이름맞춤')
        if new is not None and new != v:
            changed.append((src, k, v, new))
            if src == '7.7':
                n77 += 1
            elif src == '초기':
                n8 += 1
            else:
                ntr += 1
            v = new
        out.append((k, v))

    body = ''.join('%s = %s\r\n' % (k, v) for k, v in out)
    print('  한국7.7 값으로  %4d' % n77)
    print('  초기판 값으로   %4d' % n8)
    print('  지급량에서 만듦 %4d' % ntr)
    print('  자리표시자가 달라 막음 %3d · 빈 값이라 막음 %3d'
          % (len(blocked_ph), len(blocked_empty)))
    print('  표 %d줄 · %d바이트 -> %d바이트'
          % (len(out), len(cur_text.encode('utf-8')), len(body.encode('utf-8'))))
    if dry:
        print()
        for src, k, old, new in changed:
            print('  [%s] %-26s %-30s -> %s' % (src, k[:26], old[:30], new[:40]))
        return 0

    import UnityPy
    p = os.path.join(TREE, DATA, fname)
    os.makedirs(BAK, exist_ok=True)
    bak = os.path.join(BAK, fname)
    if not os.path.exists(bak):
        shutil.copy2(p, bak)
        print('  원본을 남겨 둠: backup/text/%s' % fname)
    env = UnityPy.load(p)
    for o in env.objects:
        if o.path_id != pid or o.type.name != 'TextAsset':
            continue
        t = o.read_typetree()
        t['m_Script'] = body
        _a, _b, fold, fnew = replace_object(p, pid, bytes(o.save_typetree(t)))
        print('  %s : 파일 %d -> %d 바이트' % (fname[:14], fold, fnew))
        break
    return 0


def restore():
    if not os.path.isdir(BAK):
        raise SystemExit('남겨 둔 원본이 없습니다: %s' % BAK)
    n = 0
    for name in sorted(os.listdir(BAK)):
        shutil.copy2(os.path.join(BAK, name), os.path.join(TREE, DATA, name))
        n += 1
    print('되돌린 파일 %d개' % n)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry', action='store_true')
    ap.add_argument('--restore', action='store_true')
    a = ap.parse_args()
    if a.restore:
        return restore()
    return build(a.dry)


if __name__ == '__main__':
    sys.exit(main())
