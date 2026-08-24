# -*- coding: utf-8 -*-
"""주간순위의 **프로필 사진**을 한국 초기판 데모 화면에서 오려 낸다.

한국 초기판(1.2.3, 유니티 3.5.6f4)의 `LOBBY_ATLAS` 에는 로비 화면이 통째로
**그림으로** 그려져 있다. 그 주간순위 칸에 개발 당시 쓰던 이름 · 기록 ·
프로필 사진이 그대로 박혀 있다(문자열이 아니라 픽셀이라 문자열 검색으로는
안 잡힌다).

    1 한지윤 25345M   2 김호근 1345M   3 하흥희 1145M
    4 신용석   945M   5 차요한  745M

사진은 인물 사진 · 야구공 · 검정 컨버터블 · 스피커 · 인물 사진이다. 사내에서
아무 그림이나 끼워 둔 티가 난다. 그 다섯 장을 80x80 으로 오려 낸다.

## 게임에 넣는 것은 접었다

`CRSystem/RankData` 에 `imageUrl` 칸이 있고 화면마다 있는
`LoadingProfileImage(url)` 코루틴이 `new WWW(url)` 로 받아 `UITexture` 에
입힌다. 그런데 그 칸을 채우는 곳은 `CRSystem::SetDefaultRankData` 뿐이고,
거기서 **소셜 친구 정보에서만** 가져온다 — 우리가 응답 JSON 에 넣어 줘도
쳐다보지 않는다(실측).

그래서 그 메서드에 IL 을 덧대 채워 보았는데 **두 번 다 모노 JIT 이 죽었다**
(`localfix` 끝자리 · `rankfix` 블록, 둘 다 네이티브 크래시). 이 프로젝트가
`tunnelfix.cs` 에 적어 둔 "중간에 끼워 넣으면 모노 JIT 이 죽는다"와 같은
자리로 보인다. 얻는 것에 비해 위험이 커서 접었다 — 이름과 기록만 살렸다.

이 도구는 **그림을 꺼내 보는 용도**로 남긴다. `export/rank/` 에 떨어지고
APK 에는 안 실린다.

    python tools/rankphoto.py          export/rank 에 다섯 장을 뽑는다
    python tools/rankphoto.py --scan   자리만 보여 준다
"""
import argparse
import io
import os
import sys

CODE = os.path.dirname(os.path.abspath(__file__))
HERE = os.path.dirname(CODE)
sys.path.insert(0, CODE)

KR8 = os.path.join(HERE, '_scratch', 'kr8', 'assets', 'bin', 'Data')
DST = os.path.join(HERE, 'export', 'rank')
ATLAS = 'LOBBY_ATLAS'

# 실측한 자리. 사진 칸은 검은 테두리 안쪽 80x80 이고 줄 간격은 116 이다.
X, Y0, SIZE, PITCH = 127, 1454, 80, 116
WHO = ['한지윤', '김호근', '하흥희', '신용석', '차요한']


def sheet():
    import UnityPy
    from PIL import Image
    for fn in sorted(os.listdir(KR8)):
        p = os.path.join(KR8, fn)
        if not os.path.isfile(p) or os.path.getsize(p) < 100000:
            continue
        try:
            env = UnityPy.load(p)
        except Exception:
            continue
        for o in env.objects:
            if o.type.name != 'Texture2D':
                continue
            try:
                t = o.read_typetree()
            except Exception:
                continue
            if t['m_Name'] == ATLAS:
                im = o.read().image.convert('RGBA')
                return Image.alpha_composite(
                    Image.new('RGBA', im.size, (0, 0, 0, 255)), im).convert('RGB')
    raise SystemExit('%s 를 못 찾았습니다 (초기판 트리가 있습니까?)' % ATLAS)


def cuts():
    im = sheet()
    return [(WHO[i], im.crop((X, Y0 + PITCH * i, X + SIZE,
                              Y0 + PITCH * i + SIZE)))
            for i in range(len(WHO))]


def install(say=print):
    os.makedirs(DST, exist_ok=True)
    for i, (who, im) in enumerate(cuts()):
        p = os.path.join(DST, '%d.png' % (i + 1))
        im.save(p)
        say('  %d.png  %-8s %dx%d  %d바이트'
            % (i + 1, who, im.width, im.height, os.path.getsize(p)))
    say('%s 에 %d장 뽑았습니다 (APK 에는 안 실립니다).'
        % (os.path.relpath(DST, HERE), len(WHO)))
    return 0


def scan(say=print):
    from PIL import Image
    got = cuts()
    out = Image.new('RGB', (len(got) * (SIZE + 8), SIZE + 8), (30, 30, 34))
    for i, (_w, im) in enumerate(got):
        out.paste(im, (i * (SIZE + 8) + 4, 4))
    p = os.path.join(HERE, 'work_troy', 'kr8_photos.png')
    if os.path.isdir(os.path.dirname(p)):
        out.save(p)
        say('미리보기: %s' % os.path.relpath(p, HERE))
    for i, (who, im) in enumerate(got):
        say('  %d  %-8s (%d,%d) %dx%d'
            % (i + 1, who, X, Y0 + PITCH * i, im.width, im.height))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scan', action='store_true')
    a = ap.parse_args()
    return scan() if a.scan else install()


if __name__ == '__main__':
    sys.exit(main())
