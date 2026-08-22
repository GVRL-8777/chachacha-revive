# -*- coding: utf-8 -*-
"""옮길 말의 열쇠를 긁어모아 `lang/*.json` 에 맞춰 넣습니다.

    python langkeys.py            무엇이 모자란지 보기만 합니다
    python langkeys.py --write    lang/*.json 을 맞춰 씁니다
    python langkeys.py --new ja --name 日本語    새 언어 뼈대를 만듭니다

**이미 있는 번역은 건드리지 않습니다.** 새 열쇠는 빈 값으로 들어가고,
빈 값이면 화면에 한국어가 그대로 나오므로 어디가 덜 됐는지 바로 보입니다.
없어진 열쇠는 지웁니다(파일이 계속 불어나지 않게).

열쇠는 **한국어 원문 그대로**입니다. 그래서 새 언어를 붙일 때는
`lang/en.json` 을 복사해 값만 바꾸면 됩니다.
"""
import argparse
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

KO = re.compile('[가-힣]')
LIT = r"""(?:'((?:[^'\\]|\\.)*)'|"((?:[^"\\]|\\.)*)")"""


def lits(text, fn):
    """`fn('…')` 꼴에서 문자열을 뽑는다.

    `+` 로 이은 것(자바스크립트)과 그냥 붙여 쓴 것(파이썬) 둘 다 잇는다."""
    out = []
    pat = re.compile(re.escape(fn) + r'\(\s*' + LIT +
                     r'(?:\s*\+?\s*' + LIT + r')*')
    for m in pat.finditer(text):
        parts = [(a if a is not None else b)
                 for a, b in re.findall(LIT, m.group(0))]
        s = ''.join(parts)
        s = s.replace("\\'", "'").replace('\\"', '"').replace('\\\\', '\\')
        if KO.search(s):
            out.append(s)
    return out


def collect():
    """화면과 서버 양쪽에서 열쇠를 모은다."""
    import chatool_page as P
    import chatool_page_assets as PA
    import chasaves as V
    import chahost as H
    import chabuild as B

    keys = set()
    js = ''.join(re.findall(r'<script>(.*?)</script>', P.PAGE, re.S))
    keys |= set(lits(js, 'T'))
    keys |= set(lits(PA.ASSETS, 'T'))

    keys |= set(lits(io.open(os.path.join(HERE, 'chatool.py'),
                             encoding='utf-8').read(), '_msg'))
    keys |= set(lits(io.open(os.path.join(HERE, 'chatool_assets.py'),
                             encoding='utf-8').read(), '_L'))
    # 표에 원문으로 둔 것 — 쓰는 자리에서 옮긴다
    import chatool_assets as A
    keys |= {d for _k, d, _e in A.FORMATS}
    keys |= {lab for _k, lab in A.CATS}
    for f in ('chasaves.py', 'chahost.py', 'chabuild.py'):
        keys |= set(lits(io.open(os.path.join(HERE, f),
                                 encoding='utf-8').read(), 't'))

    # 표에 박아 둔 말 — 함수 호출이 아니라 훑기에 안 잡힌다
    for p in V.PRESETS:
        keys |= {p['label'], p['tag'], p['desc'], p['note']} | set(p['facts'])
    for w in H.WAYS:
        keys |= {w['label'], w['desc']} | set(w['steps'])
    keys |= {what for _rel, what in B.WATCH}
    keys |= {'(아직 APK 가 없습니다)'}

    # 탭 이름은 `T(변수)` 로 옮기므로 훑기에 안 잡힌다
    m = re.search(r'const TABS=\[(.*?)\];', js, re.S)
    if m:
        keys |= set(re.findall(r"'([^']+)'", m.group(1)))

    return sorted(k for k in keys if KO.search(k))


def sync(write=False):
    import chalang
    keys = collect()
    print('열쇠 %d개' % len(keys))
    os.makedirs(chalang.DIR, exist_ok=True)
    for f in sorted(os.listdir(chalang.DIR)):
        if not f.endswith('.json'):
            continue
        code = f[:-5]
        old = chalang.load(code)
        out = {'_name': old.get('_name', code)}
        added, dropped = [], [k for k in old if k != '_name' and k not in keys]
        for k in keys:
            if code == chalang.DEFAULT_LANG:
                # 한국어는 원문이 곧 번역. 단 뜻 가름표(`기록|주행`)는
                # 떼어 낸다 — 안 그러면 화면에 막대기가 그대로 나온다.
                out[k] = old.get(k) or chalang.bare(k)
            else:
                out[k] = old.get(k, '')
                if not out[k]:
                    added.append(k)
        blank = sum(1 for k in keys if not out.get(k))
        print('  %-6s 채움 %d / %d · 새 열쇠 %d · 없어진 열쇠 %d'
              % (code, len(keys) - blank, len(keys), len(added), len(dropped)))
        for k in added[:8]:
            print('      비었음: %s' % k[:70])
        if write:
            io.open(os.path.join(chalang.DIR, f), 'w',
                    encoding='utf-8').write(
                json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
    if write:
        chalang.reload()
        print('맞춰 썼습니다.')
    else:
        print('보기만 했습니다. 실제로 쓰려면 --write 를 붙이세요.')


def new_lang(code, name):
    import chalang
    keys = collect()
    os.makedirs(chalang.DIR, exist_ok=True)
    p = os.path.join(chalang.DIR, '%s.json' % code)
    if os.path.exists(p):
        raise SystemExit('이미 있습니다: %s' % p)
    out = {'_name': name or code}
    for k in keys:
        out[k] = ''
    io.open(p, 'w', encoding='utf-8').write(
        json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
    print('만들었습니다: %s' % p)
    print('값만 채우면 런처의 언어 목록에 바로 뜹니다.')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true', help='lang/*.json 에 쓴다')
    ap.add_argument('--new', help='새 언어 코드 (예: ja)')
    ap.add_argument('--name', help='그 언어의 이름 (예: 日本語)')
    a = ap.parse_args()
    if a.new:
        new_lang(a.new, a.name)
    else:
        sync(a.write)


if __name__ == '__main__':
    main()
