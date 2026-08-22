# -*- coding: utf-8 -*-
"""chacnserver.py 에 NetQuery 패킷 자동 응답을 붙인다."""
import io

p = 'chacnserver.py'
s = io.open(p, encoding='utf-8').read()

anchor = '# 중국판 클라는 URL 패딩'
add = '''# NetQuery/NetRecive 계열 패킷 스키마 (netcn.py 가 IL 에서 추출)
NETQ = {}
_np = os.path.join(SP, "netcn.json")
if os.path.exists(_np):
    NETQ = json.load(open(_np, encoding="utf-8-sig"))


def _packet_default(key):
    """키 이름으로 기본값을 고른다. 클라의 GetString/GetInt/GetBoolean 과 맞춰야 한다."""
    k = key.lower()
    if k.startswith(("is", "can", "able", "enable", "use", "valid")) or k.endswith("flag"):
        return False
    if k.endswith(("url", "name", "message", "code", "date", "id", "class", "nick")):
        return ""
    return 0


def auto_packet(path):
    """NetQuery 응답을 스키마대로 만든다.

    빈 배열은 이 게임의 JSON 파서가 null 로 읽어 NRE 를 내므로 항목을 최소 1개 넣는다."""
    info = NETQ.get(path)
    if not info:
        return None
    body = {"success": True, "errorCode": None, "token": Session.token}
    keys = info["keys"]
    if info.get("container") and len(keys) > 1:
        body[keys[0]] = [dict((k, _packet_default(k)) for k in keys[1:])]
    else:
        for k in keys:
            body.setdefault(k, _packet_default(k))
    return body


'''
assert anchor in s
s = s.replace(anchor, add + anchor, 1)

# 디스패치: 전용 핸들러 -> HTTP_ 스키마 -> NetQuery 패킷 순
old = '''            fn = ROUTES.get(path)
            resp = fn(req) if fn else auto(path)'''
new = '''            fn = ROUTES.get(path)
            if fn:
                resp = fn(req)
            elif path in ROUTE_CLASS:
                resp = auto(path)
            else:
                resp = auto_packet(path) or auto(path)'''
assert old in s
s = s.replace(old, new, 1)

io.open(p, 'w', encoding='utf-8').write(s)
import ast
ast.parse(io.open(p, encoding='utf-8').read())
print('chacnserver.py 에 NetQuery 자동 응답 추가 (구문 OK)')
