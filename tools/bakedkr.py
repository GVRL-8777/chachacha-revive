# -*- coding: utf-8 -*-
"""프리팹에 **박혀 있는** 중국어 UILabel 을 한국어로 바꾼다.

문자열표(UILocalize)를 거치지 않고 프리팹 안에 원문이 그대로 들어 있는 라벨이
78개 있다. 표를 아무리 한글화해도 이들은 영영 중국어로 남는다.
`m_Text` 를 직접 갈아끼우고(길이가 달라지므로 자산을 재조립) 해결한다.

번역 원칙
  · 화면에 실제로 보이는 문구만 옮긴다.
  · `项目名称`(항목 이름), `1234 分` 처럼 런타임에 덮어써지는 자리표시자는
    그대로 두거나 한국어 자리표시자로만 바꾼다.
  · 결제 금액(`5元` 6개)은 서버가 상품 목록을 주지 않아 그대로 남는 자리라,
    한국 서비스 기준 금액대로 채워 넣는다(추정값).
"""
import io
import os
import glob
import struct
import sys
from collections import defaultdict

from sfparse import parse
from sfwrite import ALIGN
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile

CN = 'survey/5577.com.cjenm.chachachacn/assets/bin/Data'
OVERLAY = 'overlay'
TEXT_OFF = 72
APPLY = '--apply' in sys.argv

# 화면에 보이는 문구 (중국어 -> 한국어)
TEXT = {
    '加速度': '가속도',
    '最高时速': '최고속도',
    '耗油量': '연비',
    '设置': '설정',
    '一周排名': '주간순위',
    '全国排名': '전국순위',
    '上周排行': '지난주 순위',
    '读取中…': '불러오는 중…',
    '否': '아니오',
    '取消对决': '대결 취소',
    '对手': '상대',
    '高级汽油': '고급 휘발유',
    '购买汽车': '자동차 구매',
    '随机购买汽车': '자동차 뽑기',
    '折价换新': '보상 판매',
    '说明': '설명',
    '竞技模式': '경기 모드',
    '障碍赛模式': '장애물 모드',
    # 글자대로 옮겨 놓고 보니 앱이 죽었을 때 쓰는 말이라 화면과 안 맞았다.
    # 문자열표에 `PauseTitleLabel = 일시 정지` 가 이미 있다.
    # `tools/bakedtext.py` 가 '일시 정지'로 고쳐 준다.
    '意外终止': '비정상 종료',
    '重新购买': '다시 구매',
    '请稍等': '잠시만 기다려 주세요',
    '请求': '요청',
    '分': '점',
    '七天后初始化': '7일 후 초기화',
    '给你赠送了轮胎': '타이어를 보내왔습니다',
    '所有车型升级至 Sclass': '모든 차량 S클래스로 승급',
    '哪个国家': '국가',
    'G商城大奖': 'G마켓 그랑프리',
    '机会只有一次！': '기회는 한 번뿐입니다!',
    '只可以通过本窗口购买，不容错过哦！': '이 창에서만 구매할 수 있습니다. 놓치지 마세요!',
    '请不要关闭此窗口,否则失去重新挑战的机会.': '이 창을 닫으면 재도전 기회가 사라집니다.',
    '重新挑战将失去刚刚获得的奖励.': '재도전하면 방금 받은 보상은 사라집니다.',
    '重新挑战会随机发放奖励道具和金币.': '재도전 시 보상 아이템과 골드를 무작위로 드립니다.',
    '(金币,副油箱,无敌加速,高级汽油,加速燃料,前置雷达,油霸)':
        '(골드, 보조연료탱크, 무적가속, 고급 휘발유, 가속연료, 전방레이더, 연비왕)',
    '[FF4242]用折价[-]奖杯可再进행挑战.': '[FF4242]트로피[-]로 다시 도전할 수 있습니다.',
    '[FF4242]用折价[-]奖杯可再进行挑战.': '[FF4242]트로피[-]로 다시 도전할 수 있습니다.',
    '"这个成绩,满意吗?': '"이 성적, 만족하시나요?',
    '耗油量, 从1级升级为 2级': '연비, 1단계에서 2단계로 상승',
    '1名 : 5000     /  2名 : 3000     / 3名 : 1000':
        '1위 : 5000     /  2위 : 3000     / 3위 : 1000',
    # 친구 초대 보상 안내
    '1回': '1회', '5回': '5회', '15回': '15회', '30回': '30회', '50回': '50회',
    '轮胎 X5': '타이어 X5',
    '金币 X4000': '골드 X4000',
    '奖杯 X20': '트로피 X20',
    '合金 或者 奖杯 X50': '허미 또는 트로피 X50',
    '喵喵 或者 金币 X20000': '미아우 또는 골드 X20000',
    # 자리표시자(런타임에 덮어써짐) — 그래도 한국어로 둔다
    '项目名称': '항목 이름',
    '1234 分': '1234 점',
}

# 결제 금액 자리(상품 6종). 서버가 상품 목록을 주지 않아 이 값이 그대로 보인다.
# 한국 서비스 기준 금액대로 채운다(정확한 원본 표는 남아 있지 않아 추정).
PRICE_FILE = 'f0f04142d5931c242bcabff1858a37b5'
PRICES = {'0_Value_Label': '1,200원', '1_Value_Label': '2,990원',
          '2_Value_Label': '5,900원', '3_Value_Label': '11,000원',
          '4_Value_Label': '22,000원', '5_Value_Label': '55,000원'}


def script_names():
    sf = SerializedFile(EndianBinaryReader(
        io.open(os.path.join(CN, 'sharedassets0.assets'), 'rb').read()), None)
    out = {}
    for pid, o in sf.objects.items():
        if o.type.name != 'MonoScript':
            continue
        d = o.get_raw_data()
        n = struct.unpack_from('<i', d, 0)[0]
        if 0 < n < 200:
            try:
                out[pid] = d[4:4 + n].decode('utf-8')
            except UnicodeDecodeError:
                pass
    return out


def process(path, names, report):
    try:
        sf = SerializedFile(EndianBinaryReader(io.open(path, 'rb').read()), None)
    except Exception:
        return None
    gname = {}
    for q, o in sf.objects.items():
        if o.type.name == 'GameObject':
            try:
                gname[q] = o.read_typetree()['m_Name']
            except Exception:
                pass
    base = os.path.basename(path)
    patched = {}
    for q, o in sf.objects.items():
        if o.type.name != 'MonoBehaviour':
            continue
        d = o.get_raw_data()
        if len(d) < 80:
            continue
        if names.get(struct.unpack_from('<i', d, 16)[0]) != 'UILabel':
            continue
        n = struct.unpack_from('<i', d, TEXT_OFF)[0]
        if not (0 < n < 4000) or TEXT_OFF + 4 + n > len(d):
            continue
        try:
            txt = d[TEXT_OFF + 4:TEXT_OFF + 4 + n].decode('utf-8')
        except UnicodeDecodeError:
            continue
        go = gname.get(struct.unpack_from('<i', d, 4)[0], '')
        new = None
        if base == PRICE_FILE and go in PRICES:
            new = PRICES[go]
        elif txt in TEXT:
            new = TEXT[txt]
        if new is None or new == txt:
            continue
        nb = new.encode('utf-8')
        field = struct.pack('<i', len(nb)) + nb
        while len(field) % 4:
            field += b'\x00'
        tail = d[TEXT_OFF + 4 + ((n + 3) & ~3):]
        patched[q] = bytes(d[:TEXT_OFF]) + field + tail
        report.append((base, go, txt.replace('\n', ' ')[:24], new[:26]))
    return patched if patched else None


def rebuild(path, patched, out):
    meta = parse(path)
    raw = io.open(path, 'rb').read()
    off = meta['data_offset']
    data = bytearray()
    newobjs = []
    for ob in sorted(meta['objects'], key=lambda x: x['start']):
        while len(data) % 8:
            data.append(0)
        st = len(data)
        b = patched.get(ob['path_id']) or raw[off + ob['start']: off + ob['start'] + ob['size']]
        data += b
        newobjs.append(dict(ob, start=st, size=len(b)))
    m = meta['unity'].encode('utf-8') + b'\x00'
    m += struct.pack('<i', meta['platform'])
    m += struct.pack('<i', 0)
    m += struct.pack('<i', meta['big_id'])
    m += struct.pack('<i', len(newobjs))
    for ob in sorted(newobjs, key=lambda x: x['path_id']):
        m += struct.pack('<iIIiHh', ob['path_id'], ob['start'], ob['size'],
                         ob['type_id'], ob['class_id'], ob['destroyed'])
    m += struct.pack('<i', len(meta['externals']))
    for nm in meta['externals']:
        m += b'\x00' + b'\x00' * 16 + struct.pack('<i', 0) + nm.encode('utf-8') + b'\x00'
    m += b'\x00'
    do = max(meta['data_offset'], ALIGN(20 + len(m) + 64))
    head = struct.pack('>IIII', len(m), do + len(data), 9, do)
    head += bytes([1 if meta['endian'] == '>' else 0, 0, 0, 0])
    ob2 = bytearray(head + m)
    while len(ob2) < do:
        ob2 += b'\x00'
    ob2 += data
    io.open(out, 'wb').write(bytes(ob2))


def main():
    names = script_names()
    report = []
    files = [p for p in glob.glob(os.path.join(CN, '*'))
             if not os.path.isdir(p) and not p.endswith('.resS') and '.split' not in p]
    touched = 0
    for p in files:
        name = os.path.basename(p)
        src = os.path.join(OVERLAY, name)
        base = src if os.path.exists(src) else p
        patched = process(base, names, report)
        if not patched:
            continue
        if APPLY:
            rebuild(base, patched, os.path.join(OVERLAY, name))
        touched += 1
    print("바꾼 라벨 %d개 (자산 %d개)" % (len(report), touched))
    for r in report[:30]:
        print("  %-30s %-22s %-24s -> %s" % (r[0][:30], r[1][:22], r[2], r[3]))
    if not APPLY:
        print("\n(미적용: --apply 를 붙이면 실제로 씀)")


if __name__ == '__main__':
    main()
