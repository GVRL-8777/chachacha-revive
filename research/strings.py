# 이진 파일에서 아스키 문자열을 뽑는다(중복 제거).
import sys, re
b=open(sys.argv[1],'rb').read()
n=int(sys.argv[2]) if len(sys.argv)>2 else 6
pat=sys.argv[3] if len(sys.argv)>3 else None
rx=re.compile(rb'[\x20-\x7e]{%d,}'%n)
out=[]
for m in rx.finditer(b):
    s=m.group().decode('ascii')
    if pat is None or re.search(pat, s, re.I):
        out.append(s)
seen=set(); res=[]
for s in out:
    if s not in seen:
        seen.add(s); res.append(s)
print(len(res), "unique strings")
for s in res: print(s)
