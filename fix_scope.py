# -*- coding: utf-8 -*-
"""맵 배선 블록을 번들 블록 안으로 옮긴다 (fBundle 등 지역 변수를 쓰기 위해)."""
import io

p = 'patchcn.cs'
s = io.open(p, encoding='utf-8').read()

start = s.index('        // ---- 새 맵 테마 추가 배선 ----')
end = s.index('        // 360/NetmarbleS 플러그인은 이 환경에 존재하지 않는다.')
block = s[start:end]
s = s[:start] + s[end:]

# 번들 블록의 끝(Update 삽입 로그 다음 줄의 닫는 중괄호) 앞에 끼워 넣는다
marker = '            Console.WriteLine("  Generic_Title::Update -> __ChaBundleTick (번들 다운로드/로드 검증)");\n'
assert marker in s
# 블록 안쪽이므로 들여쓰기를 4칸 더 준다
inner = "\n".join(('    ' + ln) if ln.strip() else ln for ln in block.split("\n"))
s = s.replace(marker, marker + inner, 1)

io.open(p, 'w', encoding='utf-8').write(s)
print('맵 배선 블록을 번들 블록 안으로 이동')
