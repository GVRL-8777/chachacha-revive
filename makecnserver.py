# -*- coding: utf-8 -*-
"""cha8server.py 를 바탕으로 중국판 전용 서버 chacnserver.py 를 만든다."""
import io

s = io.open('cha8server.py', encoding='utf-8').read()

# 1) 머리말/스키마 파일 교체
s = s.replace('다함께 차차차 v1.3.1 (8.apk) 전용 사설 서버.',
              '一起车车车 (중국판 5577.com.cjenm.chachachacn) 전용 사설 서버.')
s = s.replace('사용법: python cha8server.py [포트]', '사용법: python chacnserver.py [포트]')
s = s.replace('_p = os.path.join(SP, "api8.json")', '_p = os.path.join(SP, "apicn.json")')
s = s.replace('LOG = os.path.join(SP, "server8.log")', 'LOG = os.path.join(SP, "servercn.log")')
s = s.replace('=== 차차차 v1.3.1 서버 :%d', '=== 중국판 차차차 서버 :%d')

# 2) 경로 -> 응답 클래스 표를 중국판 것으로 교체
a = s.index('# 경로 -> 응답 클래스\nROUTE_CLASS = {')
b = s.index('}\n', s.index('"/event/review/complete"')) + 2
new_table = '''# 경로 -> 응답 클래스 (중국판은 86개 경로를 쓴다. 로그인/로비 임계 경로만 명시하고
# 나머지는 스키마 기반 자동 응답으로 처리한다)
ROUTE_CLASS = {
    "/service/inspection/check": "HTTP_CheckService",
    "/service/notice/get": "HTTP_CheckNotice",
    "/user/auth/login": "HTTP_Login",
    "/user/auth/logout": "HTTP_Logout",
    "/user/auth/withdrawal": "HTTP_WithDrawal",
    "/user/auth/cancelwithdrawal": "HTTP_CancelWithDrawal",
    "/user/info/get": "HTTP_UserInfo",
    "/user/info/update": "HTTP_UpdateUserInfo",
    "/user/tire/check": "HTTP_CheckTire",
    "/user/car/list": "HTTP_GetCarList",
    "/user/car/select": "HTTP_SelectCar",
    "/user/car/upgrade": "HTTP_UpgradeCar",
    "/user/car/tune": "HTTP_TuneCar",
    "/user/car/compensate": "HTTP_TradeBuyValueList",
    "/user/character/list": "HTTP_GetCharacterList",
    "/user/character/select": "HTTP_SelectCharacter",
    "/user/boast/set": "HTTP_BoastAble",
    "/shop/item/list": "HTTP_GetItemList",
    "/shop/item/buy": "HTTP_BuyItem",
    "/shop/car/buy": "HTTP_BuyCar",
    "/shop/car/unlock": "HTTP_UnlockClass",
    "/shop/car/unlockbuy": "HTTP_UnlockBuy",
    "/shop/car/compensate": "HTTP_TradeBuy",
    "/shop/character/buy": "HTTP_BuyCharacter",
    "/shop/gold/exchange": "HTTP_ExchangeGold",
    "/shop/tire/exchange": "HTTP_ExchangeTire",
    "/play/game/start": "HTTP_GameStart",
    "/play/game/finish": "HTTP_GameFinish",
    "/play/item/use": "HTTP_UseItem",
    "/play/item/buyuse": "HTTP_BuyUseItem",
    "/ranking/current/list": "HTTP_GetRank",
    "/ranking/previous/list": "HTTP_GetRank",
    "/ranking/previous/reward": "HTTP_GetPrevRankReward",
    "/tire/present/list": "HTTP_GetGiftList",
    "/tire/present/recv": "HTTP_RecvGiftTire",
    "/tire/present/recvAll": "HTTP_RecvAllGiftTire",
    "/tire/present/send": "HTTP_SendGiftTire",
    "/invitation/list": "HTTP_InviteList",
    "/invitation/invite": "HTTP_Invite",
    "/setting/present/allow": "HTTP_AbleGiftSetting",
    "/event/review/complete": "HTTP_Event",
    "/grandprix/info/get": "HTTP_GrandPrixInfo",
}

# 중국판 클라는 URL 패딩(`/xxxx/`) 때문에 경로 앞에 잉여 세그먼트가 붙는다.
# 알려진 최상위 접두사가 나오는 지점부터 잘라 쓴다.
KNOWN_ROOTS = ("/user/", "/play/", "/service/", "/shop/", "/ranking/", "/skill/",
               "/setting/", "/event/", "/ladder/", "/tire/", "/invitation/",
               "/grandprix/", "/versus/", "/gotya/")


def normalize(path):
    for r in KNOWN_ROOTS:
        i = path.find(r)
        if i > 0:
            return path[i:]
    return path

'''
s = s[:a] + new_table + s[b:]

# 3) 요청 처리에서 경로 정규화
s = s.replace('            path = target.split("?")[0].rstrip("/") or "/"',
              '            path = normalize(target.split("?")[0]).rstrip("/") or "/"')

io.open('chacnserver.py', 'w', encoding='utf-8').write(s)
import ast
ast.parse(io.open('chacnserver.py', encoding='utf-8').read())
print('chacnserver.py 생성 (구문 OK)')
