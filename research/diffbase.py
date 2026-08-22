# -*- coding: utf-8 -*-
"""작업 트리(x77)에서 기준 APK 와 내용이 다른 파일만 추린다.

백업 용량을 줄이려고 쓴다. 기준 APK + 이 목록이면 트리를 그대로 되살린다.
"""
import os
import sys
import zipfile
import zlib

BASE = sys.argv[1] if len(sys.argv) > 1 else 'base.apk'
TREE = sys.argv[2] if len(sys.argv) > 2 else 'x77'

z = zipfile.ZipFile(BASE)
known = dict((i.filename, i.CRC) for i in z.infolist())

changed = []
total = 0
for root, _dirs, files in os.walk(TREE):
    for f in files:
        p = os.path.join(root, f)
        rel = os.path.relpath(p, TREE).replace(os.sep, '/')
        b = open(p, 'rb').read()
        if known.get(rel) != (zlib.crc32(b) & 0xffffffff):
            changed.append((rel, len(b)))
            total += len(b)

print('바뀐/새 파일 %d개, 합계 %.1f MB' % (len(changed), total / 1e6))
for rel, n in sorted(changed, key=lambda x: -x[1])[:15]:
    print('   %-55s %8d' % (rel, n))
with open('x77_changed.txt', 'w', encoding='utf-8') as fh:
    for rel, _n in sorted(changed):
        fh.write('x77/' + rel + '\n')
print('목록 -> x77_changed.txt')
