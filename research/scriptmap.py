# -*- coding: utf-8 -*-
"""배포판 간 MonoScript pathID 대응표를 만든다(이름 기준).

프리팹의 MonoBehaviour 는 m_Script 로 MonoScript 를 가리키는데, 그 pathID 는
배포판마다 다르다. 이름으로 짝지어 새 pathID 를 찾아 둔다.
MonoScript 의 첫 필드가 길이 접두 문자열(스크립트 이름)이라 원시 바이트로 읽는다.
"""
import io, json, os, struct, sys
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile


def script_names(path):
    sf = SerializedFile(EndianBinaryReader(io.open(path, 'rb').read()), None)
    out = {}
    for pid, o in sf.objects.items():
        if o.type.name != 'MonoScript':
            continue
        d = o.get_raw_data()
        if len(d) < 4:
            continue
        ln = struct.unpack_from('<i', d, 0)[0]
        if 0 < ln < 200 and 4 + ln <= len(d):
            try:
                out[d[4:4 + ln].decode('utf-8')] = pid
            except UnicodeDecodeError:
                pass
    return out


src, dst, out = sys.argv[1], sys.argv[2], sys.argv[3]
a = script_names(src)
b = script_names(dst)
m = {}
missing = []
for name, pid in a.items():
    if name in b:
        m[str(pid)] = b[name]
    else:
        missing.append(name)
io.open(out, 'w', encoding='utf-8').write(json.dumps(m))
print("원본 %d개 / 대상 %d개 / 짝지음 %d개 / 대상에 없음 %d개"
      % (len(a), len(b), len(m), len(missing)))
