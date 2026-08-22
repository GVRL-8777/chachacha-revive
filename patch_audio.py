# -*- coding: utf-8 -*-
"""AudioSource.Play() 널 안전화를 login 모드 전용 블록에서 꺼내 항상 적용되게 한다.

원본 오디오는 전부 CDN 전용이라 AudioSource 필드가 죄다 null 이다.
race 모드로 빌드하면 이 패치가 실행되지 않아 Player::GameStart 가
accel2Sound.Play() 에서 NRE 로 죽고 → 레이스가 시작되지 않는다(속도 0).
"""
import io

p = 'dbhook.cs'
s = io.open(p, encoding='utf-8').read()

start_mark = '            // 오디오는 전부 CDN 전용이라 AudioSource 필드가 죄다 null 이다.'
end_mark = '                Console.WriteLine("  AudioSource.Play() 널 안전화 {0}곳", playFixed);\n            }\n'

a = s.index(start_mark)
b = s.index(end_mark) + len(end_mark)
block = s[a:b]

# login 블록에서 제거
s = s[:a] + s[b:]

# 4칸 내어쓰기해서 mode 분기 앞에 넣는다
dedented = "\n".join(line[4:] if line.startswith('    ') else line
                     for line in block.split("\n"))

anchor = '        // ---- (2g) mode=login: 게스트 버튼을 정식 게임서버 로그인으로 돌린다 ----'
assert anchor in s
s = s.replace(anchor, dedented + "\n" + anchor, 1)

io.open(p, 'w', encoding='utf-8').write(s)
print('AudioSource.Play 널 안전화를 항상 적용되게 이동')
