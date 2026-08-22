"""
차차차 APK 빌더: 안티탬퍼 프록시 제거 + AssetCatalogue 베이스 URL 리다이렉트.

1) lib/armeabi-v7a/{libunity,libmono}.so 를 assets/libs/ 의 정품으로 교체
   (2014년 커스텀 ELF 로더가 IFUNC 재배치를 처리 못해 최신 Android 에서 크래시)
2) Unity 에셋에 직렬화된 CDN 베이스 URL 을 우리 서버로 교체
   원본: http://cr.img.mcdn.netmarble.kr/cr/Real/Android/   (48바이트)
   Unity 문자열은 [int32 길이][바이트] 형식이라 길이를 그대로 48로 맞추면
   파일 시프트 없이 제자리 패치가 된다. 경로는 우리가 서버를 만드니 자유.

사용법: python buildpatched.py <base_url> <out.apk>
   예:  python buildpatched.py http://192.168.0.100:8888/ out.apk
"""
from _here import apk
import zipfile, struct, sys, os

SRC = apk('kr')
ASSET = "assets/bin/Data/46d4d4a5ba7c79e469ef05e22157e120"
ORIG = b"http://cr.img.mcdn.netmarble.kr/cr/Real/Android/"   # 48 bytes
SWAP = {
    "lib/armeabi-v7a/libunity.so": "assets/libs/armeabi-v7a/libunity.so",
    "lib/armeabi-v7a/libmono.so":  "assets/libs/armeabi-v7a/libmono.so",
}
TARGET_LEN = len(ORIG)   # 48


def make_url(base):
    """base 를 정확히 TARGET_LEN 바이트로 맞춘다. 부족하면 필러 경로 세그먼트를 끼운다."""
    if not base.endswith('/'):
        base += '/'
    if len(base) > TARGET_LEN:
        raise SystemExit(
            "[에러] 베이스 URL 이 %d바이트로 너무 깁니다 (최대 %d).\n"
            "       더 짧은 호스트(IP 또는 짧은 도메인)를 쓰세요." % (len(base), TARGET_LEN))
    need = TARGET_LEN - len(base)
    if need == 0:
        return base
    if need == 1:
        return base + '/'          # 빈 세그먼트 (서버에서 //로 들어옴)
    # 'x'*(need-1) + '/'  -> 한 개의 필러 디렉터리
    return base + 'x' * (need - 1) + '/'


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    base = sys.argv[1]
    out = sys.argv[2]
    # 선택: IL 패치된 Assembly-CSharp.dll 을 끼워넣는다 (게스트 로그인 + 판수 제한 해제)
    patched_dll = sys.argv[3] if len(sys.argv) > 3 else None
    url = make_url(base)
    assert len(url) == TARGET_LEN
    print("원본 URL : %s" % ORIG.decode())
    print("교체 URL : %s   (%d바이트, 길이 동일)" % (url, len(url)))
    print("게임이 실제로 요청할 주소:\n   %sCatalogue/AssetCatalogue.txt\n" % url)

    zin = zipfile.ZipFile(SRC)

    # 에셋 패치
    data = bytearray(zin.read(ASSET))
    idx = bytes(data).find(ORIG)
    if idx < 0:
        raise SystemExit("[에러] 에셋에서 원본 URL 을 찾지 못했습니다.")
    prefix = struct.unpack_from('<I', data, idx - 4)[0]
    if prefix != TARGET_LEN:
        raise SystemExit("[에러] 길이 접두사가 %d (예상 %d)" % (prefix, TARGET_LEN))
    data[idx:idx + TARGET_LEN] = url.encode()
    print("에셋 패치: offset 0x%05x, 접두사 %d 유지" % (idx, prefix))

    payload = {ASSET: bytes(data)}
    for dst, src in SWAP.items():
        payload[dst] = zin.read(src)
        print("라이브러리 교체: %s <- %s (%d bytes)" % (dst, src, len(payload[dst])))

    if patched_dll:
        entry = "assets/bin/Data/Managed/Assembly-CSharp.dll"
        blob = open(patched_dll, 'rb').read()
        orig_len = zin.getinfo(entry).file_size
        if len(blob) != orig_len:
            print("  [경고] 패치 DLL 크기가 원본과 다릅니다 (%d != %d)" % (len(blob), orig_len))
        payload[entry] = blob
        print("IL 패치 DLL 적용: %s (%d bytes)" % (patched_dll, len(blob)))

    if os.path.exists(out):
        os.remove(out)
    zout = zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED)
    n_copy = n_swap = 0
    for info in zin.infolist():
        n = info.filename
        if n.startswith("META-INF/") and (
                n.upper().endswith((".SF", ".RSA", ".DSA", ".EC")) or n == "META-INF/MANIFEST.MF"):
            continue
        if n in payload:
            zout.writestr(n, payload[n], zipfile.ZIP_DEFLATED)
            n_swap += 1
        else:
            zout.writestr(info, zin.read(n), info.compress_type)
            n_copy += 1
    zout.close()
    zin.close()
    print("\n교체 %d / 복사 %d -> %s (%d bytes)" % (n_swap, n_copy, out, os.path.getsize(out)))
    print("다음: jarsigner 로 서명 후 adb install")


if __name__ == '__main__':
    main()
