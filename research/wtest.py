# -*- coding: utf-8 -*-
"""UnityPy 로 mainData(ResourceManager)를 수정·저장할 수 있는지 검증한다.

이게 되면 '자산 파일 복사 + 색인 등록' 방식으로 맵/차량을 이식할 수 있다.
"""
import os, shutil, io, UnityPy

SRC = 'survey/5577.com.cjenm.chachachacn/assets/bin/Data/mainData'
TMP = 'wtest_mainData'
shutil.copy(SRC, TMP)

env = UnityPy.load(TMP)
rm_reader = [r for r in env.objects if r.type.name == "ResourceManager"][0]
rm = rm_reader.read()
print("원래 컨테이너 항목 %d개" % len(rm.m_Container))

# 기존 항목 하나를 복제해 새 경로로 추가해 본다
p0, ptr0 = rm.m_Container[0]
print("샘플 항목:", p0, "->", getattr(ptr0, 'file_id', None), getattr(ptr0, 'path_id', None))

try:
    rm.m_Container.append(("__xplant_test", ptr0))
    print("항목 추가 후 %d개" % len(rm.m_Container))
    rm.save()
    print("save() 성공")
    with open(TMP, 'wb') as f:
        f.write(env.file.save())
    print("파일 쓰기 성공 (%.1f KB)" % (os.path.getsize(TMP) / 1024))
except Exception as e:
    print("쓰기 실패:", type(e).__name__, e)
    raise SystemExit(1)

# 다시 읽어 확인
env2 = UnityPy.load(TMP)
rm2 = [r for r in env2.objects if r.type.name == "ResourceManager"][0].read()
names = [p for p, _ in rm2.m_Container]
print("재읽기 항목 %d개, 테스트 항목 존재: %s"
      % (len(names), "__xplant_test" in names))
