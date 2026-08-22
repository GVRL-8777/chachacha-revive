# -*- coding: utf-8 -*-
"""번들에서 **우리가 이름으로 꺼내 쓸 것만** 남기고 나머지 이름을 비켜 준다.

번들 조회는 오브젝트 이름표로 한다(경로 마지막 조각, 소문자). 그런데 이식한
테마에 딸려 온 자산 중에는 중국판이 자기 자원 이름으로 쓰는 것(`bridge01`,
`shadow` …)이 섞여 있다. 그러면 중국판이 자기 맵을 부를 때 번들 쪽이 먼저
잡혀 엉뚱한 것이 올라오고, 그 테마는 조각이 하나도 안 쌓여
`GetNextMap` 이 0으로 나누고 `currentMap` 이 널이 된다.
그 뒤로는 `Player._CalcSpeed` 가 매 프레임 죽어 차가 안 나가고 HUD 도 멈춘다.

그래서 스펙에 적은 키(우리가 부를 이름)만 남기고, 나머지 GameObject 이름은
첫 글자를 '~' 로 바꾼다. 길이가 같아 안전하고, 번들 내부 참조는 전부 pathID
기준이라 영향이 없다.

  python derename.py pack.dat [스펙파일 …]
"""
import io
import os
import sys

from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile
from sfparse import parse

PACK = sys.argv[1] if len(sys.argv) > 1 else 'pack.dat'
SPECS = sys.argv[2:] or ['mapspec.txt', 'voxspec.txt', 'hellyspec.txt']


def wanted():
    keys = set()
    for sp in SPECS:
        if not os.path.exists(sp):
            continue
        for ln in io.open(sp, encoding='utf-8').read().splitlines():
            ln = ln.strip()
            if not ln:
                continue
            parts = ln.split(':')
            if len(parts) < 2:
                continue
            keys.add(parts[1].split('/')[-1].lower())
    return keys


def cn_names():
    """중국판이 자기 자원 이름으로 쓰는 것들(경로 마지막 조각)."""
    import UnityPy
    env = UnityPy.load(os.path.join(
        'survey/5577.com.cjenm.chachachacn/assets/bin/Data', 'mainData'))
    rm = [r for r in env.objects if r.type.name == 'ResourceManager'][0].read()
    return set(p.split('/')[-1].lower() for p, _ in rm.m_Container)


def main():
    keep = wanted()
    cn = cn_names()
    meta = parse(PACK)
    raw = bytearray(io.open(PACK, 'rb').read())
    sf = SerializedFile(EndianBinaryReader(bytes(raw)), None)
    recs = dict((o['path_id'], o) for o in meta['objects'])
    hit = skip = 0
    for pid, o in sf.objects.items():
        if o.type.name != 'GameObject':
            continue
        try:
            tree = o.read_typetree()
        except Exception:
            continue
        nm = tree.get('m_Name') or ''
        if not nm or nm.startswith('~'):
            continue
        low = nm.lower()
        if low in keep or low not in cn:
            skip += 1
            continue
        tree['m_Name'] = '~' + nm[1:]
        blob = bytes(o.save_typetree(tree))
        rec = recs[pid]
        if len(blob) != rec['size']:
            continue
        st = meta['data_offset'] + rec['start']
        raw[st:st + len(blob)] = blob
        hit += 1
    io.open(PACK, 'wb').write(bytes(raw))
    print("그대로 둔 것 %d개 / 중국판과 겹쳐 비킨 것 %d개" % (skip, hit))


if __name__ == '__main__':
    main()
