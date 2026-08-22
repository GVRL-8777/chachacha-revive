# -*- coding: utf-8 -*-
"""세그먼트의 트랜스폼 계층과 메시 바운드를 월드 기준으로 환산해 비교한다.

GetNextMap 이 조각을 rotation=Euler(270,0,0) 으로 놓으므로
  메시 local X -> 월드 X (좌우)
  메시 local Y -> 월드 Z (주행축, -부호)
  메시 local Z -> 월드 Y (높이)
"""
import os, sys
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile

def show(path, label):
    sf = SerializedFile(EndianBinaryReader(open(path, 'rb').read()), None)
    print("=== %s" % label)
    for pid, o in sorted(sf.objects.items()):
        try:
            t = o.read_typetree()
        except Exception:
            continue
        if o.type.name == 'Transform':
            print("  T pid=%-3s pos=%-22s scale=%-20s 부모=%s"
                  % (pid,
                     tuple(round(v, 2) for v in t['m_LocalPosition'].values()),
                     tuple(round(v, 3) for v in t['m_LocalScale'].values()),
                     t['m_Father']['m_PathID']))
        elif o.type.name == 'Mesh':
            a = t['m_LocalAABB']; c = a['m_Center']; e = a['m_Extent']
            print("  M pid=%-3s 월드X[%7.1f ~ %7.1f] 폭=%6.1f | 월드Z[%7.1f ~ %7.1f] 길이=%6.1f"
                  " | 월드Y[%6.1f ~ %6.1f] 높이=%5.1f"
                  % (pid,
                     c['x'] - e['x'], c['x'] + e['x'], e['x'] * 2,
                     -(c['y'] + e['y']), -(c['y'] - e['y']), e['y'] * 2,
                     c['z'] - e['z'], c['z'] + e['z'], e['z'] * 2))

CN = 'survey/5577.com.cjenm.chachachacn/assets/bin/Data'
GO = 'survey/gogogoracer-1-4-3/assets/bin/Data'
show(os.path.join(CN, sys.argv[1]), '중국판')
show('gbeach_seg.dat', '이식본(번들에 넣은 것, 보정 반영)')
