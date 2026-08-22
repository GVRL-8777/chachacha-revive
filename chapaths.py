# -*- coding: utf-8 -*-
"""원본 APK 가 어디 있는지 **스스로 찾습니다.**

예전에는 스크립트마다 `D:/어딘가/CCC_fK_v7.7.0.apk` 처럼 만든 사람의
경로가 박혀 있었습니다. 남이 받아 쓰려면 그 줄들을 일일이 고쳐야 했습니다.
이제 안 고쳐도 됩니다.

찾는 차례
  1. 환경변수 `CHA_APK_DIR`
  2. 스크립트 폴더 안의 `apk/`
  3. 스크립트 폴더 자체
  4. 그 부모 폴더

파일 이름은 배포처마다 제각각이라 **여러 이름을 두고 찾습니다.**
못 찾으면 무엇을 어디에 두면 되는지 알려 주고 멈춥니다.

    import chapaths
    cn = chapaths.apk('cn')          # 중국판 (없으면 오류)
    kr = chapaths.apk('kr', need=False)   # 없으면 None
"""
import glob
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# 열쇠 -> (사람이 읽을 이름, 찾아볼 파일 이름들)
#
# 앞에 있는 이름부터 봅니다. 별표는 글로브입니다.
KNOWN = {
    'cn': ('중국판 com.cjenm.chachachacn 1.2.1', [
        '5577.com.cjenm.chachachacn.apk',
        '*chachachacn*.apk',
    ]),
    'kr': ('한국판 com.cjenm.chachacha 7.7.0', [
        'CCC_fK_v7.7.0.apk',
        'CCC_fK*.apk',
        '*chachacha*7.7*.apk',
    ]),
    'kakao': ('카카오판 com.cjenm.chachacha_inni 1.4.0', [
        'racechachachaforkakao.apk',
        '*Race*Cha*Cha*Cha*for*Kakao*.apk',
        '*chachacha_inni*.apk',
    ]),
    'line': ('LINE GoGoGo 1.0.3 (한국어 문자열표)', [
        'LINE_GoGoGo-1.0.3.apk',
        'LINE_GoGoGo*.apk',
        '*LGCAR*.apk',
    ]),
    'gogo': ('GoGoGo Racer 1.4.3 (맵 이식원)', [
        'gogogoracer-1-4-3.apk',
        'gogogoracer*.apk',
        'YX_com.netmarble.chachachaf.apk',
    ]),
    'v131': ('다함께 차차차 1.3.1', [
        '8.apk',
    ]),
}


def dirs():
    """APK 가 있을 만한 자리를 차례로."""
    out = []
    env = os.environ.get('CHA_APK_DIR')
    if env:
        out += [p for p in env.split(os.pathsep) if p]
    out.append(os.path.join(HERE, 'apk'))
    out.append(HERE)
    out.append(os.path.dirname(HERE))
    seen, keep = set(), []
    for d in out:
        d = os.path.abspath(d)
        if d not in seen and os.path.isdir(d):
            seen.add(d)
            keep.append(d)
    return keep


def find(patterns):
    """이름 후보들로 첫 번째로 걸리는 파일을 돌려준다."""
    for d in dirs():
        for pat in patterns:
            hit = sorted(glob.glob(os.path.join(d, pat)))
            hit = [h for h in hit if os.path.getsize(h) > 1000000]
            if hit:
                return hit[0]
    return None


def apk(key, need=True):
    """열쇠로 원본 APK 를 찾는다. 없으면 무엇을 어디 두면 되는지 알려 준다."""
    if key not in KNOWN:
        raise KeyError('모르는 열쇠: %s (아는 것: %s)'
                       % (key, ' · '.join(sorted(KNOWN))))
    label, pats = KNOWN[key]
    got = find(pats)
    if got or not need:
        return got
    raise SystemExit(
        '\n원본 APK 를 못 찾았습니다: %s\n'
        '  찾아본 이름 : %s\n'
        '  찾아본 자리 :\n%s\n'
        '\n아래 가운데 하나를 하세요.\n'
        '  · 그 APK 를 위 자리 중 아무 데나 둡니다\n'
        '  · 또는 환경변수로 자리를 알려 줍니다\n'
        '        set CHA_APK_DIR=D:\\어디에\\두었는지      (윈도우)\n'
        '        export CHA_APK_DIR=/어디에/두었는지        (그 밖)\n'
        % (label, ' · '.join(pats),
           '\n'.join('      %s' % d for d in dirs())))


def have(key):
    return apk(key, need=False) is not None


def report():
    """어느 것이 있고 없는지 한눈에."""
    print('APK 를 찾는 자리:')
    for d in dirs():
        print('  %s' % d)
    print()
    for k in sorted(KNOWN):
        label, _pats = KNOWN[k]
        got = apk(k, need=False)
        print('  %-6s %-46s %s'
              % (k, label, os.path.basename(got) if got else '— 없음'))


if __name__ == '__main__':
    report()
