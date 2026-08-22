# -*- coding: utf-8 -*-
"""
범용 APK 리패키저.

  1) assets/libs/<abi>/*.so 의 정품 라이브러리를 lib/<abi>/ 로 되돌린다.
     (2014년 안티탬퍼 커스텀 ELF 로더가 IFUNC 재배치를 처리 못해 최신 안드로이드에서 크래시)
  2) 선택: Unity 에셋에 직렬화된 CDN 베이스 URL 을 같은 길이로 제자리 교체
  3) 선택: 패치된 Assembly-CSharp.dll 주입
  4) 기존 서명 제거 (호출부에서 jarsigner 로 재서명)

사용법:
  python buildapk.py <src.apk> <out.apk> [--url <base>] [--dll <path>] [--asset <entry>]
"""
import zipfile, struct, sys, os, argparse

ORIG_URL = b"http://cr.img.mcdn.netmarble.kr/cr/Real/Android/"   # 48바이트


def swap_map(names):
    """assets/libs/<abi>/<name>.so -> lib/<abi>/<name>.so 매핑을 만든다."""
    out = {}
    for n in names:
        if n.startswith("assets/libs/") and n.endswith(".so"):
            dst = "lib/" + n[len("assets/libs/"):]
            if dst in names:
                out[dst] = n
    return out


def fit_url(base, length):
    if not base.endswith('/'):
        base += '/'
    if len(base) > length:
        raise SystemExit("[에러] 베이스 URL 이 %d바이트 (최대 %d)" % (len(base), length))
    need = length - len(base)
    if need == 0:
        return base
    return base + ('/' if need == 1 else 'x' * (need - 1) + '/')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("out")
    ap.add_argument("--url"); ap.add_argument("--dll")
    ap.add_argument("--asset", default="assets/bin/Data/46d4d4a5ba7c79e469ef05e22157e120")
    a = ap.parse_args()

    zin = zipfile.ZipFile(a.src)
    names = set(zin.namelist())
    payload = {}

    for dst, src in swap_map(names).items():
        payload[dst] = zin.read(src)
        print("라이브러리 교체: %-34s <- %s (%d bytes)" % (dst, src, len(payload[dst])))
    if not payload:
        print("라이브러리 교체 대상 없음 (assets/libs 구조가 아님)")

    if a.url:
        if a.asset not in names:
            raise SystemExit("[에러] 에셋 엔트리 없음: " + a.asset)
        data = bytearray(zin.read(a.asset))
        i = bytes(data).find(ORIG_URL)
        if i < 0:
            raise SystemExit("[에러] 원본 URL 을 찾지 못함")
        n = struct.unpack_from('<I', data, i - 4)[0]
        url = fit_url(a.url, n)
        data[i:i + n] = url.encode()
        payload[a.asset] = bytes(data)
        print("URL 패치: %s (길이 %d 유지)" % (url, n))

    if a.dll:
        entry = "assets/bin/Data/Managed/Assembly-CSharp.dll"
        payload[entry] = open(a.dll, 'rb').read()
        print("DLL 주입: %s (%d bytes)" % (a.dll, len(payload[entry])))

    if os.path.exists(a.out):
        os.remove(a.out)
    zout = zipfile.ZipFile(a.out, "w", zipfile.ZIP_DEFLATED)
    swapped = copied = 0
    for info in zin.infolist():
        n = info.filename
        if n.startswith("META-INF/") and (
                n.upper().endswith((".SF", ".RSA", ".DSA", ".EC")) or n == "META-INF/MANIFEST.MF"):
            continue
        if n in payload:
            zout.writestr(n, payload[n], zipfile.ZIP_DEFLATED); swapped += 1
        else:
            zout.writestr(info, zin.read(n), info.compress_type); copied += 1
    zout.close(); zin.close()
    print("교체 %d / 복사 %d -> %s (%.1f MB)" % (swapped, copied, a.out,
                                                os.path.getsize(a.out) / 1048576))


if __name__ == '__main__':
    main()
