# -*- coding: utf-8 -*-
"""화면에 쓰는 **말**. 언어를 갈아 끼웁니다.

열쇠는 **한국어 원문 그대로**입니다. 이렇게 하면

  · 새 언어를 붙일 때 `lang/en.json` 을 복사해 값만 바꾸면 됩니다.
  · 번역이 빠진 자리는 한국어로 나오므로 **눈에 바로 띕니다**.
  · 코드에서 `t('세이브')` 라고 읽히므로 무슨 말인지 열쇠만 봐도 압니다.

    lang/
      en.json   {"_name": "English", "세이브": "Saves", …}
      kr.json   {"_name": "한국어",  …}

자리 채우기는 중괄호를 씁니다.

    t('세이브 {n}개를 찾았습니다', n=3)

고른 언어와 화면 밝기는 `.uiconf.json` 에 남아 다음에 켤 때 그대로 옵니다.
"""
import io
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(HERE, 'lang')
CONF = os.path.join(HERE, '.uiconf.json')

DEFAULT_LANG = 'kr'         # 열쇠가 곧 한국어라 번역이 없어도 되는 쪽
DEFAULT_THEME = 'system'    # system · light · dark

_CACHE = {}


# ------------------------------------------------------------------ 파일
def codes():
    """쓸 수 있는 언어. `lang/` 에 json 을 하나 더 넣으면 바로 늘어납니다."""
    out = []
    if os.path.isdir(DIR):
        for f in sorted(os.listdir(DIR)):
            if not f.endswith('.json'):
                continue
            code = f[:-5]
            out.append({'code': code, 'name': load(code).get('_name', code)})
    if not any(c['code'] == DEFAULT_LANG for c in out):
        out.insert(0, {'code': DEFAULT_LANG, 'name': '한국어'})
    return out


def load(code):
    """그 언어의 표. 없으면 빈 표(= 한국어 그대로)."""
    if code in _CACHE:
        return _CACHE[code]
    p = os.path.join(DIR, '%s.json' % code)
    try:
        d = json.load(io.open(p, encoding='utf-8'))
        if not isinstance(d, dict):
            d = {}
    except Exception:
        d = {}
    _CACHE[code] = d
    return d


def reload():
    """번역 파일을 고쳤을 때 다시 읽힙니다."""
    _CACHE.clear()


# ------------------------------------------------------------------ 설정
# 마지막으로 제대로 읽은 설정. 읽기가 한 번 어긋났다고 기본값으로
# 되돌아가면 **고른 언어가 소리 없이 날아간다** — 그래서 붙들어 둡니다.
_LAST = {}


def conf():
    # 'device' 는 adb 로 고른 기기의 일련번호. 언어와 한 파일에 둡니다 —
    # 셋 다 '이 PC 에서 런처를 어떻게 쓰는가' 라 자리가 같습니다.
    c = {'lang': DEFAULT_LANG, 'theme': DEFAULT_THEME, 'device': ''}
    c.update(_LAST)
    got = None
    for _ in range(3):          # 갈아 끼우는 찰나에 읽으면 윈도우가 막는다
        try:
            got = json.load(io.open(CONF, encoding='utf-8'))
            break
        except FileNotFoundError:
            break
        except Exception:
            time.sleep(0.01)
    if isinstance(got, dict):
        c.update(got)
        _LAST.update(c)
    if c.get('theme') not in ('system', 'light', 'dark'):
        c['theme'] = DEFAULT_THEME
    return c


def save_conf(**kw):
    """설정을 갈무리한다. **통째로 썼다가 갈아 끼운다.**

    예전에는 파일을 열어 그 자리에 썼다. 그 사이에 다른 쪽(런처와 CLI 가
    함께 돌 때)이 읽으면 반만 쓰인 파일을 보게 되고, `conf()` 는 그걸 조용히
    버리고 기본값을 돌려준다. 그다음 저장이 그 기본값을 그대로 굳혀
    **고른 언어가 소리 없이 한국어로 되돌아갔다.** 실제로 겪었다."""
    c = conf()
    for k in ('lang', 'theme'):
        if kw.get(k):
            c[k] = kw[k]
    if 'device' in kw:          # 빈 값도 뜻이 있다 — '아무거나' 로 되돌리기
        c['device'] = kw['device'] or ''
    try:
        tmp = '%s.%d.tmp' % (CONF, os.getpid())
        io.open(tmp, 'w', encoding='utf-8').write(
            json.dumps(c, ensure_ascii=False, indent=2))
        for _ in range(5):
            try:
                os.replace(tmp, CONF)
                break
            except OSError:     # 다른 쪽이 읽는 중 — 잠깐 뒤에 다시
                time.sleep(0.01)
    except Exception:
        pass
    _LAST.update(c)
    return c


def cur():
    return conf()['lang']


def use(code):
    """이 언어를 쓰기로 하고 갈무리한다."""
    return save_conf(lang=code)['lang']


# ------------------------------------------------------------------ 옮기기
def _fill(s, kw):
    if not kw:
        return s
    try:
        return s.format(**kw)
    except Exception:
        return s


def t(src, **kw):
    """지금 고른 언어로. 없으면 원문(한국어) 그대로."""
    return tr(cur(), src, **kw)


def bare(src):
    """열쇠에서 **뜻 가름표**를 떼어 낸 한국어 원문.

    한국어에서 같은 말이 다른 언어에서 갈리는 자리가 있습니다. '기록' 은
    런처가 한 일(History)이면서 세이브의 주행 기록(Records)입니다. 그럴
    때만 열쇠 뒤에 `|주행` 처럼 붙여 갈라 둡니다. 한국어로 볼 때는 떼어
    내므로 화면에는 그대로 '기록' 이 나옵니다."""
    i = src.rfind('|')
    return src[:i] if i > 0 else src


def tr(code, src, **kw):
    """언어를 집어서 옮긴다. 서버가 여러 요청을 받을 때 쓰기 좋습니다."""
    got = load(code).get(src)
    if not (isinstance(got, str) and got):
        got = bare(src)
    return _fill(got, kw)


def maker(code):
    """`t = chalang.maker(code)` 로 받아 쓰는 옮김이."""
    def go(src, **kw):
        return tr(code, src, **kw)
    return go


def pack(code):
    """화면(자바스크립트)에 통째로 넘길 표."""
    d = dict(load(code))
    d.pop('_name', None)
    return d


# ------------------------------------------------------------------ 만들기
def dump_template(code, keys, name=None):
    """새 언어 뼈대를 만든다. 값이 비어 있으면 한국어로 나옵니다."""
    os.makedirs(DIR, exist_ok=True)
    p = os.path.join(DIR, '%s.json' % code)
    old = load(code)
    out = {'_name': name or old.get('_name') or code}
    for k in keys:
        out[k] = old.get(k, '')
    io.open(p, 'w', encoding='utf-8').write(
        json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
    reload()
    return p
