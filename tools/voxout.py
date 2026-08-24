# -*- coding: utf-8 -*-
"""드라이버 보이스를 **귀로 들을 수 있게** 파일로 뽑는다.

왜 필요한가. 이 프로젝트는 소리를 들을 수 없다. 어느 목소리가 한국어이고
어느 것이 영문판인지, 톤이 맞는지는 사람이 들어야 안다. 그래서 지금 APK 에
실제로 들어가는 클립을 그대로 꺼내 준다.

**번들에서 뽑는다.** 트리(Resources)가 아니다. `Generic_Title.__ChaResLoad`
의 IL 을 보면 `Character VOX/` 로 시작하는 이름만 **번들을 먼저** 보므로,
실제로 들리는 것은 번들 쪽이다. 트리에 뭐가 들었든 상관없다.

    if (name.StartsWith("Character VOX/")) {
        v = __ChaFromBundle(name);   // 번들이 이긴다
        if (v) return v;
    }
    return Resources.Load(name) ?? __ChaFromBundle(name);

소리 데이터는 **변환하지 않고 그대로** 쓴다. 다만 확장자는 `m_Type` 이
아니라 **첫 바이트(매직)** 로 정한다 — 이 빌드의 클립은 `m_Type` 이 13
(FMOD 로는 OGGVORBIS)이라고 적혀 있지만 실제 내용은 **MP3**(`ÿó`)이고,
네 개는 `m_Type=20` 에 **WAV**(`RIFF`)다. 적힌 값을 믿으면 안 열리는 파일이
나온다.

    python tools/voxout.py            export/voice 에 뽑는다
    python tools/voxout.py --one      드라이버마다 대표 한 마디만
    python tools/voxout.py --out DIR  다른 곳에 뽑는다
"""
import argparse
import io
import os
import sys

CODE = os.path.dirname(os.path.abspath(__file__))
HERE = os.path.dirname(CODE)
sys.path.insert(0, CODE)

DAT = os.path.join(HERE, 'pack.dat')
OUT = os.path.join(HERE, 'export', 'voice')

# `Cutin/eCutinModelType` 열거형 순서 그대로. 게임 텍스트표의 `Char1..12` 와
# 짝지었다. 1~4 는 원작 기본 드라이버라 확실하고, 5~11 은 이 프로젝트가
# 복원 번들에서 끌어온 것이라 **짝이 확실하지 않다**(설명은 아래 README).
MODEL = [
    ('DOKANG', '도 강현'), ('SARA', 'Sarah Cha'), ('BIN', '빈 경유'),
    ('NAYOUBI', '나 연비'), ('PIG', None), ('GYARU', None), ('POLY', None),
    ('AMBER', None), ('ROI', None), ('HELLY', None), ('ANGRY', None),
]
BASE = ('DOKANG', 'SARA', 'BIN', 'NAYOUBI')     # 한국어로 갈아 끼운 넷

# 대표 한 마디 — 짧고 성격이 드러나는 것부터.
PICK = ('EQUIP', 'CHOICE', 'BOOST', 'END', 'COMBO1')

WHAT = {
    'EQUIP': '장착할 때', 'CHOICE': '고를 때', 'BOOST': '부스터',
    'TURBO': '터보', 'OIL': '연료', 'END': '주행 끝', 'CHECKPOINT': '체크포인트',
}


def clips(say=lambda *a: None):
    """번들 안의 VOX 클립. 이름 -> 소리 바이트."""
    from UnityPy.streams import EndianBinaryReader
    from UnityPy.files.SerializedFile import SerializedFile
    if not os.path.exists(DAT):
        raise SystemExit('pack.dat 이 없습니다')
    sf = SerializedFile(EndianBinaryReader(io.open(DAT, 'rb').read()), None)
    out = {}
    for _pid, o in sf.objects.items():
        if o.type.name != 'AudioClip':
            continue
        t = o.read_typetree()
        nm = t.get('m_Name') or ''
        if '_VOX_' not in nm:
            continue
        out[nm] = bytes(t.get('m_AudioData') or b'')
    return out


def ext(blob):
    """첫 바이트로 확장자를 정한다. `m_Type` 은 못 믿는다(위 설명)."""
    if blob[:4] == b'OggS':
        return '.ogg'
    if blob[:4] == b'RIFF':
        return '.wav'
    if blob[:3] == b'ID3' or (len(blob) > 1 and blob[0] == 0xFF
                              and (blob[1] & 0xE0) == 0xE0):
        return '.mp3'
    return '.bin'


def kr_source():
    """초기판(한국어) 원본 바이트. 어느 것이 한국어인지 가리는 데 쓴다."""
    import json
    from UnityPy.streams import EndianBinaryReader
    from UnityPy.files.SerializedFile import SerializedFile
    p = os.path.join(HERE, 'audio_kr8.json')
    d = os.path.join(HERE, '_scratch', 'kr8', 'assets', 'bin', 'Data')
    if not (os.path.exists(p) and os.path.isdir(d)):
        return {}
    out = {}
    for a in json.load(io.open(p, encoding='utf-8')):
        nm = a.get('name') or ''
        if '_VOX_' not in nm:
            continue
        sf = SerializedFile(EndianBinaryReader(
            io.open(os.path.join(d, a['file']), 'rb').read()), None)
        out[nm] = bytes(sf.objects[a['pid']].read_typetree()
                        .get('m_AudioData') or b'')
    return out


def run(out_dir, only_one=False, say=print):
    import shutil
    data = clips(say)
    kr = kr_source()
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)

    by = {}
    for nm in data:
        by.setdefault(nm.split('_VOX_')[0], []).append(nm)
    lines = []
    total = 0
    for i, (tag, label) in enumerate(MODEL):
        names = sorted(by.get(tag, []))
        if not names:
            continue
        is_kr = all(n in kr and kr[n] == data[n] for n in names)
        mark = '한국어' if is_kr else '영문'
        who = label or '(이름 미상)'
        folder = '%02d_%s_%s' % (i + 1, tag, mark)
        d = os.path.join(out_dir, folder)
        os.makedirs(d, exist_ok=True)
        take = names
        if only_one:
            take = []
            for suf in PICK:
                hit = [n for n in names if n.endswith('_' + suf)]
                if hit:
                    take = hit[:1]
                    break
            take = take or names[:1]
        for n in take:
            suf = n.split('_VOX_')[1]
            fn = '%s%s%s' % (suf, '_' + WHAT[suf] if suf in WHAT else '',
                             ext(data[n]))
            io.open(os.path.join(d, fn), 'wb').write(data[n])
            total += 1
        lines.append((folder, who, mark, len(take), len(names)))
        say('  %-28s %-12s %-4s %d개' % (folder, who, mark, len(take)))

    readme(out_dir, lines, only_one)
    say('')
    say('%s 에 %d개를 뽑았습니다.' % (out_dir, total))
    return 0


def readme(out_dir, lines, only_one):
    n_kr = sum(1 for _f, _w, m, _a, _b in lines if m == '한국어')
    t = []
    t.append('# 드라이버 보이스 — 들어 보실 것')
    t.append('')
    t.append('지금 APK 에 **실제로 들어가는** 클립을 그대로 뽑은 것입니다.')
    t.append('변환하지 않았습니다 — 게임 안에 든 바이트 그대로입니다.')
    t.append('대부분 MP3 이고 몇 개는 WAV 입니다')
    t.append('(게임 데이터에는 "Ogg" 라고 적혀 있지만 실제 내용은 다릅니다).')
    t.append('')
    t.append('## 지금 상태')
    t.append('')
    t.append('드라이버 %d명 중 **%d명이 한국어**, 나머지는 영문판입니다.'
             % (len(lines), n_kr))
    t.append('한국어인 넷은 한국 초기판(`8.apk`, 2013-01)에서 가져온 것이고,')
    t.append('나머지는 동남아/영문판에서 복원해 온 드라이버들이라 그쪽 더빙뿐입니다.')
    t.append('')
    t.append('| 폴더 | 게임 안 이름 | 말 | 뽑은 개수 |')
    t.append('|---|---|---|---|')
    for f, w, m, a, b in lines:
        t.append('| `%s` | %s | %s | %d / %d |' % (f, w, m, a, b))
    t.append('')
    t.append('## 이름이 미상인 까닭')
    t.append('')
    t.append('폴더 이름의 `DOKANG` 같은 말은 게임 코드의 `eCutinModelType`')
    t.append('열거형 순서 그대로입니다. **1~4번은 원작 기본 드라이버라 게임')
    t.append('텍스트표의 `Char1~Char4` 와 확실히 짝이 맞습니다.**')
    t.append('5번부터는 이 프로젝트가 복원 번들에서 끌어온 자리라, 목소리와')
    t.append('게임 안 이름(`Char5~Char12`)의 짝을 아직 확정하지 못했습니다.')
    t.append('들어 보시고 "이건 누구 목소리다" 싶으면 알려 주세요.')
    t.append('')
    t.append('## 파일 이름')
    t.append('')
    t.append('`<상황>.<확장자>` 입니다. `COMBO1~13` 은 연속 추월 단수입니다.')
    t.append('')
    for k, v in sorted(WHAT.items()):
        t.append('- `%s` — %s' % (k, v))
    t.append('')
    t.append('## 마음에 안 드시면')
    t.append('')
    t.append('```')
    t.append('python tools/voicefix.py        11명을 영문판으로 통일')
    t.append('python tools/voicefix.py --kr   기본 4명을 한국어로 (지금 상태)')
    t.append('python tools/voicefix.py --cn   중국판 원본(중국어)으로')
    t.append('```')
    if only_one:
        t.append('')
        t.append('_(대표 한 마디만 뽑은 것입니다. 전부 들으시려면 `--one` 없이'
                 ' 다시 돌리세요.)_')
    io.open(os.path.join(out_dir, 'README.md'), 'w',
            encoding='utf-8').write('\n'.join(t) + '\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=OUT)
    ap.add_argument('--one', action='store_true',
                    help='드라이버마다 대표 한 마디만')
    a = ap.parse_args()
    return run(a.out, a.one)


if __name__ == '__main__':
    sys.exit(main())
