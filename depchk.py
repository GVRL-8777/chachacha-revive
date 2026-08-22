# -*- coding: utf-8 -*-
"""이식한 자산의 의존 파일들이 대상에서 제대로 해석되는지 본다.

마젠타 렌더 = 셰이더 미해결. 의존 파일 중 '이름은 같은데 내용이 다른' 것이 있으면
그 참조가 엉뚱한 자산을 가리키게 된다.
"""
import os, hashlib, UnityPy

SRC = 'survey/gogogoracer-1-4-3/assets/bin/Data'
DST = 'survey/5577.com.cjenm.chachachacn/assets/bin/Data'
ROOT = '32f46795bf14050449f8d447cf9158b5'   # gbeach01 data 파일


def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()[:12]


def contents(d, f):
    p = os.path.join(d, f)
    if not os.path.isfile(p):
        return None
    try:
        env = UnityPy.load(p)
    except Exception:
        return '(열기실패)'
    out = []
    for r in env.objects:
        try:
            nm = r.read().m_Name
        except Exception:
            nm = ''
        out.append("%s:%s(%s)" % (r.path_id, r.type.name, nm))
    return ', '.join(out[:6])


seen = set()


def walk(f, depth=0):
    if f in seen or depth > 3:
        return
    seen.add(f)
    sp = os.path.join(SRC, f)
    if not os.path.isfile(sp):
        return
    inds = os.path.isfile(os.path.join(DST, f))
    mark = ''
    if inds:
        same = md5(sp) == md5(os.path.join(DST, f))
        mark = '대상에 있음/' + ('동일' if same else '**내용 다름**')
    else:
        mark = '대상에 없음(복사 필요)'
    print("%s%s  %s" % ('  ' * depth, f[:20], mark))
    print("%s     소스: %s" % ('  ' * depth, contents(SRC, f)))
    if inds:
        print("%s     대상: %s" % ('  ' * depth, contents(DST, f)))
    try:
        env = UnityPy.load(sp)
        af = env.objects[0].assets_file if env.objects else None
        for e in getattr(af, 'externals', []):
            walk(os.path.basename(e.path), depth + 1)
    except Exception:
        pass


walk(ROOT)
