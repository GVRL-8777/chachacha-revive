# -*- coding: utf-8 -*-
"""자산 파일을 유니티 안드로이드 빌드의 split 조각으로 쪼개 overlay 에 넣는다.

**중요**: 중국판 APK 는 `sharedassets0.assets` 를 통짜로 담지 않고
`sharedassets0.assets.split0 ~ .split20` 21조각으로만 담는다.
통짜 파일을 넣어 봐야 엔진은 조각들을 읽으므로 **수정이 전혀 반영되지 않는다**.
(이 함정 때문에 아틀라스 수정도, 폰트 교체도 오랫동안 무반응이었다)

조각 크기는 1MiB 고정, 마지막 조각만 나머지.
"""
import io, os, sys

CHUNK = 1024 * 1024
src = sys.argv[1]
name = sys.argv[2] if len(sys.argv) > 2 else 'sharedassets0.assets'
outdir = sys.argv[3] if len(sys.argv) > 3 else 'overlay'

data = io.open(src, 'rb').read()
n = 0
for i in range(0, len(data), CHUNK):
    p = os.path.join(outdir, '%s.split%d' % (name, n))
    io.open(p, 'wb').write(data[i:i + CHUNK])
    n += 1
print("%s (%d B) -> %s.split0 ~ .split%d (%d조각)" % (src, len(data), name, n - 1, n))
whole = os.path.join(outdir, name)
if os.path.exists(whole):
    os.remove(whole)
    print("통짜 %s 는 제거(엔진이 읽지 않음)" % name)
