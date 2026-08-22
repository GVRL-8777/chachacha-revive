# -*- coding: utf-8 -*-
"""AudioClip 객체의 실제 필드 구성을 들여다본다."""
import os, UnityPy

SRC = 'survey/racechachachaforkakao/assets/bin/Data'
for f in sorted(os.listdir(SRC)):
    p = os.path.join(SRC, f)
    if not os.path.isfile(p):
        continue
    try:
        env = UnityPy.load(p)
    except Exception:
        continue
    for r in env.objects:
        if r.type.name != 'AudioClip':
            continue
        c = r.read()
        nm = (c.m_Name or '')
        if 'helly_vox' not in nm.lower():
            continue
        print("클립:", nm, "| 파일:", f)
        for a in dir(c):
            if a.startswith('_'):
                continue
            try:
                v = getattr(c, a)
            except Exception:
                continue
            if callable(v):
                continue
            if isinstance(v, (bytes, bytearray)):
                print("   %-22s bytes[%d] head=%r" % (a, len(v), bytes(v[:8])))
            elif isinstance(v, (int, float, str, bool)) or v is None:
                print("   %-22s %r" % (a, v))
            else:
                print("   %-22s %s" % (a, type(v).__name__))
        # 같은 폴더에 resS 가 있는지
        print("   같은 파일명+.resS 존재:", os.path.exists(p + '.resS'))
        raise SystemExit
