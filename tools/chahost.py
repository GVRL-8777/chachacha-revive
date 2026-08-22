# -*- coding: utf-8 -*-
"""서버판이 붙을 **주소**를 바꿉니다.

주소는 DLL 이 아니라 자산 하나(`17332001ecdfef142a24e3da1ae0ca58`)에
들어 있습니다. 길이를 앞에 적어 두는 문자열 두 개입니다.

    http://127.0.0.1:8888/xxxxxxxxx/     (32자)
    http://127.0.0.1:8888/xxxxxxxxxx/    (33자)

`xxxx` 는 **빈 칸 채우기**입니다. 중국판 클라이언트가 이 뒤에 제 경로를
이어 붙이는데, 서버가 `normalize()` 로 잉여 세그먼트를 잘라내므로 몇 자든
상관없습니다. 그래서 주소를 바꿀 때는 이 채움 글자 수만 늘였다 줄이면
**파일 길이가 그대로 유지됩니다.** 직렬화 파일을 다시 쓸 필요가 없습니다.

번들 주소는 이쪽이 아니라 `tunnelfix.exe` 의 넷째 인자입니다. 그건
`builddll.sh` 가 굽습니다.
"""
import io
import os
import re
import struct

ASSET = '17332001ecdfef142a24e3da1ae0ca58'
REL = os.path.join('assets', 'bin', 'Data', ASSET)

# `http://` + 주소 + `/` + 채움 + `/`
PAT = re.compile(rb'http://([\x20-\x7e]{1,40}?)/(x*)/')
MIN_FILL = 1        # 채움을 0 으로 두면 `//` 가 되어 버린다


def asset_path(tree='x77'):
    return os.path.join(tree, REL)


def _spots(d):
    """(시작, 전체길이, 주소) 세 쌍의 목록. 길이 앞머리까지 확인한다."""
    out = []
    for m in PAT.finditer(d):
        i, j = m.start(), m.end()
        if i < 4:
            continue
        want = struct.unpack('<i', d[i - 4:i])[0]
        if want != j - i:            # 길이 앞머리가 안 맞으면 남의 문자열
            continue
        out.append((i, want, m.group(1).decode('ascii')))
    return out


def read(tree='x77'):
    """지금 박혀 있는 주소. 두 자리가 다르면 첫 자리를 돌려준다."""
    p = asset_path(tree)
    if not os.path.exists(p):
        return None
    spots = _spots(io.open(p, 'rb').read())
    return spots[0][2] if spots else None


def limit(tree='x77'):
    """넣을 수 있는 주소의 최대 길이. 짧은 쪽 자리에 맞춥니다."""
    p = asset_path(tree)
    if not os.path.exists(p):
        return 0
    spots = _spots(io.open(p, 'rb').read())
    if not spots:
        return 0
    # 전체 = len('http://') + 주소 + len('/') + 채움 + len('/')
    return min(n for _i, n, _h in spots) - 7 - 2 - MIN_FILL


def write(hostport, tree='x77', t=None):
    """주소를 바꾼다. 파일 길이는 그대로 둔다.

    돌려주는 값은 (바꾼 자리 수, 알림글)."""
    t = t or _plain
    p = asset_path(tree)
    if not os.path.exists(p):
        raise IOError(t('주소 자산이 없습니다: {p}', p=p))
    hostport = (hostport or '').strip().strip('/')
    if hostport.startswith('http://'):
        hostport = hostport[7:]
    if not hostport:
        raise ValueError('주소가 비었습니다')
    if '/' in hostport:
        raise ValueError('주소에는 host:port 만 적습니다 (경로는 뺍니다)')

    d = bytearray(io.open(p, 'rb').read())
    spots = _spots(bytes(d))
    if not spots:
        raise ValueError('주소 자리를 찾지 못했습니다')

    for i, total, _old in spots:
        fill = total - 7 - len(hostport) - 2
        if fill < MIN_FILL:
            raise ValueError(
                '주소가 %d자인데 이 자리는 최대 %d자까지 들어갑니다. '
                '더 짧은 이름이나 IP 를 쓰세요.'
                % (len(hostport), total - 7 - 2 - MIN_FILL))
        new = ('http://%s/%s/' % (hostport, 'x' * fill)).encode('ascii')
        assert len(new) == total
        d[i:i + total] = new

    io.open(p, 'wb').write(bytes(d))
    return len(spots), t('주소를 {host} 로 바꿨습니다 (자리 {n}곳)',
                        host=hostport, n=len(spots))


# --------------------------------------------------------------- 붙는 방법
# 서버를 어디에 세우느냐에 따라 폰이 쓸 주소가 달라집니다.
WAYS = [
    {
        'no': 2,
        'key': 'usb',
        'label': 'USB 직결',
        'host': '127.0.0.1',
        'desc': 'PC 와 USB 로 이은 채로만 붙습니다. 공유기도 IP 도 필요 '
                '없어 시험할 때 가장 편합니다.',
        'steps': ['PC 에서 `python chacnserver.py` 를 띄웁니다',
                  '`adb reverse tcp:8888 tcp:8888` 을 한 번 실행합니다',
                  '기기를 다시 꽂을 때마다 되돌림 터널을 다시 엽니다'],
        'fixed': True,
    },
    {
        'no': 3,
        'key': 'lan',
        'label': '같은 공유기',
        'host': '',
        'desc': '집 안에서 PC 를 서버로 씁니다. PC 의 IP 가 바뀌면 APK 를 '
                '다시 구워야 합니다.',
        'steps': ['PC 의 랜 IP 를 적습니다 (예: 192.168.0.10)',
                  '방화벽에서 그 포트를 열어 둡니다',
                  '폰이 같은 공유기에 붙어 있어야 합니다'],
        'fixed': False,
    },
    {
        'no': 4,
        'key': 'mesh',
        'label': '사설 메시',
        'host': '',
        'desc': 'Tailscale 같은 가상 사설망에 PC 와 폰을 넣습니다. 공유기 '
                '설정 없이 밖에서도 붙고, 주소가 고정입니다.',
        'steps': ['PC 와 폰에 같은 메시를 깔고 같은 계정으로 붙입니다',
                  'PC 의 메시 IP 를 적습니다 (예: 100.101.102.103)',
                  '이름이 길면 자리가 모자라니 IP 를 쓰는 편이 낫습니다'],
        'fixed': False,
    },
    {
        'no': 5,
        'key': 'cloud',
        'label': '클라우드',
        'host': '',
        'desc': '늘 켜져 있는 서버에 올립니다. 여럿이 쓰려면 서버에 계정과 '
                '인증을 붙여야 합니다 — 지금 서버는 한 사람용입니다.',
        'steps': ['서버에 chacnserver.py 와 bundles/ 를 올립니다',
                  '공개 IP 나 도메인을 적습니다',
                  '평문 HTTP 입니다. 아무나 닿을 수 있는 자리에 두지 마세요'],
        'fixed': False,
    },
]

WAY_BY_KEY = dict((w['key'], w) for w in WAYS)


def _plain(src, **kw):
    i = src.rfind('|')          # 뜻 가름표(`기록|주행`)는 떼어 낸다
    if i > 0:
        src = src[:i]
    return src.format(**kw) if kw else src


def ways(t=None):
    """화면에 뿌릴 붙는 방법 표. 옮김이를 주면 그 말로 옮겨 돌려준다."""
    t = t or _plain
    out = []
    for w in WAYS:
        q = dict(w)
        q['label'] = t(w['label'])
        q['desc'] = t(w['desc'])
        q['steps'] = [t(x) for x in w['steps']]
        out.append(q)
    return out
