# -*- coding: utf-8 -*-
"""두 APK 의 Texture2D 를 이름별로 모아 해상도/포맷을 비교한다.
   신버전 UI 가 더 거칠어 보이는 이유(해상도가 실제로 낮은지)를 확인하기 위한 것."""
import os, sys, collections, UnityPy

def scan(folder):
    out = {}
    for f in os.listdir(folder):
        p = os.path.join(folder, f)
        if not os.path.isfile(p):
            continue
        try:
            env = UnityPy.load(p)
        except Exception:
            continue
        for r in env.objects:
            if r.type.name != "Texture2D":
                continue
            try:
                t = r.read()
            except Exception:
                continue
            nm = (t.m_Name or "").strip()
            if not nm:
                continue
            prev = out.get(nm)
            cur = (t.m_Width, t.m_Height, int(t.m_TextureFormat))
            if prev is None or cur[0] * cur[1] > prev[0] * prev[1]:
                out[nm] = cur
    return out

a = scan(sys.argv[1])   # 7.7.0
b = scan(sys.argv[2])   # 8.apk
print("7.7.0 텍스처 %d개 / 8.apk 텍스처 %d개" % (len(a), len(b)))

common = sorted(set(a) & set(b))
print("\n이름이 같은 텍스처 %d개 중 해상도가 다른 것:" % len(common))
diff = 0
for k in common:
    if a[k][:2] != b[k][:2]:
        diff += 1
        if diff <= 25:
            print("  %-34s 7.7.0=%dx%d(fmt%d)  8.apk=%dx%d(fmt%d)"
                  % (k, a[k][0], a[k][1], a[k][2], b[k][0], b[k][1], b[k][2]))
print("  ... 총 %d개 상이" % diff)

smaller = [k for k in common if a[k][0] * a[k][1] < b[k][0] * b[k][1]]
bigger = [k for k in common if a[k][0] * a[k][1] > b[k][0] * b[k][1]]
print("\n7.7.0 이 더 작은 것: %d개 / 더 큰 것: %d개" % (len(smaller), len(bigger)))

fmt_a = collections.Counter(v[2] for v in a.values())
fmt_b = collections.Counter(v[2] for v in b.values())
print("\n포맷 분포 7.7.0:", fmt_a.most_common(6))
print("포맷 분포 8.apk:", fmt_b.most_common(6))

ui_a = {k: v for k, v in a.items() if 'atlas' in k.lower() or 'ui' in k.lower()}
ui_b = {k: v for k, v in b.items() if 'atlas' in k.lower() or 'ui' in k.lower()}
print("\nUI 아틀라스 예시 (7.7.0):")
for k in sorted(ui_a)[:12]:
    print("   %-34s %dx%d fmt%d" % (k, ui_a[k][0], ui_a[k][1], ui_a[k][2]))
print("UI 아틀라스 예시 (8.apk):")
for k in sorted(ui_b)[:12]:
    print("   %-34s %dx%d fmt%d" % (k, ui_b[k][0], ui_b[k][1], ui_b[k][2]))
