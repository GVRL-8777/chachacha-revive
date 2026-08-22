# -*- coding: utf-8 -*-
"""gogogoracer 1.4.2 의 helly(변신 로봇 차량) 자산 스펙을 만든다.

중국판 클라이언트는 로봇 차량을 **이미 지원한다**:
  CarDataLinker::Update 가 "Car/{0}/{0}_robot@{1}" 을 로드하고
  EffectManager::Setting 이 "Car/{0}/{0}_Robot_Effect" 를 로드하며
  차량 DB 스키마에 IsRobot 필드가 있다. 자산만 없다.

컨테이너 키는 gogogoracer 카탈로그 경로 그대로(이미 소문자)를 쓴다.
클라이언트가 요청하는 "Car/helly/..." 는 Load 가 소문자로 바꿔 비교하므로 맞는다.
"""
import io, os, UnityPy
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile

D = 'survey/gogo142/assets/bin/Data'
env = UnityPy.load(os.path.join(D, 'mainData'))
rm = [r for r in env.objects if r.type.name == 'ResourceManager'][0].read()
af = env.objects[0].assets_file

# 경로 하나에 오브젝트가 여러 개 걸린 경우가 있다(프리팹 루트 + 하위).
# 프리팹은 GameObject 를, 나머지는 파일의 첫 오브젝트를 고른다.
cands = {}
for p, ptr in rm.m_Container:
    if not p.startswith('car/helly/') or not ptr.file_id:
        continue
    fn = os.path.basename(af.externals[ptr.file_id - 1].path)
    cands.setdefault(p, []).append((fn, ptr.path_id))

specs, roots = [], []
for p in sorted(cands):
    best = None
    for fn, pid in cands[p]:
        fp = os.path.join(D, fn)
        if not os.path.exists(fp):
            continue
        sf = SerializedFile(EndianBinaryReader(io.open(fp, 'rb').read()), None)
        o = sf.objects.get(pid)
        if o is None:
            continue
        # GameObject 를 최우선, 그 다음은 아무거나
        rank = 0 if o.type.name == 'GameObject' else 1
        if best is None or rank < best[0]:
            best = (rank, fn, pid, o.type.name)
    if best is None:
        print("  건너뜀(대상 없음): %s" % p)
        continue
    _, fn, pid, tn = best
    specs.append('%s/%s:%s:%d' % (D, fn, p, pid))
    roots.append(fn)
    print("  %-38s %-14s pid=%s" % (p, tn, pid))

io.open('hellyspec.txt', 'w', encoding='utf-8').write('\n'.join(specs) + '\n')
io.open('hellyroots.txt', 'w', encoding='utf-8').write('\n'.join(sorted(set(roots))) + '\n')
print("helly 자산 %d개 / 루트 파일 %d개" % (len(specs), len(set(roots))))
