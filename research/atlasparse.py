# -*- coding: utf-8 -*-
"""NGUI UIAtlas(MonoBehaviour)의 스프라이트 목록을 원시 바이트에서 해석한다.

플레이어 빌드엔 사용자 스크립트 타입트리가 없어 정식 파싱이 불가능하다.
그러나 NGUI 2.x 의 UIAtlas.Sprite 는 다음 순서로 직렬화된다:
    string name (길이 접두 + UTF8 + 4바이트 정렬)
    float outer.x, outer.y, outer.width, outer.height      (xMin,yMin,width,height)
    float inner.x, inner.y, inner.width, inner.height
    ... (판본에 따라 paddingLeft/Right/Top/Bottom 등 float/int 가 이어짐)

스프라이트 이름들이 배열로 연달아 나오므로, 이름을 찾은 뒤 그 뒤의 float 8개를
읽으면 좌표를 얻을 수 있다. 실제 값이 텍스처 크기 범위 안에 드는지로 검증한다.

사용법: python atlasparse.py <파일> <pathID> [텍스처폭] [텍스처높이]
"""
import io, re, struct, sys
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile

path, pid = sys.argv[1], int(sys.argv[2])
TW = int(sys.argv[3]) if len(sys.argv) > 3 else 0
TH = int(sys.argv[4]) if len(sys.argv) > 4 else 0

sf = SerializedFile(EndianBinaryReader(io.open(path, 'rb').read()), None)
d = sf.objects[pid].get_raw_data()
print("MonoBehaviour %d바이트" % len(d))


def read_str(b, off):
    """길이 접두 문자열을 읽고 (문자열, 다음 오프셋) 을 준다. 실패 시 (None, off)."""
    if off + 4 > len(b):
        return None, off
    n = struct.unpack_from('<i', b, off)[0]
    if not (0 < n <= 128) or off + 4 + n > len(b):
        return None, off
    try:
        s = b[off + 4:off + 4 + n].decode('utf-8')
    except UnicodeDecodeError:
        return None, off
    if not re.fullmatch(r'[\w\-. ()\[\]]+', s):
        return None, off
    return s, off + 4 + ((n + 3) & ~3)


sprites = []
off = 0
while off < len(d) - 4:
    s, nxt = read_str(d, off)
    if s is None:
        off += 4
        continue
    # 이름 뒤 float 8개를 좌표로 시도
    if nxt + 32 <= len(d):
        f = struct.unpack_from('<8f', d, nxt)
        ok = all(-1.0 <= v <= max(TW, TH, 4096) + 1 for v in f)
        if ok and f[2] > 0 and f[3] > 0:
            sprites.append((s, tuple(round(x, 1) for x in f[:4]), nxt))
            off = nxt + 32
            continue
    off = nxt

print("스프라이트 후보 %d개" % len(sprites))
for name, outer, o in sprites:
    print("  %-26s x=%-7s y=%-7s w=%-7s h=%-7s  @%d" % (name, outer[0], outer[1], outer[2], outer[3], o))
