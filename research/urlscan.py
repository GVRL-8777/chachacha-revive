# -*- coding: utf-8 -*-
"""배포판 자산에서 http(s) URL 을 전부 뽑는다(에셋번들 CDN 주소를 찾기 위해)."""
import io, os, re, sys, glob
pat = re.compile(rb'https?://[A-Za-z0-9_.:/%\-]{6,120}')
for D, L in [('survey/5577.com.cjenm.chachachacn/assets/bin/Data', '중국판'),
             ('survey/racechachachaforkakao/assets/bin/Data', '카카오/인니'),
             ('survey/gogogoracer-1-4-3/assets/bin/Data', 'gogo 1.4.3'),
             ('survey/gogo142/assets/bin/Data', 'gogo 1.4.2'),
             ('survey/line103/assets/bin/Data', 'LINE 1.0.3'),
             ('survey/8/assets/bin/Data', '8.apk'),
             ('survey/CCC_fK_v7.7.0/assets/bin/Data', '7.7.0')]:
    hits = set()
    for f in glob.glob(os.path.join(D, '*')):
        if not os.path.isfile(f) or '.split' in f:
            continue
        try:
            b = io.open(f, 'rb').read()
        except Exception:
            continue
        for m in pat.finditer(b):
            hits.add(m.group().decode('ascii', 'ignore'))
    print("=== %s (%d개)" % (L, len(hits)))
    for h in sorted(hits):
        print("   " + h)
