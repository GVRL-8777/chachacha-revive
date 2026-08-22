# -*- coding: utf-8 -*-
"""차량 DB(JSON TextAsset)에 helly(변신 로봇)를 추가하고 다시 자산으로 만든다.

중국판의 차량 표는 `Editor_/DataBase/CarDataBase` TextAsset(JSON)이다.
클라이언트는 서버가 준 carNo 를 CarIndex 로 찾으므로(-1 보정),
비어 있는 인덱스 하나를 쓰면 서버 쪽 수정 없이도 목록에 들어간다.
IsRobot=true 로 두면 CarDataLinker 가 로봇 애니메이션 경로를 로드한다.

파일 크기가 바뀌므로 TextAsset 을 새로 직렬화해 overlay 로 얹는다.
"""
import io, json, os, struct, sys
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile
from sfparse import parse
from sfwrite import ALIGN

D = 'survey/5577.com.cjenm.chachachacn/assets/bin/Data'
SRC = [f for f in os.listdir(D) if f.startswith('ade64ecd')][0]
OUT = os.path.join('overlay', SRC)

meta = parse(os.path.join(D, SRC))
raw = io.open(os.path.join(D, SRC), 'rb').read()
sf = SerializedFile(EndianBinaryReader(raw), None)
o = list(sf.objects.values())[0]
tree = o.read_typetree()
txt = tree['m_Script']
if isinstance(txt, (bytes, bytearray)):
    txt = txt.decode('utf-8')
db = json.loads(txt)
arr = db['CarDataBase']['CarInfoDB']['CarDataArray']

if any(c['CarName'].lower() == 'helly' for c in arr):
    print('이미 들어 있다')
else:
    gtr = [c for c in arr if c['CarName'] == 'GTR'][0]
    used = set(c['CarIndex'] for c in arr)
    idx = next(i for i in range(0, 60) if i not in used)     # 빈 인덱스(17)
    helly = json.loads(json.dumps(gtr))                       # 깊은 복사
    helly.update({
        'CarName': 'helly', 'CarIndex': idx,
        'StartCarClassType': 'A',        # 프리팹이 A/S/R 세 등급만 있다
        'CostGold': 0, 'UnlockTrophy': 0,
        'Preminum': True, 'NewCar': True, 'EventCar': False, 'RivalCar': False,
        'IsRobot': True,                 # 로봇 변신
        'HasMission': False, 'MissionType': 'none',
    })
    arr.append(helly)
    print('helly 추가: CarIndex=%d (서버 carNo=%d)' % (idx, idx + 1))

new_txt = json.dumps(db, ensure_ascii=False, separators=(',', ':'))
tree['m_Script'] = new_txt
blob = bytes(o.save_typetree(tree))
print('JSON %d -> %d 바이트' % (len(txt), len(new_txt)))

objs = [{'path_id': o.path_id, 'start': 0, 'size': len(blob),
         'type_id': int(o.class_id), 'class_id': int(o.class_id), 'destroyed': 0}]
m = meta['unity'].encode('utf-8') + b'\x00'
m += struct.pack('<i', meta['platform'])
m += struct.pack('<i', 0)
m += struct.pack('<i', meta['big_id'])
m += struct.pack('<i', len(objs))
for ob in objs:
    m += struct.pack('<iIIiHh', ob['path_id'], ob['start'], ob['size'],
                     ob['type_id'], ob['class_id'], ob['destroyed'])
m += struct.pack('<i', len(meta['externals']))
for name in meta['externals']:
    m += b'\x00' + b'\x00' * 16 + struct.pack('<i', 0) + name.encode('utf-8') + b'\x00'
m += b'\x00'
data_offset = max(meta['data_offset'], ALIGN(20 + len(m) + 64))
head = struct.pack('>IIII', len(m), data_offset + len(blob), 9, data_offset)
head += bytes([1 if meta['endian'] == '>' else 0, 0, 0, 0])
out = bytearray(head + m)
while len(out) < data_offset:
    out += b'\x00'
out += blob
io.open(OUT, 'wb').write(bytes(out))
print('출력: %s (%d B, 원본 %d B)' % (OUT, len(out), len(raw)))
