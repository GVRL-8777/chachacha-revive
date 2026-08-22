"""
게임 컨텐츠 데이터(차량 스탯/아이템/미션)가 APK 안에 있는지 확인한다.
있으면 로컬만으로 복원 가능, 없으면 죽은 CDN 에셋 번들이 필요하다.
"""
import zipfile, re, collections

APK = r"D:\Vibes\ChaChaCha\CCC_fK_v7.7.0.apk"
z = zipfile.ZipFile(APK)

# 게스트 기본차 AVEO 를 비롯한 차량명/데이터 흔적
PATTERNS = {
    "AVEO(기본차)": rb'AVEO',
    "CarData류":    rb'(PlayerCarData|CarDataBase|CarData|carFuleCost|correctedOilmileage)',
    "DataBase번들": rb'(DataBase|AssetBundle)',
    "아이템/미션":   rb'(ItemData|MissionData|SkillData|itemCode)',
}

hits = collections.defaultdict(list)
for name in z.namelist():
    if name.endswith('/'):
        continue
    try:
        data = z.read(name)
    except Exception:
        continue
    for label, pat in PATTERNS.items():
        found = re.findall(pat, data)
        if found:
            hits[label].append((name, len(found), len(data)))

for label in PATTERNS:
    lst = sorted(hits[label], key=lambda t: -t[1])
    print("=" * 62)
    print("[%s]  %d개 엔트리에서 발견" % (label, len(lst)))
    for name, cnt, size in lst[:8]:
        print("   %-52s x%-4d (%d bytes)" % (name[:52], cnt, size))
    print()

# AVEO 주변 문맥 (차량 리소스 경로인지 데이터 레코드인지 구분)
print("=" * 62)
print("[AVEO 문맥]")
for name in z.namelist():
    if name.endswith('/'):
        continue
    try:
        data = z.read(name)
    except Exception:
        continue
    for m in re.finditer(rb'AVEO', data):
        s = max(0, m.start() - 60)
        ctx = data[s:m.end() + 60]
        printable = re.sub(rb'[^\x20-\x7e]', b'.', ctx).decode('ascii')
        print("   %s @0x%x: %s" % (name.split('/')[-1][:28], m.start(), printable))
        break
