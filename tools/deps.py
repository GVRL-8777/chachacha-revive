# -*- coding: utf-8 -*-
"""자산 파일이 참조하는 외부 파일을 재귀로 모아 overlay 폴더에 복사한다.

주의: 대상 배포판(중국판)에 **같은 이름의 파일이 이미 있으면 건너뛴다**.
파일명은 내용 기반 GUID 라 같은 이름이면 같은 자산이고, 유니티 내장 리소스
파일(0000...) 처럼 판본마다 내용이 다른 것을 덮어쓰면 게임이 깨진다.

사용법:
  python deps.py <원본Data> <출력폴더> <루트파일 또는 @목록파일> ...
"""
import io, os, shutil, sys
from sfparse import parse

CN = 'survey/5577.com.cjenm.chachachacn/assets/bin/Data'

D = sys.argv[1]
OUT = sys.argv[2]
roots = []
for a in sys.argv[3:]:
    if a.startswith('@'):
        roots += [l.strip() for l in io.open(a[1:], encoding='utf-8').read().splitlines() if l.strip()]
    else:
        roots.append(a)
roots = list(dict.fromkeys(roots))          # 중복 제거, 순서 유지

seen, todo = set(), list(roots)
while todo:
    f = todo.pop()
    if f in seen:
        continue
    seen.add(f)
    p = os.path.join(D, f)
    if not os.path.exists(p):
        print("  없음: %s" % f)
        continue
    try:
        m = parse(p)
    except Exception as e:
        print("  못읽음: %s (%s)" % (f, e))
        continue
    todo += m['externals']

os.path.isdir(OUT) or os.makedirs(OUT)
copied = skipped = 0
total = 0
for f in sorted(seen):
    if f in roots:
        continue                            # 루트는 번들에 들어간다
    if os.path.exists(os.path.join(CN, f)):
        print("  건너뜀(중국판에 이미 있음): %s" % f)
        skipped += 1
        continue
    src = os.path.join(D, f)
    if not os.path.exists(src):
        continue
    shutil.copy(src, os.path.join(OUT, f))
    total += os.path.getsize(src)
    copied += 1
print("의존 파일 %d개 복사 (%.1f MB) / 건너뜀 %d개 / 루트 %d개"
      % (copied, total / 1048576.0, skipped, len(roots)))
