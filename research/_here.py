# -*- coding: utf-8 -*-
# 조사용 스크립트가 원본 APK 와 작업 폴더를 **스스로 찾게** 해 준다.
#
# 예전에는 이 폴더의 스크립트마다 만든 사람 PC 의 APK 경로가
# 박혀 있었다. 남이 받아 쓰면 그 줄부터 고쳐야 했다. 이제 안 고쳐도 된다.
#
#     from _here import ROOT, apk
#     APK = apk('kr')        # 한국판 7.7.0 (없으면 어디에 두라고 알려 준다)
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.join(ROOT, 'tools') not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, 'tools'))

import chapaths


def apk(key='kr', need=True):
    return chapaths.apk(key, need=need)
