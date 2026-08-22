# -*- coding: utf-8 -*-
"""세이브 파일 살림살이. **화면이 없는 쪽**입니다.

APK 는 한 벌(`com.cjenm.chachacha.revive`)이고, 판 가르기는 전부 세이브가
합니다. 그래서 세이브를 만들고·고치고·지우고·폰과 주고받는 일이 런처의
중심입니다. 그 일감을 여기 모았습니다.

  · 프리셋      새 세이브의 밑그림 두 벌 (프리셋 01 · 02)
  · PC 쪽       saves/ 안의 `.json` 들
  · 폰 쪽       adb 로 훑어 온 세이브들 (앱 본체 + 게임 안 겹판의 칸들)

`chatool` 의 것을 다시 쓰되, 폰 쪽은 파일 하나가 아니라 **여러 개**를
다루므로 여기서 새로 씁니다(겹판이 `slot01.json` … 을 만듭니다).
"""
import io
import json
import os
import shutil
import time

import chastate as S
import chatool as T


HERE = T.HERE
SAVES = T.SAVES


# ==================================================================== 프리셋
# 이름에서 판 이름(rag · rich 따위)을 걷어냈습니다. 번호와 설명만 둡니다.
PRESETS = [
    {
        'no': 1,
        'key': 'bespontovnyj-pirozhok',
        'label': '프리셋 01',
        'tag': '처음부터',
        'desc': '아베오 한 대와 도 강현 한 명으로 시작합니다. '
                '나머지 차와 드라이버는 게임 안에서 사 모읍니다.',
        'facts': ['골드 50,000', '트로피 10', '타이어 900',
                  '자동차 1대', '드라이버 1명', '아이템 없음'],
        'note': '앱을 처음 깔았을 때, 그리고 세이브가 하나도 없을 때의 '
                '기본값입니다. 트로피는 상점에서 얼마든지 살 수 있으므로 '
                '시작이 가난해도 막히지 않습니다.',
    },
    {
        'no': 2,
        'key': 'malchiki-mazhory',
        'label': '프리셋 02',
        'tag': '전부 해금',
        'desc': '차와 드라이버를 모두 가진 상태로 시작합니다. '
                '구경하거나 시험할 때 씁니다.',
        'facts': ['골드 999,999,999', '트로피 999,999,999', '타이어 998',
                  '자동차 전부', '드라이버 12명', '아이템 99개씩'],
        'note': '강화공구상자만 1개입니다 — 클라이언트가 0/1 로 자릅니다.',
    },
]

PRESET_BY_KEY = dict((p['key'], p) for p in PRESETS)


def _plain(src, **kw):
    """옮김이를 안 준 자리의 기본값 — 원문 그대로.

    열쇠 뒤의 뜻 가름표(`기록|주행`)는 떼어 냅니다. 그래야 창 런처가
    보던 한국어가 그대로 남습니다."""
    i = src.rfind('|')
    if i > 0:
        src = src[:i]
    return src.format(**kw) if kw else src


def presets(t=None):
    """화면에 뿌릴 프리셋 표. 옮김이를 주면 그 말로 옮겨 돌려준다."""
    t = t or _plain
    out = []
    for p in PRESETS:
        q = dict(p)
        q['label'] = t(p['label'])
        q['tag'] = t(p['tag'])
        q['desc'] = t(p['desc'])
        q['note'] = t(p['note'])
        q['facts'] = [t(f) for f in p['facts']]
        out.append(q)
    return out


def preset_label(key, t=None):
    t = t or _plain
    p = PRESET_BY_KEY.get(key)
    return ('%s · %s' % (t(p['label']), t(p['tag']))) if p else (key or t('없음'))


def default_preset():
    """세이브가 하나도 없을 때 쓸 밑그림."""
    return PRESETS[0]


def make(preset_key):
    return S.preset(preset_key)


# ================================================================== PC 세이브
def names():
    return T.slots()


def path(name):
    return T.slot_path(name)


def read(name):
    return T.read_slot(name)


def write(name, data):
    T.write_slot(name, data)


def exists(name):
    return os.path.exists(path(name))


def free_name(stem):
    """`stem`, `stem 2`, `stem 3` … 중 아직 안 쓰는 이름."""
    if not exists(stem):
        return stem
    i = 2
    while exists('%s %d' % (stem, i)):
        i += 1
    return '%s %d' % (stem, i)


def create(name, preset_key):
    name = free_name(name)
    write(name, make(preset_key))
    return name


def duplicate(name, to=None):
    to = free_name(to or (name + ' 사본'))
    write(to, read(name))
    return to


def rename(name, to):
    if to == name:
        return name
    if exists(to):
        raise ValueError('같은 이름이 이미 있습니다: %s' % to)
    os.replace(path(name), path(to))
    if T.active_name() == name:
        io.open(T.ACTIVE, 'w', encoding='utf-8').write(to)
    return to


def remove(name):
    p = path(name)
    if os.path.exists(p):
        os.remove(p)
    if T.active_name() == name:
        rest = names()
        if rest:
            T.set_active(rest[0])


def export_to(name, dest):
    shutil.copyfile(path(name), dest)
    return dest


def import_from(src, name=None):
    data = json.load(io.open(src, encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError('세이브 파일이 아닙니다')
    stem = name or os.path.splitext(os.path.basename(src))[0]
    stem = free_name(stem)
    write(stem, data)
    return stem


def bootstrap():
    """세이브가 하나도 없으면 기본값 한 벌을 만들어 둔다.

    예전에는 쓰고 있던 `chastate.json` 을 들여왔는데, 그러면 '기본값'이
    그때그때 달라졌습니다. 이제는 언제나 프리셋 01 입니다."""
    os.makedirs(SAVES, exist_ok=True)
    if names():
        return None
    p = default_preset()
    write(p['label'], make(p['key']))
    io.open(T.ACTIVE, 'w', encoding='utf-8').write(p['label'])
    return p['label']


def stat(name):
    p = path(name)
    try:
        st = os.stat(p)
        return {'size': st.st_size,
                'when': time.strftime('%Y-%m-%d %H:%M',
                                      time.localtime(st.st_mtime))}
    except OSError:
        return {'size': 0, 'when': ''}


# =============================================================== 읽어 보이기
def _g(src, keys, fallback=None):
    cur = src
    for k in keys:
        if not isinstance(cur, dict):
            return fallback
        cur = cur.get(k)
    return fallback if cur is None else cur


def comma(n):
    try:
        return '{:,}'.format(int(n))
    except (TypeError, ValueError):
        return str(n)


def brief(data, t=None):
    """목록 한 줄에 붙일 짧은 요약."""
    t = t or _plain
    if not isinstance(data, dict):
        return t('읽을 수 없습니다')
    return t('골드 {gold} · 트로피 {trophy} · 차 {cars}대 · 드라이버 {drv}명',
             gold=comma(_g(data, ('player', 'gold'), 0)),
             trophy=comma(_g(data, ('player', 'trophy'), 0)),
             cars=len(data.get('carsOwned') or []),
             drv=len(data.get('driversOwned') or []))


def sections(data, t=None):
    """상세 화면에 뿌릴 [(제목, [(칸, 값)…])…].

    값 가운데 **게임의 것**(별명 · 차 이름 · 드라이버 이름 · 아이템 이름)은
    옮기지 않습니다. 도 강현은 어느 말로 보든 도 강현입니다."""
    t = t or _plain
    if not isinstance(data, dict):
        return [(t('읽을 수 없음'),
                 [(t('내용|무엇'), t('세이브 형식이 아닙니다'))])]

    pl = data.get('player') or {}
    cars = list(data.get('carsOwned') or [])
    drv = list(data.get('driversOwned') or [])
    items = data.get('items') or {}
    skills = data.get('skills') or []
    rec = data.get('records') or {}

    drv_names = dict(S.DRIVERS)
    now_drv = drv_names.get(pl.get('driver'), pl.get('driver'))

    owned_items = [(S.ITEM_LABEL.get(k, k), items.get(k, 0))
                   for k in S.ITEMS if items.get(k)]

    out = [
        (t('플레이어'), [
            (t('별명'), pl.get('nickName') or '—'),
            (t('골드'), comma(pl.get('gold', 0))),
            (t('트로피'), comma(pl.get('trophy', 0))),
            (t('타이어'), comma(pl.get('tire', 0))),
            (t('타는 차'), pl.get('car') or '—'),
            (t('드라이버'), '%s' % now_drv),
        ]),
        (t('보유'), [
            (t('자동차'), t('{n}대 / {all}대', n=len(cars), all=len(S.CARS))),
            (t('드라이버'), t('{n}명 / 12명', n=len(drv))),
            (t('아이템'),
             ' · '.join('%s %d' % x for x in owned_items) or t('없음')),
            (t('스킬'),
             t('{n}개', n=len(skills)) if skills else t('없음')),
        ]),
        (t('기록|주행'), [
            (t('주행 최고'), comma(rec.get('bestScore', 0))),
            (t('장애물 최고'), comma(rec.get('bestScoreHurdle', 0))),
            (t('최장 거리'), comma(rec.get('maxDistance', 0))),
            (t('플레이 횟수'), comma(rec.get('playCount', 0))),
        ]),
        (t('밑그림'), [
            (t('프리셋'), preset_label(data.get('preset') or '', t)),
        ]),
    ]
    return out


def car_lines(data):
    """보유 차량을 등급별로 묶어 돌려준다."""
    owned = set(data.get('carsOwned') or [])
    cls = data.get('carClass') or {}
    by = {}
    for _no, name, start in S.CARS:
        if name not in owned:
            continue
        c = cls.get(name, start)
        by.setdefault(c, []).append(name)
    order = ['R', 'S', 'A', 'B', 'C']
    return [(c, sorted(by[c])) for c in order if c in by]


# =================================================================== 폰 쪽
DEVICE_DIR = '/storage/emulated/0/Android/data/%s/files'


def device_ready():
    return T.adb_ok()


def device_list():
    return T.adb_devices()


def device_saves(t=None):
    """폰에 있는 세이브를 모두 훑는다.

    앱 본체가 쓰는 `chasave.json` 하나만이 아닙니다. 게임 안 겹판이
    `slot01.json` … 을 같은 폴더에 만들므로 그 칸들도 같이 봅니다.
    예전에 깔았던 패키지들도 함께 훑어 되찾을 수 있게 합니다."""
    t = t or _plain
    out = []
    for pkg, label in T.KNOWN_APPS:
        d = DEVICE_DIR % pkg
        r = T._run(T.adb_cmd('shell', 'ls', '-l', d))
        if r.returncode != 0:
            continue
        for ln in (r.stdout or '').splitlines():
            parts = ln.split()
            if len(parts) < 4:
                continue
            fn = parts[-1]
            if not fn.endswith('.json'):
                continue
            size = 0
            for p in parts:
                if p.isdigit() and int(p) > 64:
                    size = int(p)
            when = ' '.join(parts[-3:-1]) if len(parts) >= 4 else ''
            out.append({
                'pkg': pkg,
                'app': label,
                'file': fn,
                'remote': d + '/' + fn,
                'size': size,
                'when': when,
                'kind': t('본체') if fn == 'chasave.json' else t('게임 안 칸'),
                'current': pkg == T.PKG,
            })
    out.sort(key=lambda x: (not x['current'], x['pkg'], x['file']))
    return out


def device_read(remote, t=None):
    """폰의 세이브 하나를 임시로 받아 와 내용을 읽는다."""
    t = t or _plain
    tmp = os.path.join(SAVES, '.peek.json')
    r = T._run(T.adb_cmd('pull', remote, tmp))
    if r.returncode != 0 or not os.path.exists(tmp):
        return None, (r.stderr or r.stdout or t('가져오지 못했습니다')).strip()
    try:
        data = json.load(io.open(tmp, encoding='utf-8'))
    except Exception as e:
        return None, t('읽을 수 없습니다: {why}', why=e)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
    return data, ''


def device_pull(remote, name=None, t=None):
    """폰의 세이브를 PC 로 가져와 새 세이브로 만든다."""
    data, err = device_read(remote, t)
    if data is None:
        return None, err
    stem = free_name(name or os.path.splitext(os.path.basename(remote))[0])
    write(stem, data)
    return stem, ''


def device_push(name, remote=None):
    """PC 의 세이브를 폰으로 올린다. 자리를 안 주면 앱 본체 자리로."""
    remote = remote or (DEVICE_DIR % T.PKG) + '/chasave.json'
    T._run(T.adb_cmd('shell', 'mkdir', '-p', os.path.dirname(remote)))
    r = T._run(T.adb_cmd('push', path(name), remote))
    ok = r.returncode == 0
    return ok, ((r.stdout or '') + (r.stderr or '')).strip()


def device_remove(remote, t=None):
    t = t or _plain
    r = T._run(T.adb_cmd('shell', 'rm', '-f', remote))
    ok = r.returncode == 0
    msg = ((r.stdout or '') + (r.stderr or '')).strip()
    if not ok and 'Permission denied' in msg:
        msg = t('안드로이드 11 이후로는 다른 앱의 Android/data 를 shell 이 '
                '지울 수 없습니다. 앱을 지웠다 다시 깔아야 합니다.')
    return ok, msg
