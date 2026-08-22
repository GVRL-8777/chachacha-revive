# -*- coding: utf-8 -*-
"""배포판별 AudioClip 전수 조사. ROPE 보이스가 다른 이름으로 있는지 확인한다."""
import os, glob, io, re
from collections import Counter
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile

DIRS = [('survey/5577.com.cjenm.chachachacn/assets/bin/Data', '중국판'),
        ('survey/racechachachaforkakao/assets/bin/Data', '카카오판'),
        ('survey/gogogoracer-1-4-3/assets/bin/Data', 'gogogoracer')]
for D, L in DIRS:
    names = []
    for f in sorted(glob.glob(os.path.join(D, '*'))):
        if not os.path.isfile(f):
            continue
        try:
            sf = SerializedFile(EndianBinaryReader(io.open(f, 'rb').read()), None)
        except Exception:
            continue
        for pid, o in sf.objects.items():
            if o.type.name != 'AudioClip':
                continue
            try:
                names.append(o.read_typetree()['m_Name'])
            except Exception:
                pass
    # 접두어(첫 언더바 앞)로 묶는다
    c = Counter(n.split('_')[0].upper() for n in names)
    print("=== %-12s AudioClip %d개, 접두어 %d종" % (L, len(names), len(c)))
    print("   " + ', '.join('%s(%d)' % (k, v) for k, v in sorted(c.items())))
    rope = [n for n in names if re.search(r'rope|mental|심리', n, re.I)]
    if rope:
        print("   ★ ROPE/MENTAL 후보: %s" % rope[:8])
