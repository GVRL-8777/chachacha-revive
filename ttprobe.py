# -*- coding: utf-8 -*-
"""오브젝트를 타입트리로 읽고(read_typetree) 다시 쓰기(save_typetree)가 되는지 확인한다.

파일에 타입트리가 없으므로 UnityPy 는 TPK(내장 타입 DB)에서 4.1.5 용 트리를 가져온다.
이게 왕복되면 PPtr 재번호를 안전하게 할 수 있다.
"""
import io, json
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile

SRC = 'survey/gogogoracer-1-4-3/assets/bin/Data/32f46795bf14050449f88a9b04a1acfb'
sf = SerializedFile(EndianBinaryReader(io.open(SRC, 'rb').read()), None)

for pid, o in sf.objects.items():
    raw = o.get_raw_data()
    print("=== pathId=%s %s (%d B)" % (pid, o.type.name, len(raw)))
    try:
        tree = o.read_typetree()
    except Exception as e:
        print("   read_typetree 실패:", type(e).__name__, e)
        continue
    if o.type.name in ('GameObject', 'Transform', 'MeshFilter', 'MeshRenderer'):
        print("   ", json.dumps(tree, ensure_ascii=False)[:400])
    # 왕복 검증
    try:
        o.save_typetree(tree)
        new = o.get_raw_data()
        print("   왕복: %d B -> %d B, 동일: %s" % (len(raw), len(new), raw == new))
    except Exception as e:
        print("   save_typetree 실패:", type(e).__name__, e)
