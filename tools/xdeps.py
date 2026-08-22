# -*- coding: utf-8 -*-
"""이식 자산의 의존 파일을 **이름 충돌 없이** 옮긴다.

예전 deps.py 는 "중국판에 같은 이름 파일이 이미 있으면 건너뛴다"는 규칙이었다.
파일 이름이 자산 GUID 라 같은 이름이면 같은 자산이라고 본 것인데, 판본이
다르면 같은 GUID 자리에 내용이 다른 자산이 들어 있다. 그래서 이식한 터널이
중국판 터널의 재질·메시를 끌어다 쓰다가 맵이 비어 보였다.

여기서는 내용이 다르면 **새 이름을 붙여** 따로 넣고, 그 이름을 가리키도록
참조를 고쳐 쓴다. 참조는 직렬화 파일 메타데이터에 32자리 16진수 문자열로
적혀 있어 길이가 같으니 제자리 치환이 안전하다.

공여판이 여러 개라 서로 겹치는 것도 같은 방식으로 갈라낸다. 앞서 넣어 둔
결과 위에 계속 얹을 수 있게 rename 표를 읽고 쓴다.

  python xdeps.py <공여판Data> <출력폴더> <루트 또는 @목록> ...
"""
import hashlib
import io
import json
import os
import re
import sys

from sfparse import parse
import sfx

CN = 'survey/5577.com.cjenm.chachachacn/assets/bin/Data'
HEX32 = re.compile(r'^[0-9a-f]{32}$')


def md5b(b):
    return hashlib.md5(b).hexdigest()


def md5f(p):
    return md5b(io.open(p, 'rb').read())


def main():
    D, OUT = sys.argv[1], sys.argv[2]
    roots = []
    for a in sys.argv[3:]:
        if a.startswith('@'):
            roots += [l.strip() for l in io.open(a[1:], encoding='utf-8')
                      .read().splitlines() if l.strip()]
        else:
            roots.append(a)
    roots = list(dict.fromkeys(roots))

    mapfile = 'rename_%s.json' % os.path.basename(OUT)
    ren = json.load(io.open(mapfile, encoding='utf-8')) \
        if os.path.exists(mapfile) else {}
    os.path.isdir(OUT) or os.makedirs(OUT)

    # 1) 의존 닫힘
    seen, todo = set(), list(roots)
    while todo:
        f = todo.pop()
        if f in seen:
            continue
        seen.add(f)
        p = os.path.join(D, f)
        if not os.path.exists(p):
            continue
        try:
            todo += parse(p)['externals']
        except Exception as e:
            print("  못읽음: %s (%s)" % (f, e))

    # 2) 이름 배정
    same = fresh = 0
    newren = {}
    shared = []
    for f in sorted(seen):
        src = os.path.join(D, f)
        if not os.path.exists(src):
            continue
        if not HEX32.match(f):
            shared.append(f)            # sharedassets 등 공용 파일. 절대 안 건드린다
            continue
        h = md5f(src)
        cnp = os.path.join(CN, f)
        ovp = os.path.join(OUT, f)
        if os.path.exists(cnp) and md5f(cnp) == h:
            same += 1
            continue
        if os.path.exists(ovp) and md5f(ovp) == h:
            fresh += 1                  # 앞선 공여판이 이미 같은 것을 넣어 뒀다
            continue
        if os.path.exists(cnp) or os.path.exists(ovp):
            if f in ren and ren[f] == h:
                pass
            newren[f] = h               # 자리가 차 있다 -> 내용으로 새 이름
        else:
            fresh += 1

    for k, v in newren.items():
        # 같은 이름을 공여판마다 다른 내용으로 갈라내면 앞서 쓴 참조가 어긋난다
        if k in ren and ren[k] != v:
            raise SystemExit("이미 %s -> %s 로 갈라 두었는데 %s 를 요구한다"
                             % (k, ren[k], v))
    ren.update(newren)

    # 3) 복사 + 참조 고쳐쓰기 (루트는 번들에 들어가므로 뺀다)
    copied = total = 0
    for f in sorted(seen):
        if f in roots or f in shared:
            continue
        src = os.path.join(D, f)
        if not os.path.exists(src):
            continue
        dst_name = ren.get(f, f)
        dst = os.path.join(OUT, dst_name)
        data = bytearray(io.open(src, 'rb').read())
        if dst_name == f and os.path.exists(os.path.join(CN, f)) \
                and md5f(os.path.join(CN, f)) == md5b(bytes(data)):
            continue                    # 중국판 것과 같으니 넣을 필요가 없다
        for off, nm in sfx.externals(bytes(data)):
            if nm in ren:
                data[off:off + 32] = ren[nm].encode('ascii')
        io.open(dst, 'wb').write(bytes(data))
        copied += 1
        total += len(data)

    json.dump(ren, io.open(mapfile, 'w', encoding='utf-8'), indent=1)
    print("루트 %d개 / 의존 닫힘 %d개" % (len(roots), len(seen)))
    print("  중국판과 같아 그대로 씀   : %d개" % same)
    print("  이름이 비어 있어 그대로   : %d개" % fresh)
    print("  자리가 차서 갈라냄        : %d개 (누적 %d개)" % (len(newren), len(ren)))
    if shared:
        print("  손대지 않은 공용 파일     : %s" % sorted(set(shared)))
    print("복사 %d개 (%.1f MB) -> %s" % (copied, total / 1048576.0, OUT))


if __name__ == '__main__':
    main()
