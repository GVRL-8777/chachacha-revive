# -*- coding: utf-8 -*-
"""이식할 보이스 클립의 sfmerge 스펙 목록을 만든다.

중국판에 없는 캐릭터의 보이스를 카카오판에서 가져온다.
  드라이버용 : PIG, GYARU, ANGRY           (드라이버 슬롯 4, 5, 6)
  차 이름용  : POLY, AMBER, ROI, HELLY     (Player::_GetCutinModel 이 차 이름으로 덮어쓴다)
  ROPE(슬롯 7) 는 어느 배포판에도 원본이 없다.

컨테이너 키는 게임이 Resources.Load 에 넘기는 문자열 그대로 쓴다:
  "Character VOX/<모델>/<모델>_VOX_<보이스타입>"
"""
import io, os, UnityPy

D = 'survey/racechachachaforkakao/assets/bin/Data'
# 기본 드라이버 4명(sara bin dokang nayoubi)의 보이스는 중국판에도 있지만
# 중국어 더빙이라 카카오판(한국어)으로 갈아 끼운다.
WANT = ['pig', 'gyaru', 'angry', 'poly', 'amber', 'roi', 'helly',
        'sara', 'bin', 'dokang', 'nayoubi']

env = UnityPy.load(os.path.join(D, 'mainData'))
rm = [r for r in env.objects if r.type.name == 'ResourceManager'][0].read()
af = env.objects[0].assets_file

out, missing = [], []
for p, ptr in rm.m_Container:
    parts = p.split('/')
    if len(parts) != 3 or parts[0] != 'character vox' or parts[1] not in WANT:
        continue
    fn = os.path.basename(af.externals[ptr.file_id - 1].path) if ptr.file_id else None
    if not fn or not os.path.exists(os.path.join(D, fn)):
        missing.append(p)
        continue
    model = parts[1].upper()
    suffix = parts[2].split('_vox_')[-1].upper()
    key = "Character VOX/%s/%s_VOX_%s" % (model, model, suffix)
    out.append("%s/%s:%s:%d" % (D, fn, key, ptr.path_id))

out.sort()
io.open('voxspec.txt', 'w', encoding='utf-8').write('\n'.join(out))
print("보이스 클립 %d개 (캐릭터 %d명) -> voxspec.txt" % (len(out), len(WANT)))
if missing:
    print("파일 없음 %d개: %s" % (len(missing), missing[:3]))
for w in WANT:
    print("   %-6s %d개" % (w, sum(1 for o in out if '/%s/' % w.upper() in o)))
