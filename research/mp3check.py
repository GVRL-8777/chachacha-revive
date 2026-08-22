# -*- coding: utf-8 -*-
"""뽑아낸 MP3 가 정상 프레임을 갖췄는지 확인하고 대략적인 길이를 계산한다."""
import io, os, glob

BR = {  # MPEG1 Layer3 비트레이트 표 (kbps)
    1: 32, 2: 40, 3: 48, 4: 56, 5: 64, 6: 80, 7: 96,
    8: 112, 9: 128, 10: 160, 11: 192, 12: 224, 13: 256, 14: 320}
SR = {0: 44100, 1: 48000, 2: 32000}

for path in sorted(glob.glob(r'D:\Vibes\ChaChaCha\*.mp3')):
    b = io.open(path, 'rb').read()
    # 첫 동기 워드 찾기
    i = 0
    while i < len(b) - 4:
        if b[i] == 0xFF and (b[i + 1] & 0xE0) == 0xE0:
            break
        i += 1
    if i >= len(b) - 4:
        print("%-28s 프레임 없음 (MP3 아님?)" % os.path.basename(path))
        continue
    h = b[i:i + 4]
    ver = (h[1] >> 3) & 3          # 3 = MPEG1
    layer = (h[1] >> 1) & 3        # 1 = Layer3
    bri = (h[2] >> 4) & 0xF
    sri = (h[2] >> 2) & 3
    ch = (h[3] >> 6) & 3
    br = BR.get(bri, 0)
    sr = SR.get(sri, 0)
    # 프레임 개수로 길이 추정
    frames, p = 0, i
    while p < len(b) - 4:
        if b[p] == 0xFF and (b[p + 1] & 0xE0) == 0xE0:
            bi = (b[p + 2] >> 4) & 0xF
            si = (b[p + 2] >> 2) & 3
            if bi in BR and si in SR:
                flen = int(144 * BR[bi] * 1000 / SR[si]) + ((b[p + 2] >> 1) & 1)
                if flen > 4:
                    frames += 1
                    p += flen
                    continue
        p += 1
    dur = frames * 1152.0 / sr if sr else 0
    print("%-28s %6d B | 오프셋 %d | MPEG%s Layer%s | %dkbps %dHz %s | 프레임 %d | 약 %.2f초"
          % (os.path.basename(path), len(b), i,
             {3: '1', 2: '2', 0: '2.5'}.get(ver, '?'),
             {1: '3', 2: '2', 3: '1'}.get(layer, '?'),
             br, sr, ['스테레오', '조인트', '듀얼', '모노'][ch], frames, dur))
