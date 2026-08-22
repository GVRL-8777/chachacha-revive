# -*- coding: utf-8 -*-
"""APK 의 **패키지 이름**을 바꿉니다. 기기의 `Android/data/<여기>` 폴더 이름입니다.

두 군데만 고치면 됩니다.

  1) `AndroidManifest.xml` 의 `package=` 속성
     이진 XML(AXML)이라 문자열 풀을 다시 써야 합니다. 이름 길이가 바뀌면
     풀 오프셋과 청크 크기가 전부 밀립니다. 풀 뒤의 요소들은 문자열을
     **번호**로 가리키므로 번호만 그대로면 안전합니다.

  2) `resources.arsc` 의 패키지 이름
     여기 이름 칸은 UTF-16 128자 **고정**이라 제자리에서 덮어쓰면 됩니다.
     `getIdentifier(이름, 종류, getPackageName())` 로 리소스를 찾는 코드가
     있으면 이게 안 맞을 때 조용히 0 을 돌려받습니다.

**클래스 이름은 그대로 둡니다.** 매니페스트가 액티비티를 절대 이름
(`com.cjenm.chachachacn.CustomUnityPlayerActivity`)으로 적어 두어서
패키지 이름과 클래스 이름이 달라도 됩니다. dex 안의 클래스는 손대지
않으므로 깨질 일이 없습니다.

바꾸고 나면 **다른 앱**이 됩니다. 옛 앱과 나란히 깔리고 세이브는
넘어오지 않습니다.

  python setpkg.py <in.apk> <out.apk> <새 패키지 이름>
  python setpkg.py <in.apk> --show
"""
import io
import struct
import sys
import zipfile

RES_STRING_POOL = 0x0001
RES_TABLE_PACKAGE = 0x0200
UTF8_FLAG = 1 << 8
ARSC_NAME_CHARS = 128            # 규격이 못박아 둔 칸 크기


def u16(b, o):
    return struct.unpack_from('<H', b, o)[0]


def u32(b, o):
    return struct.unpack_from('<I', b, o)[0]


# ------------------------------------------------------------------ AXML
def axml_strings(b, pool_off=8):
    """(문자열 목록, utf8 여부). AXML 은 보통 UTF-16 입니다."""
    cnt = u32(b, pool_off + 8)
    style_cnt = u32(b, pool_off + 12)
    flags = u32(b, pool_off + 16)
    str_start = u32(b, pool_off + 20)
    utf8 = bool(flags & UTF8_FLAG)
    hdr = u16(b, pool_off + 2)
    offs = [u32(b, pool_off + hdr + 4 * i) for i in range(cnt)]
    base = pool_off + str_start
    out = []
    for o in offs:
        p = base + o
        if utf8:
            n = b[p]
            p += 2 if n & 0x80 else 1
            m = b[p]
            if m & 0x80:
                m = ((m & 0x7F) << 8) | b[p + 1]
                p += 2
            else:
                p += 1
            out.append(b[p:p + m].decode('utf-8', 'replace'))
        else:
            n = u16(b, p)
            out.append(b[p + 2:p + 2 + n * 2].decode('utf-16le', 'replace'))
    return out, utf8, style_cnt


def axml_setpkg(b, old, new):
    """풀에서 old 와 **정확히 같은** 문자열만 new 로 바꿉니다.

    클래스 이름(`…chachachacn.CustomUnityPlayerActivity`)은 old 로 시작할
    뿐 같지는 않으므로 건드리지 않습니다. 그게 핵심입니다."""
    pool_off = 8
    if u16(b, pool_off) != RES_STRING_POOL:
        raise SystemExit('AXML 문자열 풀을 못 찾았습니다')
    strs, utf8, style_cnt = axml_strings(b, pool_off)
    hits = [i for i, s in enumerate(strs) if s == old]
    if not hits:
        raise SystemExit('매니페스트에 %r 이 없습니다' % old)
    for i in hits:
        strs[i] = new

    body = bytearray()
    offs = []
    for s in strs:
        offs.append(len(body))
        if utf8:
            raw = s.encode('utf-8')
            body += bytes([len(s), len(raw)]) + raw + b'\x00'
        else:
            body += struct.pack('<H', len(s)) + s.encode('utf-16le') + b'\x00\x00'
    while len(body) % 4:
        body += b'\x00'

    hdr = u16(b, pool_off + 2)
    old_size = u32(b, pool_off + 4)
    if style_cnt:
        raise SystemExit('스타일이 있는 풀은 아직 다루지 않습니다')
    head = bytearray(b[pool_off:pool_off + hdr])
    struct.pack_into('<I', head, 20, hdr + 4 * len(strs))   # stringsStart
    struct.pack_into('<I', head, 24, 0)                     # stylesStart
    pool = bytes(head) + b''.join(struct.pack('<I', o) for o in offs) \
        + bytes(body)
    pool = bytearray(pool)
    struct.pack_into('<I', pool, 4, len(pool))

    out = bytearray(b[:pool_off]) + pool + b[pool_off + old_size:]
    struct.pack_into('<I', out, 4, len(out))                # 파일 전체 크기
    return bytes(out), len(pool) - old_size, len(hits)


# ------------------------------------------------------------------ arsc
def arsc_setpkg(b, old, new):
    """패키지 이름 칸(UTF-16 128자 고정)을 제자리에서 덮어씁니다."""
    if len(new) >= ARSC_NAME_CHARS:
        raise SystemExit('패키지 이름이 너무 깁니다')
    want = old.encode('utf-16le')
    i = b.find(want)
    if i < 0:
        return b, 0
    if u16(b, i - 12) != RES_TABLE_PACKAGE:
        raise SystemExit('패키지 청크 머리를 못 찾았습니다')
    out = bytearray(b)
    out[i:i + ARSC_NAME_CHARS * 2] = (
        new.encode('utf-16le').ljust(ARSC_NAME_CHARS * 2, b'\x00'))
    return bytes(out), 1


# ------------------------------------------------------------------ 실행
START_ELEMENT = 0x0102


def manifest_pkg(b):
    """`<manifest package="…">` 속성을 정직하게 읽습니다.

    '다른 문자열의 앞머리인 것' 같은 눈대중은 쓰지 않습니다. 이름을 한 번
    바꾸고 나면 더는 앞머리가 아니어서 엉뚱한 걸 집습니다
    (`android.hardware.touchscreen` 을 집었습니다)."""
    strs, _, _ = axml_strings(b)
    pool_size = u32(b, 12)
    off = 8 + pool_size
    while off + 8 <= len(b):
        typ = u16(b, off)
        size = u32(b, off + 4)
        if size <= 0:
            break
        if typ == START_ELEMENT:
            name = strs[u32(b, off + 20)]
            if name == 'manifest':
                hdr = u16(b, off + 2)
                a_start = u16(b, off + 24)
                a_size = u16(b, off + 26)
                a_cnt = u16(b, off + 28)
                base = off + hdr + a_start      # 속성 자리는 **머리 뒤**부터
                for i in range(a_cnt):
                    p = base + i * a_size
                    nm = u32(b, p + 4)
                    if nm < len(strs) and strs[nm] == 'package':
                        raw = u32(b, p + 8)
                        return strs[raw] if raw < len(strs) else None
                return None
        off += size
    return None


def current_pkg(apk):
    return manifest_pkg(zipfile.ZipFile(apk).read('AndroidManifest.xml'))


def main():
    if len(sys.argv) >= 3 and sys.argv[2] == '--show':
        print(current_pkg(sys.argv[1]) or '(못 찾았습니다)')
        return 0
    if len(sys.argv) < 4:
        raise SystemExit(__doc__.strip().splitlines()[-2].strip())
    src, dst, new = sys.argv[1], sys.argv[2], sys.argv[3]
    old = sys.argv[4] if len(sys.argv) > 4 else current_pkg(src)
    if not old:
        raise SystemExit('지금 패키지 이름을 못 알아냈습니다')
    if old == new:
        print('이미 %s 입니다' % new)

    zin = zipfile.ZipFile(src)
    mf, delta, n = axml_setpkg(zin.read('AndroidManifest.xml'), old, new)
    print('매니페스트: %r -> %r (%d곳, 크기 %+d)' % (old, new, n, delta))
    arsc = zin.read('resources.arsc')
    arsc, k = arsc_setpkg(arsc, old, new)
    print('resources.arsc: 패키지 이름 %s' % ('바꿨습니다' if k else '없어서 건너뜁니다'))

    zout = zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED)
    for info in zin.infolist():
        nm = info.filename
        if nm.startswith('META-INF/') and (
                nm.upper().endswith(('.SF', '.RSA', '.DSA', '.EC'))
                or nm == 'META-INF/MANIFEST.MF'):
            continue
        if nm == 'AndroidManifest.xml':
            zout.writestr(info, mf, info.compress_type)
        elif nm == 'resources.arsc':
            zout.writestr(info, arsc, info.compress_type)
        else:
            zout.writestr(info, zin.read(nm), info.compress_type)
    zout.close()
    print('%s -> %s' % (src, dst))
    return 0


if __name__ == '__main__':
    sys.exit(main())
