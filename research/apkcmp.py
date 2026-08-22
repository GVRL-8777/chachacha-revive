# -*- coding: utf-8 -*-
"""여러 APK 의 Unity 버전 / 번들 유무 / 로컬 Resources 경로를 비교한다."""
import zipfile, re, sys, io, os

APKS = sys.argv[1:]
PATH = re.compile(rb'^[a-zA-Z0-9_\-/ ().@#&+]{2,120}$')

def respaths(z):
    try: d = z.read("assets/bin/Data/mainData")
    except KeyError: return set()
    out = set()
    for m in re.finditer(rb'(?=([\x02-\x78]\x00\x00\x00))', d):
        ln = d[m.start()]
        s = d[m.start()+4:m.start()+4+ln]
        if len(s) == ln and PATH.match(s):
            out.add(s.decode('ascii'))
    return out

for apk in APKS:
    z = zipfile.ZipFile(apk)
    names = z.namelist()
    u3d = [n for n in names if n.endswith('.unity3d')]
    unity = "?"
    for cand in ("assets/bin/Data/mainData", "assets/bin/Data/globalgamemanagers"):
        if cand in names:
            m = re.findall(rb'\d+\.\d+\.\d+[a-z]\d+', z.read(cand)[:400])
            if m: unity = m[0].decode(); break
    total = sum(i.file_size for i in z.infolist())
    rp = respaths(z)
    print("=" * 70)
    print("%s  (%.1f MB, 압축해제 %.1f MB)" % (os.path.basename(apk),
          os.path.getsize(apk)/1048576, total/1048576))
    print("  Unity %s | 엔트리 %d | .unity3d %d개 | Resources 경로 %d종"
          % (unity, len(names), len(u3d), len(rp)))
    io.open(os.path.basename(apk) + ".paths.txt", "w", encoding="utf-8").write("\n".join(sorted(rp)))
    # 우리가 필요한 것들
    for key, pat in (("도로(background/background)", r'^background/background'),
                     ("PlayerEffect", r'playereffect'),
                     ("Atlas_Cutin", r'atlas_cutin'),
                     ("Player_ 차량 프리팹", r'/player_[a-z0-9_]+_[asrbc](_low)?$'),
                     ("사운드/보이스", r'(vox|bgm|sound)')):
        hit = sorted(p for p in rp if re.search(pat, p, re.I))
        print("   %-26s %3d개  %s" % (key, len(hit), hit[:3]))
