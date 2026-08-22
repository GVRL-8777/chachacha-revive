# -*- coding: utf-8 -*-
"""chacnserver.py 의 차량 목록을 '전 차량 보유' 로 바꾼다.

CRSystem.carName 이 "AVEO" 인데 CarInfoManager.GetCarDataByName 이 null 을 돌려줘
로비 차량 표시가 죽는다. 어떤 carNo 가 AVEO 인지 모르므로 1..N 을 전부 보유로 준다.
덤으로 차고에 중국판 차량 29종이 다 들어온다.
"""
import io

p = 'chacnserver.py'
s = io.open(p, encoding='utf-8').read()

start = s.index('def ep_carlist(req):')
end = s.index('def ep_charlist(req):')
new = '''def ep_carlist(req):
    """보유 차량 목록. 전 차량(1..CAR_MAX)을 보유로 돌려준다."""
    b = auto("/user/car/list")
    keys, types, ci = _container("HTTP_GetCarList")
    if ci is not None:
        cars = []
        for no in range(1, CAR_MAX + 1):
            c = dict((m, default_of(types.get(m, "int"))) for m in keys[ci + 1:])
            if "carNo" in c:
                c["carNo"] = no
            if "carSeq" in c:
                c["carSeq"] = no
            if "carClass" in c:
                c["carClass"] = "C"
            if "isSelected" in c:
                c["isSelected"] = (no == PLAYER["carNo"])
            for k in ("carAccel", "carSpeed", "carFuleCost", "carLevel", "level"):
                if k in c:
                    c[k] = 1
            cars.append(c)
        b[keys[ci]] = cars
    return b


def ep_caropenspec(req):
    """서비스가 열어 둔 차량 목록. 역시 전부 열어 둔다."""
    b = auto_packet("/service/resource/carlist") or {"success": True, "errorCode": None}
    b["cars"] = [{"carNo": n} for n in range(1, CAR_MAX + 1)]
    return b


'''
s = s[:start] + new + s[end:]

# CAR_MAX 상수
s = s.replace('PLAYER = {', 'CAR_MAX = 45          # 중국판은 차량 41종. 넉넉히 잡는다\n\nPLAYER = {', 1)

# 라우팅 등록
s = s.replace('    "/user/car/list": ep_carlist,',
              '    "/user/car/list": ep_carlist,\n    "/service/resource/carlist": ep_caropenspec,', 1)

io.open(p, 'w', encoding='utf-8').write(s)
import ast
ast.parse(io.open(p, encoding='utf-8').read())
print('전 차량 보유로 변경 (구문 OK)')
