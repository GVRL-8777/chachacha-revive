# -*- coding: utf-8 -*-
"""aqua 테마의 풀 재질이 엉뚱한 것을 셰이더로 물고 있는 것을 고친다.

공여판에서 이 재질(aqua_Grass)은 `sharedassets1.assets` 의 pathID 69,
즉 Mobile-Particle-Alpha 셰이더를 가리킨다. 그런데 sharedassets 는 판본마다
내용이 완전히 다른 공용 파일이라 이름을 갈라낼 수도, 덮어쓸 수도 없다.
중국판에서 같은 자리(pathID 69)는 Transform 이라 셰이더가 없는 셈이 되어
그 풀이 아예 그려지지 않는다.

중국판에도 같은 셰이더가 내장 리소스에 들어 있으므로(0000..f000.. 의 pathID 2)
거기를 가리키게 바꾼다.
"""
import io
import os

from sfparse import parse
from setext import set_externals
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile

CN = 'survey/5577.com.cjenm.chachachacn/assets/bin/Data'
BUILTIN = '0000000000000000f000000000000000'
MAT = 'ov/80602c1fb7130bb43805ce865a534ad5'


def shader_pathid(name):
    sf = SerializedFile(EndianBinaryReader(
        io.open(os.path.join(CN, BUILTIN), 'rb').read()), None)
    for pid, o in sf.objects.items():
        if o.type.name == 'Shader' and getattr(o.read(), 'm_Name', '') == name:
            return pid
    raise SystemExit("중국판 내장 리소스에 %s 가 없다" % name)


def main():
    if not os.path.exists(MAT):
        print("대상 재질이 없다: %s" % MAT)
        return
    pid = shader_pathid('Mobile-Particle-Alpha')

    ext = parse(MAT)['externals']
    if ext[0] != BUILTIN:
        set_externals(MAT, [BUILTIN] + list(ext[1:]))

    meta = parse(MAT)
    raw = bytearray(io.open(MAT, 'rb').read())
    sf = SerializedFile(EndianBinaryReader(bytes(raw)), None)
    o = sf.objects[1]
    tree = o.read_typetree()
    tree['m_Shader'] = {'m_FileID': 1, 'm_PathID': pid}
    blob = bytes(o.save_typetree(tree))
    rec = [x for x in meta['objects'] if x['path_id'] == 1][0]
    assert len(blob) == rec['size'], (len(blob), rec['size'])
    st = meta['data_offset'] + rec['start']
    raw[st:st + len(blob)] = blob
    io.open(MAT, 'wb').write(bytes(raw))

    chk = SerializedFile(EndianBinaryReader(io.open(MAT, 'rb').read()), None)
    print("aqua_Grass 셰이더 -> %s : pathID %d (Mobile-Particle-Alpha)"
          % (parse(MAT)['externals'][0][:12], chk.objects[1].read_typetree()
             ['m_Shader']['m_PathID']))


if __name__ == '__main__':
    main()
