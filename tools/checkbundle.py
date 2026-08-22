# -*- coding: utf-8 -*-
"""이식한 맵 번들에서 **참조가 끊긴 조각**을 찾는다.

증상: 주행 중 특정 구간에서 지형이 통째로 사라지고 하늘만 보인다.
조각(GameObject)은 살아 있는데 그 아래 매달린 Mesh/Material/Texture 중 하나가
번들에도 없고 중국판 Data 에도 없으면, 그 구간만 아무것도 안 그려진다.

각 Background/* 조각의 하위 트리를 훑어 내부 참조(fileID=0)가 번들 안에
실제로 존재하는지, 외부 참조(fileID>0)가 가리키는 파일이 있는지 확인한다.
"""
import io
import os
import struct
from collections import defaultdict

from sfparse import parse

BUNDLE_DIR = 'bundles'
CN = 'survey/5577.com.cjenm.chachachacn/assets/bin/Data'


def load_bundle_files():
    """UnityRaw 번들 안의 serialized file 을 꺼낸다(mkbundle.py 가 만든 구조)."""
    import glob
    out = []
    for p in glob.glob(os.path.join(BUNDLE_DIR, '*')):
        if os.path.isdir(p):
            continue
        out.append(p)
    return out


def main():
    import UnityPy
    for p in load_bundle_files():
        try:
            env = UnityPy.load(p)
        except Exception as e:
            print("%s: 열기 실패 %s" % (os.path.basename(p), e))
            continue
        objs = {}
        for o in env.objects:
            objs[(o.assets_file.name if o.assets_file else '', o.path_id)] = o
        print("%s: 오브젝트 %d개" % (os.path.basename(p), len(objs)))

        # 파일별 외부 참조 목록
        for f in env.files.values():
            if not hasattr(f, 'externals'):
                continue
            ext = [e.path for e in f.externals]
            missing_ext = [e for e in ext
                           if not os.path.exists(os.path.join(CN, os.path.basename(e)))
                           and not os.path.basename(e).startswith('library/')
                           and 'unity default resources' not in e
                           and 'unity_builtin_extra' not in e]
            if missing_ext:
                print("  [외부참조 없음] %s" % ', '.join(missing_ext))

        # 내부 참조가 끊긴 오브젝트
        ids = set(pid for (_n, pid) in objs.keys())
        dangling = defaultdict(list)
        for (fname, pid), o in objs.items():
            try:
                d = o.get_raw_data()
            except Exception:
                continue
            # 8바이트 정렬 위치마다 PPtr(fileID=0, pathID) 패턴을 훑는다
            for off in range(0, len(d) - 8, 4):
                fid, tgt = struct.unpack_from('<ii', d, off)
                if fid != 0 or tgt <= 0 or tgt > 100000:
                    continue
                if tgt not in ids:
                    dangling[o.type.name].append(tgt)
        if dangling:
            print("  [내부참조 후보 끊김] %s"
                  % ', '.join('%s×%d' % (k, len(v)) for k, v in dangling.items()))


if __name__ == '__main__':
    main()
