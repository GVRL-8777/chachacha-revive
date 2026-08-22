# -*- coding: utf-8 -*-
"""모든 배포판에서 _VOX_ 가 든 AudioClip 을 카탈로그와 무관하게 전수 조사한다.

카탈로그(ResourceManager)에 안 실린 자산도 파일에는 남아 있을 수 있으므로
Data 폴더의 모든 직렬화 파일을 직접 훑는다.
"""
import os, re, glob, io
from collections import defaultdict
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile

DIRS = [('survey/5577.com.cjenm.chachachacn/assets/bin/Data', '중국판'),
        ('survey/racechachachaforkakao/assets/bin/Data', '카카오판'),
        ('survey/gogogoracer-1-4-3/assets/bin/Data', 'gogogoracer')]

for D, L in DIRS:
    got = defaultdict(int)
    for f in sorted(glob.glob(os.path.join(D, '*'))):
        if not os.path.isfile(f):
            continue
        b = io.open(f, 'rb').read()
        if b'_VOX_' not in b:
            continue
        try:
            sf = SerializedFile(EndianBinaryReader(b), None)
        except Exception:
            continue
        for pid, o in sf.objects.items():
            if o.type.name != 'AudioClip':
                continue
            try:
                n = o.read_typetree()['m_Name']
            except Exception:
                continue
            if '_VOX_' in n.upper():
                got[n.split('_VOX_')[0].upper()] += 1
    print("=== %-12s 캐릭터 %d명" % (L, len(got)))
    for k in sorted(got):
        print("   %-10s %d개" % (k, got[k]))
