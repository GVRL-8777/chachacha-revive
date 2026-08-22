"""APK 전체 엔트리를 훑어 CDN/서버 호스트 문자열이 어디에 박혀 있는지 찾는다."""
from _here import apk
import zipfile, re, sys

APK = apk('kr')
PAT = re.compile(rb'[\x20-\x7e]{4,200}?(mcdn|netmarble\.kr|\.mcdn\.|cr/Real|AssetCatalogue|img\.netmarble)[\x20-\x7e]{0,200}', re.I)

z = zipfile.ZipFile(APK)
hits = 0
for name in z.namelist():
    if name.endswith('/'):
        continue
    try:
        data = z.read(name)
    except Exception:
        continue
    found = set()
    for m in PAT.finditer(data):
        s = m.group().decode('ascii', 'replace')
        found.add(s)
    # UTF-16LE 로도 검사 (Unity/.NET 직렬화 문자열)
    try:
        u = data.decode('utf-16-le', 'ignore').encode('ascii', 'ignore')
        for m in PAT.finditer(u):
            found.add('[utf16] ' + m.group().decode('ascii', 'replace'))
    except Exception:
        pass
    if found:
        hits += 1
        print('=' * 3, name, '(%d bytes)' % len(data))
        for s in sorted(found)[:12]:
            print('     ', s)
print('\n[%d entries matched]' % hits)
