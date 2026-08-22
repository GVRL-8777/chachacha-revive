# -*- coding: utf-8 -*-
"""유니티 4 용 UnityRaw(무압축) 에셋번들을 만든다.

목적: 색인(mainData)을 건드리지 않고 **자산을 추가**하기 위해서다.
클라이언트는 `WWW.assetBundle` -> `AssetBundle.Load(이름, 타입)` 으로 꺼내 쓴다.
(두 API 모두 libunity.so 에 icall 이 살아 있음을 확인했다)

핵심: 담을 내용은 배포판에서 뽑은 직렬화 파일 **그대로**다.
이미 Unity 4.1.5 레이아웃이라 재인코딩이 필요 없고, 우리는 컨테이너만 씌운다.

레이아웃 (전부 빅엔디안):
  "UnityRaw\\0"
  u32 version = 3
  str version_player  ("3.x.x")
  str version_engine  ("4.1.5f1")
  u32 minimumStreamedBytes
  u32 headerSize
  u32 numberOfLevelsToDownloadBeforeStreaming
  i32 levelCount (=1)
  u32 compressedSize      (= 디렉터리+데이터 길이)
  u32 uncompressedSize    (동일)
  u32 completeFileSize
  u32 fileInfoHeaderSize
  --- headerSize 위치부터 ---
  i32 nodeCount
  node × { str path; u32 offset(headerSize 기준); u32 size }
  ... 파일 데이터 ...

사용법: python mkbundle.py <출력.unity3d> <넣을파일> [내부이름]
"""
import struct, sys, os, io


def bw(*parts):
    return b''.join(parts)


def u32(v):
    return struct.pack('>I', v)


def i32(v):
    return struct.pack('>i', v)


def cstr(s):
    return s.encode('utf-8') + b'\x00'


def build(files, engine_ver='4.1.5f1', player_ver='3.x.x'):
    """files: [(내부이름, 바이트)]"""
    # 1) 디렉터리 + 데이터 블록 만들기 (offset 은 headerSize 기준 상대값)
    #    디렉터리 크기를 먼저 알아야 offset 을 정할 수 있으므로 두 번 계산한다.
    def dir_size(offsets):
        b = i32(len(files))
        for (name, data), off in zip(files, offsets):
            b += cstr(name) + u32(off) + u32(len(data))
        return len(b)

    offs = [0] * len(files)
    for _ in range(4):                      # 수렴할 때까지 반복
        ds = dir_size(offs)
        cur = (ds + 3) & ~3                 # 엔진은 노드 데이터 시작을 4바이트로 정렬해 읽는다
        new = []
        for name, data in files:
            new.append(cur)
            cur += len(data)
            cur = (cur + 3) & ~3            # 4바이트 정렬
        if new == offs:
            break
        offs = new

    block = bytearray()
    block += i32(len(files))
    for (name, data), off in zip(files, offs):
        block += cstr(name) + u32(off) + u32(len(data))
    for (name, data), off in zip(files, offs):
        while len(block) < off:
            block += b'\x00'
        block += data
    while len(block) % 4:
        block += b'\x00'
    block = bytes(block)

    # 2) 헤더. headerSize 를 알아야 하므로 역시 반복 계산한다.
    header_size = 0
    for _ in range(4):
        h = bw(cstr('UnityRaw'), u32(3), cstr(player_ver), cstr(engine_ver))
        h += u32(len(block))                # minimumStreamedBytes
        h += u32(header_size)               # headerSize
        h += u32(1)                         # numberOfLevelsToDownloadBeforeStreaming
        h += i32(1)                         # levelCount
        h += u32(len(block))                # compressedSize
        h += u32(len(block))                # uncompressedSize
        h += u32(header_size + len(block))  # completeFileSize
        h += u32(header_size)               # fileInfoHeaderSize
        if len(h) == header_size:
            break
        header_size = len(h)
    while len(h) < header_size:
        h += b'\x00'
    return h + block


def main():
    out = sys.argv[1]
    src = sys.argv[2]
    name = sys.argv[3] if len(sys.argv) > 3 else 'CAB-' + os.path.basename(src)[:16]
    data = io.open(src, 'rb').read()
    blob = build([(name, data)])
    io.open(out, 'wb').write(blob)
    print("번들 생성: %s (%.1f KB, 내부이름 %s)" % (out, len(blob) / 1024, name))

    # 역검증: UnityPy 로 다시 열어 본다
    try:
        import UnityPy
        env = UnityPy.load(out)
        objs = list(env.objects)
        print("역검증: 오브젝트 %d개" % len(objs))
        for r in objs[:8]:
            try:
                nm = r.read().m_Name
            except Exception:
                nm = ''
            print("   pathId=%-4s %-16s %s" % (r.path_id, r.type.name, nm))
    except Exception as e:
        print("역검증 실패:", type(e).__name__, e)


main()
