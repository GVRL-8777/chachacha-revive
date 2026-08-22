# -*- coding: utf-8 -*-
"""APK 들을 훑어 버전/유니티/리소스 목록을 뽑는다."""
import os, sys, zipfile, re, io, subprocess, shutil
import UnityPy

APKS = sys.argv[1:]
OUT = 'survey'
os.makedirs(OUT, exist_ok=True)


def merge_splits(d):
    import collections
    groups = collections.defaultdict(list)
    for f in os.listdir(d):
        m = re.match(r'(.+)\.split(\d+)$', f)
        if m:
            groups[m.group(1)].append((int(m.group(2)), f))
    for base, parts in groups.items():
        parts.sort()
        with open(os.path.join(d, base), 'wb') as w:
            for _, f in parts:
                w.write(open(os.path.join(d, f), 'rb').read())
        for _, f in parts:
            os.remove(os.path.join(d, f))
    return len(groups)


for apk in APKS:
    name = os.path.splitext(os.path.basename(apk))[0]
    print("=" * 70)
    print(apk, "(%.1f MB)" % (os.path.getsize(apk) / 1048576))
    try:
        z = zipfile.ZipFile(apk)
    except Exception as e:
        print("  ZIP 열기 실패:", e)
        continue
    names = z.namelist()
    print("  엔트리 %d개" % len(names))
    if not any(n.startswith('assets/bin/Data/') for n in names):
        print("  유니티 데이터 없음 -> 실제 게임 APK 가 아님")
        print("  상위 엔트리:", names[:12])
        continue

    d = os.path.join(OUT, name, 'assets/bin/Data')
    if not os.path.isdir(d):
        for n in names:
            if n.startswith('assets/bin/Data/'):
                z.extract(n, os.path.join(OUT, name))
        merged = merge_splits(d)
        print("  split 병합 %d개" % merged)
    print("  Data 파일 %d개" % len(os.listdir(d)))

    # 유니티 버전
    try:
        head = open(os.path.join(d, 'mainData'), 'rb').read(64)
        m = re.search(rb'(\d\.\d+\.\d+[a-z]\d+)', head)
        print("  유니티:", m.group(1).decode() if m else "?")
    except Exception as e:
        print("  mainData 없음:", e)
        continue

    try:
        env = UnityPy.load(os.path.join(d, 'mainData'))
        rm = [r for r in env.objects if r.type.name == "ResourceManager"][0].read()
        paths = sorted(set(p for p, _ in rm.m_Container))
        io.open(os.path.join(OUT, name + '.txt'), 'w', encoding='utf-8').write("\n".join(paths))
        print("  리소스 경로 %d개 -> %s.txt" % (len(paths), name))
        import collections
        top = collections.Counter(p.split('/')[0] for p in paths)
        print("  최상위:", top.most_common(8))
        cars = sorted(set(p.split('/')[1] for p in paths if p.startswith('car/') and '/' in p[4:]))
        print("  car 하위 %d종: %s" % (len(cars), cars[:18]))
        for kw in ('helly', 'completemap', 'atlas', 'font'):
            hit = [p for p in paths if kw in p.lower()]
            print("  '%s' %d개: %s" % (kw, len(hit), hit[:4]))
    except Exception as e:
        print("  리소스 목록 실패:", type(e).__name__, e)
