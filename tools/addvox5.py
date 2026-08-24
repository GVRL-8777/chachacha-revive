# -*- coding: utf-8 -*-
"""빠져 있던 **캐릭터 보이스 세 벌**을 5.1.0 에서 옮겨 온다.

지금 번들에는 열한 명의 보이스가 220줄 들어 있다. 5.1.0 에는 열네 명 280줄이
있고, 우리에게 없는 셋이 이들이다.

    ROPE       정신이     Driver_8   **지금 빌드에서 바로 쓴다**
    NAJUNGBI   나정비     Driver_9   드라이버가 없어 아직 안 울린다
    AHNBYULE   안별이     Driver_10  드라이버가 없어 아직 안 울린다

## 왜 셋 중 하나만 바로 쓰나

보이스를 고르는 길은 `Cutin::SetVoiceAudioClip` 이다.

    "Character VOX/" + eCutinModelType + "/" + eCutinModelType + "_VOX_" + …

우리 빌드의 `eCutinModelType` 은 열둘(끝이 `ROPE`)이고 `eDriverType` 은
여덟이다. 5.1.0 은 열넷 · 열이라 `NAJUNGBI` · `AHNBYULE` 이 더 있다. 즉
나정비와 안별이는 **드라이버 자체가 없어** 고를 수가 없다. 소리만 넣어
두고, 드라이버 둘을 붙이는 일은 따로 한다(열거자 두 개를 늘리고
`Player::_GetCutinModel` 을 손보고 컷인 그림을 넣어야 한다).

정신이(`ROPE`)는 `eCutinModelType.ROPE` 도 `eDriverType.Driver_8` 도 이미
있는데 **소리만 없었다.** 이 도구가 그 자리를 채운다.

## 어떻게 넣나

소리 60개는 5.1.0 트리의 자산 파일 55개에 흩어져 있고, 그중 하나는
UI 화면이 통째로 든 큰 파일이다(`*_VOX_CHOICE` · `*_VOX_EQUIP` 이 거기 있다).
그 파일을 통째로 들여오면 쓰지도 않을 오브젝트 2천 개가 딸려 온다. 그래서
**AudioClip 60개만 오려** 새 직렬화 파일 하나로 묶는다. AudioClip 은
가리키는 것이 없어(PPtr 0개) 그냥 옮겨도 된다 — 소리는 `m_AudioData` 안에
그대로 들어 있다(형식 13, 실제로는 MP3. `docs/VOICE.md`).

    python tools/addvox5.py --scan     무엇을 가져오나
    python tools/addvox5.py            넣는다
    python tools/addvox5.py --remove   앞 단계로 되돌린다
"""
import argparse
import collections
import io
import os
import struct
import sys

CODE = os.path.dirname(os.path.abspath(__file__))
HERE = os.path.dirname(CODE)
sys.path.insert(0, CODE)

SRC = os.path.join(HERE, '_scratch', 'v5', 'v510', 'assets', 'bin', 'Data')
OUT = os.path.join(HERE, 'vox5.assets')
AUDIOCLIP = 83

# 번들 덧붙이기 차례에서 이 도구의 자리 (`tools/bundlechain.py`)
STAGE = 'bundlevox'

# 5.1.0 자원 폴더 이름 → 우리 번들이 쓰는 `eCutinModelType` 철자.
WHO = collections.OrderedDict([('rope', 'ROPE'), ('najungbi', 'NAJUNGBI'),
                               ('ahnbyule', 'AHNBYULE')])


def collect():
    """[(번들안이름, 원본파일, pathID)] — 60줄."""
    import UnityPy
    from sfparse import parse
    md = os.path.join(SRC, 'mainData')
    ext = [os.path.basename(e) for e in parse(md)['externals']]
    rm = [o for o in UnityPy.load(md).objects
          if o.type.name == 'ResourceManager'][0]
    out = []
    for k, v in rm.read_typetree()['m_Container']:
        if not k.startswith('character vox/'):
            continue
        # 5.1.0 색인에는 `character vox/ahnbyule /…` 처럼 빈칸이 낀 줄이 있다.
        who = k.split('/')[1].strip()
        if who not in WHO:
            continue
        seg = k.rsplit('/', 1)[-1].strip()
        name = 'Character VOX/%s/%s' % (WHO[who], seg.upper())
        fn = ext[v['m_FileID'] - 1] if v['m_FileID'] else 'mainData'
        out.append((name, fn, v['m_PathID']))
    return sorted(out)


def clips(say=lambda *a: None):
    """[(번들안이름, AudioClip 날바이트)] — 이름은 오브젝트 이름으로 고친다."""
    from sfparse import parse
    cache = {}
    out = []
    for name, fn, pid in collect():
        p = os.path.join(SRC, fn)
        if fn not in cache:
            cache[fn] = (parse(p), io.open(p, 'rb').read())
        meta, raw = cache[fn]
        rec = [o for o in meta['objects'] if o['path_id'] == pid][0]
        if rec['class_id'] != AUDIOCLIP:
            raise SystemExit('%s 는 AudioClip 이 아닙니다 (class %d)'
                             % (name, rec['class_id']))
        b = raw[meta['data_offset'] + rec['start']:][:rec['size']]
        n = struct.unpack_from('<i', b, 0)[0]
        real = b[4:4 + n].decode('utf-8')
        # 원본에 `AHNBYULE _VOX_CHOICE` 처럼 빈칸이 낀 이름이 있다. 번들은
        # **이름으로** 찾으므로 빈칸이 있으면 영영 못 찾는다. 여기서 턴다.
        fixed = real.replace(' ', '')
        if fixed != real:
            nb = fixed.encode('utf-8')
            b = (struct.pack('<i', len(nb)) + nb
                 + b'\0' * ((-len(nb)) % 4) + b[4 + n + ((-n) % 4):])
            say('  이름의 빈칸을 텄습니다: %r → %r' % (real, fixed))
        out.append(('Character VOX/%s/%s'
                    % (name.split('/')[1], fixed), bytes(b)))
    return out


def build(say=print):
    from sfparse import parse
    from mktaegeuk import write_serialized
    got = clips(say)
    tmpl = parse(os.path.join(SRC, collect()[0][1]))
    objs = [(i + 1, AUDIOCLIP, b) for i, (_n, b) in enumerate(got)]
    write_serialized(OUT, tmpl, objs, [])
    say('  %s %.1f MB · 소리 %d개'
        % (os.path.basename(OUT), os.path.getsize(OUT) / 1048576.0, len(objs)))
    return [(n, i + 1) for i, (n, _b) in enumerate(got)]


def add(say=print):
    import bundlechain
    import packadd
    if not os.path.isdir(SRC):
        raise SystemExit('5.1.0 트리가 없습니다: %s' % SRC)
    names = build(say)
    bundlechain.start(STAGE, say)
    say('번들에 얹습니다…')
    packadd.add(OUT, ['%s:%d' % (n, p) for n, p in names], say)
    packadd.wrap(say)
    bundlechain.done(STAGE, say)
    say('')
    say('보이스 %d개를 넣었습니다. 정신이(ROPE)는 바로 들립니다.' % len(names))
    say('나정비 · 안별이는 드라이버가 아직 없어 소리만 들어 있습니다.')
    return 0


def scan(say=print):
    import addcars5
    if not os.path.isdir(SRC):
        say('5.1.0 트리가 없습니다: %s' % SRC)
        return 1
    got = collect()
    say('가져올 보이스 %d줄 · 원본 파일 %d개'
        % (len(got), len(set(f for _n, f, _p in got))))
    per = collections.Counter(n.split('/')[1] for n, _f, _p in got)
    for k, v in per.items():
        say('  %-10s %d개' % (k, v))
    sf = addcars5._sf(os.path.join(HERE, 'pack.dat'))
    man = [o for o in sf.objects.values() if o.type.name == 'AssetBundle'][0]
    have = set(c[0] for c in man.read_typetree()['m_Container'])
    dup = [n for n, _f, _p in got if n in have]
    say('번들에 이미 있는 줄: %d개' % len(dup))
    cur = collections.Counter()
    for k in have:
        if k.lower().startswith('character vox/'):
            cur[k.split('/')[1]] += 1
    say('지금 번들의 보이스: %s' % ' · '.join('%s %d' % x
                                        for x in sorted(cur.items())))
    return 0


def remove(say=print):
    import bundlechain
    bundlechain.start(STAGE, say)
    bundlechain.done(STAGE, say)
    if os.path.exists(OUT):
        os.remove(OUT)
    say('보이스를 뺐습니다. APK 를 다시 만드세요.')
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
