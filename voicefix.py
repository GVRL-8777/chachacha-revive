# -*- coding: utf-8 -*-
"""기본 드라이버 4명의 보이스를 딴 판의 것으로 갈아 끼웁니다.

중국판에는 `SARA_VOX_*` `NAYOUBI_VOX_*` `BIN_VOX_*` `DOKANG_VOX_*` 넉 벌
80개가 중국어 더빙으로 들어 있습니다.

**한국어 드라이버 보이스는 어디에도 없습니다.** 가진 빌드를 전부 훑은
결과 VOX 클립이 있는 곳은 두 군데뿐입니다.
  · 중국판(x77)                    — 4명, 중국어
  · survey/racechachachaforkakao   — 11명, **동남아/영문판**
    (폴더 이름과 달리 차 이름이 Garuda·Hummie·Magnum 입니다)
진짜 한국판 `kr`(수리카·해미·매그넘)에는 VOX 가 한 개도 없습니다.
7.7.0 에서 드라이버 보이스가 통째로 빠진 것으로 보입니다.

그래서 이 도구가 하는 일은 "한국어로 바꾸기"가 아니라
**나머지 7명과 말을 맞추기** 입니다. 복원 번들에 들어 있는 다른 캐릭터
보이스도 같은 동남아/영문판에서 왔기 때문입니다.

**정한 것 (2026-08-21)**: 한국어가 없으니 영문판으로 간다.
지금 빌드는 11명이 모두 영문판 더빙이다. 되돌릴 이유가 생기면 `--cn`.

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

HERE = os.path.dirname(os.path.abspath(__file__))
DONOR = os.path.join(HERE, 'survey', 'racechachachaforkakao')
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
    cn = dict((a['name'], a) for a in _index(TARGET, 'audio_cn.json')
              if a['name'])
    kr = dict((a['name'], a) for a in _index(DONOR, 'audio_kakao.json')
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
        print('\n%d개를 한국어로 바꿨습니다. 원본은 backup/ 에 있습니다.' % done)
        print("이제 `chatool build` 로 APK 를 다시 만드세요.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
