# -*- coding: utf-8 -*-
"""APK 굽기의 **속**. 얼굴이 없습니다.

창 런처(`chaflet`)와 브라우저 런처(`chatool web`)가 똑같이 이걸 씁니다.
한쪽에만 있는 기능이 생기지 않게 하려고 갈라 두었습니다.

정하는 것은 셋입니다.

  1. 로컬 전용인가 서버 전용인가
  2. 어느 세이브를 시작 상태로 구워 넣을까
  3. (서버 전용이면) 폰이 어느 주소로 서버를 찾을까

새 차 · 맵처럼 **자산이 바뀐 것**은 세이브로 못 옮깁니다. `stale()` 이
그런 일을 알아챕니다.
"""
import io
import json
import os
import shutil
import subprocess
import time

import chahost as H
import chalog
import chatool as T

OUT = os.path.join(T.HERE, 'chachacha_revive.apk')
CONF = os.path.join(T.HERE, '.buildconf.json')

# 이것들이 APK 보다 새것이면 다시 구워야 합니다.
WATCH = [
    ('newcars.json', '새로 넣은 차 표'),
    ('packspec.txt', '번들에 담을 목록'),
    (os.path.join('bundles', 'pack.unity3d'), '복원 자산 번들'),
    (os.path.join('x77', 'assets', 'bin', 'Data',
                  'ade64ecd8944d9640bb1438deb4f6fe3'), '자동차 표'),
    (os.path.join('x77', 'assets', 'bin', 'Data',
                  '50295c6b20ff907439e2ef8aa05f9ea7'), '이름표'),
    (os.path.join('x77', 'assets', 'bin', 'Data', 'Managed',
                  'Assembly-CSharp.dll'), '게임 코드'),
]


def stale():
    """APK 보다 새로워진 것들. 비어 있으면 다시 구울 까닭이 없습니다."""
    if not os.path.exists(OUT):
        return [('(아직 APK 가 없습니다)', '')]
    apk = os.path.getmtime(OUT)
    out = []
    for rel, what in WATCH:
        p = os.path.join(T.HERE, rel)
        if os.path.exists(p) and os.path.getmtime(p) > apk:
            out.append((what, rel))
    return out


def apk_when():
    if not os.path.exists(OUT):
        return ''
    return time.strftime('%Y-%m-%d %H:%M',
                         time.localtime(os.path.getmtime(OUT)))


# ------------------------------------------------------------------ 설정
DEFAULT_CONF = {'mode': 'local', 'way': 'usb', 'host': '', 'port': '8888',
                'server_save': 'use', 'bundle': False}


def load_conf():
    c = dict(DEFAULT_CONF)
    try:
        c.update(json.load(io.open(CONF, encoding='utf-8')))
    except Exception:
        pass
    c['port'] = str(c.get('port') or '8888')
    return c


def save_conf(c):
    try:
        keep = dict((k, c.get(k, v)) for k, v in DEFAULT_CONF.items())
        io.open(CONF, 'w', encoding='utf-8').write(
            json.dumps(keep, ensure_ascii=False, indent=2))
    except Exception:
        pass


def hostport(way, host, port):
    w = H.WAY_BY_KEY.get(way) or H.WAYS[0]
    h = (w['host'] if w['fixed'] else host) or ''
    return '%s:%s' % (h.strip() or '127.0.0.1', str(port or '8888').strip())


def _plain(src, **kw):
    i = src.rfind('|')          # 뜻 가름표(`기록|주행`)는 떼어 낸다
    if i > 0:
        src = src[:i]
    return src.format(**kw) if kw else src


def ways(t=None):
    """화면에 뿌릴 붙는 방법 표."""
    return {'ways': H.ways(t), 'limit': H.limit(T.TREE),
            'now': H.read(T.TREE) or ''}


def check(mode, way, host, port, t=None):
    """굽기 전에 막을 까닭이 있으면 그 말을 돌려준다. 없으면 빈 문자열."""
    t = t or _plain
    if mode not in ('server', 'both'):
        return ''
    w = H.WAY_BY_KEY.get(way) or H.WAYS[0]
    if not w['fixed'] and not (host or '').strip():
        return t('서버 주소를 적으세요.')
    if len(hostport(way, host, port)) > H.limit(T.TREE):
        return t('주소가 자리보다 깁니다.')
    return ''


# ------------------------------------------------------------------ 새 세이브
def fresh_save():
    """새로 들어온 자산까지 표에 담아 세이브를 하나 만든다.

    차를 새로 넣었다면 기존 세이브는 그 차를 모릅니다. `chastate` 는
    `newcars.json` 을 들여올 때 한 번만 읽으므로 다시 읽힙니다."""
    import importlib
    import chastate
    importlib.reload(chastate)
    import chasaves
    importlib.reload(chasaves)
    p = chasaves.PRESETS[0]
    nm = chasaves.create('%s (새 자산)' % p['label'], p['key'])
    T.set_active(nm)
    chalog.add('save', "새 자산을 반영해 '%s' 를 만들었습니다" % nm)
    return nm


# ------------------------------------------------------------------ 번들 주소
def rebuild_dll(url, say):
    """번들 주소를 바꿔 DLL 사슬을 다시 굽는다."""
    sh = shutil.which('sh') or shutil.which('bash')
    if not sh:
        say('sh 를 못 찾아 번들 주소는 그대로 둡니다 (Git Bash 가 있으면 됩니다)')
        return False
    say('번들 주소를 %s 로 맞추고 DLL 을 다시 굽습니다…' % url)
    env = dict(os.environ, CHA_BUNDLE_URL=url, PYTHONIOENCODING='utf-8')
    r = subprocess.run([sh, 'builddll.sh'], cwd=T.HERE, env=env,
                       capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    say(((r.stdout or '') + (r.stderr or '')).strip()[-1500:])
    if r.returncode != 0:
        raise SystemExit('DLL 사슬을 다시 굽지 못했습니다')
    return True


# ------------------------------------------------------------------ 굽기
def run(say, mode='local', slot=None, install=False, way='usb', host='',
        port='8888', server_save='use', bundle=False):
    """한 벌을 굽는다. 실패하면 SystemExit 을 던진다."""
    t0 = time.time()
    slot = slot or T.active_name()
    # 'both' 도 서버로 갈 수 있으니 주소를 맞춰 둔다.
    if mode in ('server', 'both'):
        hp = hostport(way, host, port)
        say('서버 주소를 맞춥니다: %s' % hp)
        _n, msg = H.write(hp, T.TREE)
        say('  ' + msg)
        if bundle:
            rebuild_dll('http://%s/bundle/pack.unity3d' % hp, say)
        if server_save == 'keep':
            say('서버 상태는 그대로 둡니다 (chastate.json 을 안 건드립니다)')
        else:
            T.set_active(slot)
            say("서버 시작 상태를 '%s' 로 맞췄습니다" % slot)

    T.build_apk(mode, slot, OUT, install, say)
    chalog.add('build', '%s APK 를 구웠습니다'
               % {'local': '로컬', 'server': '서버'}.get(mode, '통합'),
               {'세이브': slot, '초': round(time.time() - t0),
                '주소': hostport(way, host, port) if mode == 'server' else '—',
                '설치': bool(install)})
    return {'out': OUT, 'secs': round(time.time() - t0), 'slot': slot}
