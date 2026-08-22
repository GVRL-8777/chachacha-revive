# -*- coding: utf-8 -*-
"""타이틀 로고 보이스('다함께 차차차!')를 한국어로 바꿉니다.

중국판의 `logo chachacha` 는 중국어 더빙입니다(698 KB). 같은 이름의 한국어
더빙이 카카오판에 있습니다(73 KB).

이 클립은 **분할된 sharedassets0** 안에 있어서 파일을 통째로 다시 쓰면
21 MB 짜리 핵심 파일의 배치가 바뀝니다(왕복 시험에서 1.7 MB 줄었습니다).
그래서 그 길로 가지 않습니다.

`m_AudioData` 는 이 타입트리의 **마지막 필드**입니다. 그래서 짧은 소리를
써 넣고 남는 자리를 0 으로 두면
  · 오브젝트가 선언한 크기는 그대로이고
  · 유니티는 타입트리가 말하는 만큼만 읽으므로 뒤쪽 0 은 무시합니다.
결국 **파일 길이가 한 바이트도 안 변합니다** — 분할 조각도 그대로입니다.

  python titlevoice.py [--dry]
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import chaassets as A
from sfparse import parse
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile

HERE = os.path.dirname(os.path.abspath(__file__))
# 진짜 한국판은 `kr` 입니다. 차 이름이 수리카·해미·매그넘 입니다.
# (survey/racechachachaforkakao 는 이름이 Garuda·Hummie·Magnum 인
#  동남아/영문판이라 보이스도 한국어가 아닙니다.)
DONOR = os.path.join(HERE, 'kr')
TREE = os.path.join(HERE, 'x77')
CLIP = 'logo chachacha'
BASE = 'sharedassets0.assets'


def parts_of(d, base):
    return sorted([f for f in os.listdir(d) if f.startswith(base + '.split')],
                  key=lambda x: int(x.rsplit('split', 1)[1]))


def joined(tree, base):
    """분할된 자산을 붙여 하나로 읽습니다."""
    d = os.path.join(tree, A.DATA)
    parts = parts_of(d, base)
    if not parts:
        return None
    return b''.join(io.open(os.path.join(d, p), 'rb').read() for p in parts)


def find_clip(tree, base, name):
    """그 빌드의 분할 자산 안에서 이름으로 클립 하나를 찾습니다."""
    blob = joined(tree, base)
    if blob is None:
        return None
    f = SerializedFile(EndianBinaryReader(blob), None)
    for pid, o in f.objects.items():
        if o.type.name != 'AudioClip':
            continue
        t = o.read_typetree()
        if t.get('m_Name') == name:
            return t
    return None


def main():
    dry = '--dry' in sys.argv
    korean = find_clip(DONOR, BASE, CLIP)
    if korean is None:
        raise SystemExit('한국판(%s)에서 %s 를 찾지 못했습니다' % (DONOR, CLIP))
    print('가져올 소리: %s 의 %s (%d바이트)'
          % (os.path.basename(DONOR), CLIP, len(korean['m_AudioData'])))

    d = os.path.join(TREE, A.DATA)
    parts = parts_of(d, BASE)
    sizes = [os.path.getsize(os.path.join(d, p)) for p in parts]
    blob = bytearray(b''.join(io.open(os.path.join(d, p), 'rb').read()
                              for p in parts))
    tmp = os.path.join(HERE, '_sa0.tmp')
    io.open(tmp, 'wb').write(bytes(blob))
    meta = parse(tmp)
    os.remove(tmp)

    f = SerializedFile(EndianBinaryReader(bytes(blob)), None)
    hit = None
    for pid, o in f.objects.items():
        if o.type.name != 'AudioClip':
            continue
        if o.read_typetree().get('m_Name') == CLIP:
            hit = (pid, o)
            break
    if hit is None:
        raise SystemExit('%s 안에서 %s 를 찾지 못했습니다' % (BASE, CLIP))
    pid, obj = hit
    rec = [x for x in meta['objects'] if x['path_id'] == pid][0]
    st = meta['data_offset'] + rec['start']

    tree = obj.read_typetree()
    old_n = len(tree.get('m_AudioData') or b'')
    for k in ('m_AudioData', 'm_Format', 'm_Type', 'm_3D', 'm_UseHardware',
              'm_Stream', 'm_Frequency', 'm_Length', 'm_Channels',
              'm_BitsPerSample', 'm_Size'):
        if k in korean and k in tree:
            tree[k] = korean[k]
    # 소리 뒤를 0 으로 채워 **원래 길이에 맞춥니다.**
    # 안 채우면 오브젝트가 선언한 크기와 실제 내용이 어긋나 엄격한 읽기가
    # 걸립니다(유니티는 넘어가지만, 어긋난 채 두지 않습니다).
    # MP3 는 마지막 프레임에서 끝나므로 뒤의 0 은 소리에 영향이 없습니다.
    data = bytes(tree['m_AudioData'])
    if len(data) < old_n:
        tree['m_AudioData'] = data + bytes(old_n - len(data))
    new_blob = bytes(obj.save_typetree(tree))
    room = rec['size']
    print('%s: 소리 %d -> %d바이트(0 채움 포함) · 오브젝트 %d -> %d바이트'
          % (CLIP, old_n, len(tree['m_AudioData']), room, len(new_blob)))
    if len(new_blob) > room:
        raise SystemExit('새 소리가 자리보다 큽니다. 이 방법으로는 못 넣습니다.')
    if dry:
        print('(--dry 이므로 쓰지 않았습니다)')
        return 0

    bdir = os.path.join(HERE, 'backup')
    os.makedirs(bdir, exist_ok=True)
    for p, s in zip(parts, sizes):
        b = os.path.join(bdir, p + '.bak')
        if not os.path.exists(b):
            import shutil
            shutil.copyfile(os.path.join(d, p), b)

    blob[st:st + room] = new_blob + b'\x00' * (room - len(new_blob))
    off = 0
    for p, s in zip(parts, sizes):
        io.open(os.path.join(d, p), 'wb').write(bytes(blob[off:off + s]))
        off += s
    assert off == len(blob)
    print('분할 %d조각을 그대로 다시 썼습니다 (총 %d바이트, 길이 그대로)'
          % (len(parts), len(blob)))
    print('타이틀 보이스를 한국어로 바꿨습니다. 원본은 backup/ 에 있습니다.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
