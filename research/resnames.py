# -*- coding: utf-8 -*-
"""assets/bin/Data 의 해시 이름 파일에서 Unity 오브젝트 이름을 추출한다."""
from _here import apk
import zipfile, re, struct, collections, sys, io
z = zipfile.ZipFile(apk('kr'))
HASH = re.compile(r'^assets/bin/Data/[0-9a-f]{32}$')
NAME = re.compile(rb'[A-Za-z0-9 _()\[\]\-\.#/&+]{3,60}$')

def names(data):
    """[int32 len][bytes] 형태의 그럴듯한 이름을 앞부분에서 찾는다."""
    out = []
    for m in re.finditer(rb'(?=([\x03-\x3c]\x00\x00\x00))', data[:8192]):
        ln = data[m.start()]
        s = data[m.start()+4:m.start()+4+ln]
        if len(s) == ln and NAME.match(s):
            out.append(s.decode('ascii'))
    return out

files = [i.filename for i in z.infolist() if HASH.match(i.filename)]
print("해시 이름 에셋 파일: %d개" % len(files))
allnames = []
for f in files:
    ns = names(z.read(f))
    if ns:
        allnames.append((f.split('/')[-1], ns[0], ns[:6]))
print("이름 추출 성공: %d개\n" % len(allnames))
cnt = collections.Counter()
for _, first, _ in allnames:
    key = re.sub(r'[0-9]+', '#', first)
    cnt[key] += 1
print("[첫 이름 상위 60]")
for k, v in cnt.most_common(60):
    print("   %-46s x%d" % (k, v))
