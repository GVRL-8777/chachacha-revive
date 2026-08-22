# -*- coding: utf-8 -*-
"""중국판과 공여판의 유니티 내장 리소스 파일이 같은 배치를 갖는지 본다."""
import io, os, UnityPy

CN   = 'survey/5577.com.cjenm.chachachacn/assets/bin/Data'
GOGO = 'survey/gogogoracer-1-4-3/assets/bin/Data'

def table(d, n):
    p = os.path.join(d, n)
    if not os.path.exists(p):
        return None
    env = UnityPy.load(p)
    out = {}
    for o in env.objects:
        nm = ''
        try:
            nm = getattr(o.read(), 'm_Name', '') or ''
        except Exception:
            pass
        out[o.path_id] = (o.type.name, nm)
    return out

for n in ('0000000000000000e000000000000000',
          '0000000000000000f000000000000000',
          'unity default resources'):
    a, b = table(CN, n), table(GOGO, n)
    if a is None or b is None:
        print("%s : 한쪽 없음 (CN=%s GOGO=%s)" % (n[:20], a is not None, b is not None))
        continue
    common = set(a) & set(b)
    diff = [p for p in sorted(common) if a[p] != b[p]]
    print("%s : 중국판 %d개 / 공여판 %d개 / 공통 %d개 / 어긋남 %d개"
          % (n[:20], len(a), len(b), len(common), len(diff)))
    for p in diff[:8]:
        print("      pathID %-4d 중국판=%s  공여판=%s" % (p, a[p], b[p]))
    only = sorted(set(b) - set(a))
    if only:
        print("      공여판에만 있는 pathID %d개: %s" % (len(only), only[:10]))
