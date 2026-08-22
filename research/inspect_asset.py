"""URL 이 박힌 Unity 에셋의 직렬화 구조를 확인한다 (문자열 = int32 길이 + 바이트 + 4바이트 정렬)."""
from _here import apk
import zipfile, struct, re

APK = apk('kr')
ENTRY = "assets/bin/Data/46d4d4a5ba7c79e469ef05e22157e120"

data = zipfile.ZipFile(APK).read(ENTRY)
print("엔트리 크기: %d bytes\n" % len(data))

for m in re.finditer(rb'http://[\x20-\x7e]{5,120}', data):
    s, e = m.start(), m.end()
    url = m.group().decode()
    # 바로 앞 4바이트가 길이 접두사인지 확인
    prefix = struct.unpack_from('<I', data, s - 4)[0] if s >= 4 else -1
    ok = "OK" if prefix == len(url) else ("길이 %d != %d" % (prefix, len(url)))
    pad = (4 - (len(url) % 4)) % 4
    print("offset 0x%05x  len=%2d  접두사=%-4d [%s]  정렬패딩=%d" % (s, len(url), prefix, ok, pad))
    print("   %r" % url)
    print("   앞: %s" % data[max(0, s-12):s].hex(' '))
    print("   뒤: %s" % data[e:e+8].hex(' '))
    print()
