# -*- coding: utf-8 -*-
"""사설 서버가 들고 있는 표와 응답 뼈대를 통째로 떠서 C# 쪽에 넘긴다.

로컬 전용 APK 안에서 스키마 해석과 가격표를 다시 짜는 건 낭비이고,
무엇보다 **두 벌이 어긋날 위험**이 있다. 그래서 chacnserver.py 를 그대로
불러 값을 뜬 뒤 ChaLocalData.cs 한 파일로 굽는다.

서버 쪽 표를 고치면 이걸 다시 돌리기만 하면 로컬판도 따라온다.

  python mkskel.py
"""
import io
import json
import os
import sys

SP = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SP)
_ARGV = list(sys.argv)
sys.argv = [sys.argv[0]]          # chacnserver 가 argv[1] 을 포트로 읽는다

import chacnserver as S           # noqa: E402
import chastate as C              # noqa: E402

OUT_JSON = os.path.join(SP, 'chalocal_data.json')
OUT_CS = os.path.join(os.path.dirname(SP), 'patch', 'ChaLocalData.cs')


def gather(preset=None, pkg='', save=None):
    paths = sorted(set(S.ROUTE_CLASS) | set(S.ROUTES))
    if save:
        start = json.load(io.open(save, encoding='utf-8'))
    elif preset:
        start = C.preset(preset)
    else:
        start = C.default()
    d = {
        # 경로별 응답 뼈대 (스키마에서 뽑은 것)
        'skel': dict((p, S.auto(p)) for p in paths),
        # 세이브 파일의 시작 모양 (프리셋을 주면 그 상태)
        'default': start,
        'preset': start.get('preset') or preset or '',
        'pkg': pkg,
        # 차 번호 · 이름 · 시작 등급
        'cars': [[i, n, c] for i, n, c in C.CARS],
        'carCost': dict((str(k), list(v)) for k, v in S.CAR_COST.items()),
        'shopCars': sorted(S.SHOP_CARS),
        'gachaCars': dict((str(k), v) for k, v in S.GACHA_CARS.items()),
        'gachaOdds': [list(x) for x in S.GACHA_ODDS],
        'gachaCost': S.GACHA_COST,
        'gachaRetryCost': S.GACHA_RETRY_COST,
        'exchangeNo': dict((str(k), list(v)) for k, v in S.EXCHANGE_NO.items()),
        'goldExchange': [list(x) for x in S.GOLD_EXCHANGE],
        'tireExchange': [list(x) for x in S.TIRE_EXCHANGE],
        'tuneCost': S.TUNE_COST,
        'tuneKey': dict((str(k), v) for k, v in S.TUNE_KEY.items()),
        'classUp': dict((k, list(v)) for k, v in S.CLASS_UP.items()),
        'inviteReward': dict((str(k), list(v))
                             for k, v in S.INVITE_REWARD.items()),
        'billingItems': S.BILLING_ITEMS,
        'tradeClassValue': S.TRADE_CLASS_VALUE,
        'tradeLevelValue': dict((str(k), v)
                                for k, v in S.TRADE_LEVEL_VALUE.items()),
        'rivals': [list(x) for x in S.RIVALS],
        'knownRoots': list(S.KNOWN_ROOTS),
        'driverCount': S.DRIVER_COUNT,
        'maxGold': C.MAX_GOLD, 'maxTrophy': C.MAX_TROPHY,
        'maxTire': C.MAX_TIRE,
        'items': C.ITEMS,
        # 스킬 표(값·최대 레벨·올림값). 로컬판이 그대로 셈에 쓴다.
        'skillTab': __import__('chaskill').table(),
    }
    return d, paths


def cs_string(text):
    """C# 소스에 그대로 박을 수 있는 문자열 리터럴. 한글은 \\uXXXX 로 쓴다.

    소스 파일 인코딩에 기대지 않아야 csc 가 어떤 코드페이지에서 돌아도
    같은 결과가 나온다."""
    out = ['"']
    for ch in text:
        o = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == '\\':
            out.append('\\\\')
        elif 32 <= o < 127:
            out.append(ch)
        else:
            out.append('\\u%04x' % o)
    out.append('"')
    return ''.join(out)


def chunks(text, n=900):
    for i in range(0, len(text), n):
        yield text[i:i + n]


def main():
    preset = None
    pkg = ''
    save = None
    for i, a in enumerate(_ARGV):
        if a == '--preset' and i + 1 < len(_ARGV):
            preset = _ARGV[i + 1]
        if a == '--pkg' and i + 1 < len(_ARGV):
            pkg = _ARGV[i + 1]
        if a == '--save' and i + 1 < len(_ARGV):
            save = _ARGV[i + 1]
    d, paths = gather(preset, pkg, save)
    if save:
        print('구워 넣는 세이브: %s' % save)
    if preset:
        print('프리셋: %s' % preset)
    blob = json.dumps(d, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'))
    io.open(OUT_JSON, 'w', encoding='utf-8').write(blob)

    parts = list(chunks(blob))
    src = ['// 자동 생성 — mkskel.py 가 chacnserver.py 에서 떠 온 것이다.',
           '// 손으로 고치지 마라. 서버 표를 고쳤으면 mkskel.py 를 다시 돌려라.',
           'static class ChaLocalData',
           '{',
           '    public static string Json()',
           '    {',
           '        System.Text.StringBuilder b = new System.Text.StringBuilder(%d);'
           % (len(blob) + 16)]
    for p in parts:
        src.append('        b.Append(%s);' % cs_string(p))
    # 세이브 자리를 정할 때 쓰는 패키지 이름. JSON 을 풀기 **전에** 필요해
    # 따로 뽑아 둔다(프리셋마다 앱이 다르다).
    src += ['        return b.ToString();', '    }', '',
            '    public static string Pkg() { return %s; }' % cs_string(pkg),
            '}', '']
    io.open(OUT_CS, 'w', encoding='utf-8').write('\n'.join(src))

    have = [p for p in paths if p in S.ROUTES]
    print('경로 %d개 (손으로 짠 처리기 %d · 스키마 자동 %d)'
          % (len(paths), len(have), len(paths) - len(have)))
    print('%s  %d바이트' % (OUT_JSON, len(blob.encode('utf-8'))))
    print('%s  %d바이트 (조각 %d개)'
          % (OUT_CS, os.path.getsize(OUT_CS), len(parts)))


if __name__ == '__main__':
    main()
