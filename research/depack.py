"""
안티탬퍼 프록시 로더를 걷어내고 정품 Unity/Mono 라이브러리를 lib/ 로 되돌린다.

원본 구조:
  lib/armeabi-v7a/libunity.so      47KB  <- 커스텀 ELF 로더(프록시). IFUNC 미지원 -> 크래시
  lib/armeabi-v7a/libmono.so       92KB  <- 동일
  assets/libs/armeabi-v7a/libunity.so  9.2MB  <- 진짜
  assets/libs/armeabi-v7a/libmono.so   3.9MB  <- 진짜

결과: 시스템 링커가 정품 .so 를 직접 로드 -> IFUNC 정상 처리
"""
from _here import apk
import zipfile, shutil, sys, os

SRC = apk('kr')
OUT = sys.argv[1] if len(sys.argv) > 1 else "unpacked.apk"

SWAP = {
    "lib/armeabi-v7a/libunity.so": "assets/libs/armeabi-v7a/libunity.so",
    "lib/armeabi-v7a/libmono.so":  "assets/libs/armeabi-v7a/libmono.so",
}

zin = zipfile.ZipFile(SRC, "r")
names = zin.namelist()

# 교체 원본을 미리 읽어둔다
payload = {}
for dst, src in SWAP.items():
    payload[dst] = zin.read(src)
    print(f"  {dst}\n     <- {src}  ({len(payload[dst]):,} bytes, 원래 {zin.getinfo(dst).file_size:,})")

if os.path.exists(OUT):
    os.remove(OUT)
zout = zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED)

copied = swapped = skipped = 0
for info in zin.infolist():
    n = info.filename
    # 기존 서명은 무효가 되므로 제외 (재서명 필요)
    if n.startswith("META-INF/") and n.split("/")[-1].upper().endswith((".SF", ".RSA", ".DSA", ".EC")):
        skipped += 1
        continue
    if n == "META-INF/MANIFEST.MF":
        skipped += 1
        continue
    if n in payload:
        zout.writestr(n, payload[n], zipfile.ZIP_DEFLATED)
        swapped += 1
        continue
    zout.writestr(info, zin.read(n), info.compress_type)
    copied += 1

zout.close()
zin.close()

print(f"\n교체 {swapped} / 복사 {copied} / 제외(서명) {skipped}")
print(f"출력: {OUT}  ({os.path.getsize(OUT):,} bytes)")
