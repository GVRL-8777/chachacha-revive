# -*- coding: utf-8 -*-
"""여러 APK 에서 같은 이름의 Texture2D 중 가장 큰 것을 골라 tex8/ 에 PNG 로 뽑는다.
   7.7.0 은 저해상도/빈 껍데기만 갖고 있으므로, 다른 배포판의 원본을 서버가 내려줄 용도."""
import os, sys, collections, UnityPy

SRCS = [
    ('kakao', 'survey/racechachachaforkakao/assets/bin/Data'),
    ('cn',    'survey/5577.com.cjenm.chachachacn/assets/bin/Data'),
    ('v131',  'x8f/assets/bin/Data'),
]
WANT = [w.lower() for w in sys.argv[1:]] if len(sys.argv) > 1 else None
OUT = 'tex8'
os.makedirs(OUT, exist_ok=True)

best = {}          # 이름(소문자) -> (넓이, 소스, reader)
for tag, d in SRCS:
    if not os.path.isdir(d):
        print("건너뜀(없음):", d)
        continue
    n = 0
    for f in os.listdir(d):
        p = os.path.join(d, f)
        if not os.path.isfile(p):
            continue
        try:
            env = UnityPy.load(p)
        except Exception:
            continue
        for r in env.objects:
            if r.type.name != "Texture2D":
                continue
            try:
                t = r.read()
            except Exception:
                continue
            nm = (t.m_Name or "").strip()
            if not nm:
                continue
            key = nm.lower()
            if WANT and not any(w in key for w in WANT):
                continue
            area = int(t.m_Width) * int(t.m_Height)
            if area <= 0:
                continue
            if key not in best or area > best[key][0]:
                best[key] = (area, tag, nm, t)
            n += 1
    print("%s: 후보 %d" % (tag, n))

print("\n최종 선택 %d개" % len(best))
saved = 0
for key, (area, tag, nm, t) in sorted(best.items()):
    try:
        out = os.path.join(OUT, nm + '.png')
        t.image.save(out)
        saved += 1
        if saved <= 40:
            print("  %-32s %-6s %dx%d" % (nm, tag, t.m_Width, t.m_Height))
    except Exception as e:
        print("  %-32s 저장 실패 %s" % (nm, type(e).__name__))
print("저장 %d개 -> %s/" % (saved, OUT))
