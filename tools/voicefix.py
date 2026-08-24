# -*- coding: utf-8 -*-
"""기본 드라이버 4명의 보이스를 딴 판의 것으로 갈아 끼웁니다.

중국판에는 `SARA_VOX_*` `NAYOUBI_VOX_*` `BIN_VOX_*` `DOKANG_VOX_*` 넉 벌
80개가 중국어 더빙으로 들어 있습니다.

VOX 클립이 있는 곳은 세 군데입니다.

  · 중국판(x77)                    — 4명 80개, 중국어
  · survey/racechachachaforkakao   — 11명, 동남아/영문판
    (폴더 이름과 달리 차 이름이 Garuda·Hummie·Magnum 입니다)
  · **8.apk (한국 초기판, 2013-01)** — 4명 80개, **한국어**

**바로잡음 (2026-08-24)**: 예전에 "한국어 보이스는 어디에도 없다"고 적어
두었는데 틀렸습니다. 한국 마지막 정식판(7.7.0)에는 정말 하나도 없지만,
**한국 초기판 8.apk 에는 넉 벌 80개가 온전히 들어 있습니다.** 이름도
`BIN_VOX_*` `DOKANG_VOX_*` `NAYOUBI_VOX_*` `SARA_VOX_*` 로 1:1 로 맞습니다.

## 그래서 무엇을 고를 것인가

  `--kr`     기본 드라이버 4명을 **한국어**로 (한국판 복원이면 이쪽)
  (기본값)    11명을 영문판으로 통일

`--kr` 을 쓰면 기본 4명만 한국어가 되고 복원 번들에서 온 나머지 7명은
영문판 그대로라 **말이 섞입니다.** 대신 처음 만나는 드라이버(도 강현이
기본)가 한국어로 말합니다.

이름이 1:1 로 맞으므로 짝짓기는 이름으로 합니다. 소리 길이가 달라 제자리
덮어쓰기는 못 하고 파일을 통째로 다시 씁니다(다행히 보이스는 파일 하나에
클립 하나씩 들어 있습니다). 원본은 backup/ 에 남습니다.

  python voicefix.py            동남아/영문판 것으로 맞춥니다 (11명 통일)
  python voicefix.py --cn       중국판 원본으로 되돌립니다
  python voicefix.py --dry      무엇이 바뀌는지만 봅니다
"""
import io
import json
import os
import shutil
import sys

import chaassets as A

CODE = os.path.dirname(os.path.abspath(__file__))
# 도구는 tools/ 안에 있고, 작업 트리(x77 · saves · lang …)는 그 위에 있다.
HERE = os.path.dirname(CODE)
# 공급원. (트리, 색인 캐시 이름)
DONORS = {
    'kakao': (os.path.join(HERE, 'survey', 'racechachachaforkakao'),
              'audio_kakao.json'),
    'kr': (os.path.join(HERE, '_scratch', 'kr8'), 'audio_kr8.json'),
}
TARGET = os.path.join(HERE, 'x77')

# 소리 자체와 그 재생에 필요한 값들. 이것만 옮기고 이름은 그대로 둡니다.
FIELDS = ('m_AudioData', 'm_Format', 'm_Type', 'm_3D', 'm_UseHardware',
          'm_Stream', 'm_Size', 'm_Frequency', 'm_Length', 'm_Channels',
          'm_BitsPerSample')


def _index(tree, cache):
    """트리 안의 AudioClip 목록. 한 번 훑어 캐시에 남깁니다."""
    p = os.path.join(HERE, cache)
    if os.path.exists(p):
        return json.load(io.open(p, encoding='utf-8'))
    import scanaudio
    res = scanaudio.scan(tree)
    io.open(p, 'w', encoding='utf-8').write(
        json.dumps(res, ensure_ascii=False, indent=1))
    return res


def bundle_swap(which, dry=False, say=print):
    """**번들 안의** 보이스를 갈아 끼운다.

    이게 진짜 고쳐야 하는 자리다. `Generic_Title.__ChaResLoad` 의 IL 을
    읽어 보면 `Character VOX/` 로 시작하는 이름만 **번들을 먼저** 본다.

        if (name.StartsWith("Character VOX/")) {
            v = __ChaFromBundle(name);   // 번들이 이긴다
            if (v) return v;
        }
        return Resources.Load(name) ?? __ChaFromBundle(name);

    그래서 트리(Resources)에 한국어 클립을 아무리 잘 써 넣어도 번들에 같은
    이름이 있으면 **한 번도 안 쓰인다.** 실제로 그랬다 —
    `x77 트리 == 초기판 한국어 80/80` 인데 `x77 트리 == 번들 0/80` 이었다.

    번들은 알맹이(`pack.dat`)를 고쳐 다시 씌운다. `backup/bundle` 의 바탕본도
    같이 고친다 — 그래야 `addtroy` 가 바탕본을 되살려도 보이스가 안 사라진다.
    """
    import packadd
    from UnityPy.streams import EndianBinaryReader
    from UnityPy.files.SerializedFile import SerializedFile

    DONOR, cache = DONORS[which]
    src = dict((a['name'], a) for a in _index(DONOR, cache) if a['name'])
    dats = [p for p in (os.path.join(HERE, 'pack.dat'),
                        os.path.join(HERE, 'backup', 'bundle', 'pack.dat'))
            if os.path.exists(p)]
    if not dats:
        raise SystemExit('pack.dat 이 없습니다')

    n = 0
    for dat in dats:
        sf = SerializedFile(EndianBinaryReader(io.open(dat, 'rb').read()), None)
        blobs, names = {}, []
        for pid, o in sf.objects.items():
            if o.type.name != 'AudioClip':
                continue
            t = o.read_typetree()
            nm = t.get('m_Name') or ''
            if '_VOX_' not in nm or nm not in src:
                continue
            a = src[nm]
            sfile = A._sf(os.path.join(DONOR, A.DATA, a['file']))
            st = sfile.objects[a['pid']].read_typetree()
            if bytes(st.get('m_AudioData') or b'') == bytes(t.get('m_AudioData') or b''):
                continue                      # 이미 같은 소리다
            for f in FIELDS:
                if f in st and f in t:
                    t[f] = st[f]
            blobs[pid] = bytes(o.save_typetree(t))
            names.append(nm)
        if not blobs:
            say('  %s 는 이미 맞습니다' % os.path.basename(os.path.dirname(dat)))
            continue
        n = len(blobs)
        who = sorted(set(x.split('_VOX_')[0] for x in names))
        say('  %s: %d개 (%s)' % (dat, len(blobs), ' · '.join(who)))
        if dry:
            continue
        packadd.replace(dat, blobs, say)
        out = os.path.join(os.path.dirname(dat), 'pack.unity3d') \
            if 'backup' in dat else None
        packadd.wrap(say, out=out, dat=dat)
    return n


def restore():
    """중국판 원본 보이스로 되돌립니다.

    backup/ 에는 메시 백업도 같이 있으므로 **보이스가 든 파일만** 만집니다.
    (색인에서 VOX 클립이 들어 있는 파일 목록을 뽑아 씁니다)"""
    d = os.path.join(TARGET, A.DATA)
    files = set(a['file'] for a in _index(TARGET, 'audio_cn.json')
                if '_VOX_' in (a['name'] or ''))
    n = 0
    for fn in sorted(files):
        b = os.path.join(HERE, 'backup', fn + '.bak')
        if os.path.exists(b):
            shutil.copyfile(b, os.path.join(d, fn))
            n += 1
    print('보이스 %d개를 중국판 원본으로 되돌렸습니다' % n)
    if n < len(files):
        print('  (백업이 없는 것 %d개는 그대로 둡니다)' % (len(files) - n))
    return 0


def main():
    if '--cn' in sys.argv:
        return restore()
    dry = '--dry' in sys.argv
    which = 'kr' if '--kr' in sys.argv else 'kakao'
    DONOR, cache = DONORS[which]
    if not os.path.isdir(os.path.join(DONOR, A.DATA)):
        raise SystemExit(
            '공급원이 없습니다: %s\n'
            '한국 초기판을 쓰려면 8.apk 의 assets/bin/Data 를 거기에 풀어 두세요.'
            % DONOR)
    print('공급원: %s (%s)'
          % (which, '한국어 · 초기판' if which == 'kr' else '영문판 · 동남아'))
    cn = dict((a['name'], a) for a in _index(TARGET, 'audio_cn.json')
              if a['name'])
    kr = dict((a['name'], a) for a in _index(DONOR, cache)
              if a['name'])
    names = sorted(n for n in cn if '_VOX_' in n and n in kr)
    print('바꿀 보이스 %d개 (%s)'
          % (len(names), ' · '.join(sorted(set(n.split('_VOX_')[0]
                                               for n in names)))))
    if not names:
        return 1

    bdir = os.path.join(HERE, 'backup')
    os.makedirs(bdir, exist_ok=True)
    done = 0
    for i, nm in enumerate(names):
        src, dst = kr[nm], cn[nm]
        sf = A._sf(os.path.join(DONOR, A.DATA, src['file']))
        st = sf.objects[src['pid']].read_typetree()
        p = os.path.join(TARGET, A.DATA, dst['file'])
        tf = A._sf(p)
        o = tf.objects[dst['pid']]
        tt = o.read_typetree()
        n_old = len(tt.get('m_AudioData') or b'')
        for f in FIELDS:
            if f in st and f in tt:
                tt[f] = st[f]
        n_new = len(tt.get('m_AudioData') or b'')
        if dry:
            print('  %-24s %7d -> %7d B' % (nm, n_old, n_new))
            continue
        bak = os.path.join(bdir, dst['file'] + '.bak')
        if not os.path.exists(bak):
            shutil.copyfile(p, bak)
        A.replace_object(TARGET, dst['file'], dst['pid'],
                         bytes(o.save_typetree(tt)))
        done += 1
        sys.stdout.write('\r  %d/%d  %-26s' % (i + 1, len(names), nm))
        sys.stdout.flush()
    if not dry:
        print('\n트리 %d개를 바꿨습니다. 원본은 backup/ 에 있습니다.' % done)

    # **번들이 이긴다.** `Character VOX/` 는 Resources 보다 번들을 먼저 보므로
    # 여기까지 해야 실제로 들린다. (`bundle_swap` 의 설명을 보라)
    print('\n번들 쪽도 갈아 끼웁니다 — 이쪽이 실제로 들리는 자리입니다.')
    bundle_swap(which, dry)
    if not dry:
        print('\n끝났습니다. 이제 `chatool build` 로 APK 를 다시 만드세요.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
