# -*- coding: utf-8 -*-
"""patchcn.cs 를 테마 1종 -> N종 이식용으로 일반화한다.

  1) NEW_THEME(문자열) -> NEW_THEMES(문자열 배열)
  2) 새 배열 크기를 old.Length + N 으로
  3) 새 테마 채우기를 N개 만큼 펼쳐서 생성(개수가 컴파일 타임 상수라 루프가 필요 없다)
  4) __ChaMapHook 을 "Background/*" 전부를 번들에서 찾아보는 범용 훅으로 교체
     (번들에 없으면 null 을 돌려주고 원래 경로로 흘러간다)
"""
import io

p = 'patchcn.cs'
s = io.open(p, encoding='utf-8').read()

# 1) 상수
old = '        const string NEW_THEME = "gbeach";'
new = ('        // 중국판에 없는 테마. 전부 gogogoracer 1.4.3 에서 가져왔다.\n'
       '        static readonly string[] NEW_THEMES = {\n'
       '            "gbeach", "gbridge", "gcity", "gcliff",\n'
       '            "bbeach", "bbridge", "bcity", "bfield", "bsand",\n'
       '        };')
assert old in s, '상수'
s = s.replace(old, new, 1)

# 2) 배열 크기
old = """                ap2.Append(Instruction.Create(OpCodes.Stloc, vN));
                ap2.Append(Instruction.Create(OpCodes.Ldloc, vN));
                ap2.Append(Instruction.Create(OpCodes.Ldc_I4_1));
                ap2.Append(Instruction.Create(OpCodes.Add));
                ap2.Append(Instruction.Create(OpCodes.Newarr, (TypeReference)mtd));"""
new = """                ap2.Append(Instruction.Create(OpCodes.Stloc, vN));
                ap2.Append(Instruction.Create(OpCodes.Ldloc, vN));
                ap2.Append(Instruction.Create(OpCodes.Ldc_I4, NEW_THEMES.Length));
                ap2.Append(Instruction.Create(OpCodes.Add));
                ap2.Append(Instruction.Create(OpCodes.Newarr, (TypeReference)mtd));"""
assert old in s, '배열 크기'
s = s.replace(old, new, 1)

# 3) 새 테마 채우기
i = s.index('                // 새 테마 채우기')
j = s.index('                ap2.Append(Instruction.Create(OpCodes.Ldarg_0));\n'
            '                ap2.Append(Instruction.Create(OpCodes.Ldloc, vNew));\n'
            '                ap2.Append(Instruction.Create(OpCodes.Stfld, fOrder));', i)
fill = '''                // 새 테마들을 배열 맨 뒤에 '추가' (개수가 상수라 펼쳐서 생성한다)
                for (int ti = 0; ti < NEW_THEMES.Length; ti++)
                {
                    ap2.Append(Instruction.Create(OpCodes.Ldloc, vNew));
                    ap2.Append(Instruction.Create(OpCodes.Ldloc, vN));
                    ap2.Append(Instruction.Create(OpCodes.Ldc_I4, ti));
                    ap2.Append(Instruction.Create(OpCodes.Add));
                    ap2.Append(Instruction.Create(OpCodes.Newobj, mtdCtor));
                    ap2.Append(Instruction.Create(OpCodes.Dup));
                    ap2.Append(Instruction.Create(OpCodes.Ldstr, NEW_THEMES[ti]));
                    ap2.Append(Instruction.Create(OpCodes.Stfld, fTheme));
                    ap2.Append(Instruction.Create(OpCodes.Dup));
                    ap2.Append(Instruction.Create(OpCodes.Ldc_I4_3));
                    ap2.Append(Instruction.Create(OpCodes.Stfld, fLoop));
                    ap2.Append(Instruction.Create(OpCodes.Dup));
                    ap2.Append(Instruction.Create(OpCodes.Newobj, alCtor));
                    ap2.Append(Instruction.Create(OpCodes.Stfld, fRes));
                    ap2.Append(Instruction.Create(OpCodes.Stelem_Ref));
                }
'''
s = s[:i] + fill + s[j:]

# 로그 문구
old = '                ap2.Append(Instruction.Create(OpCodes.Ldstr, "[CNMAP] 테마 추가: " + NEW_THEME));'
new = ('                ap2.Append(Instruction.Create(OpCodes.Ldstr,\n'
       '                    "[CNMAP] 테마 " + NEW_THEMES.Length + "종 추가: "\n'
       '                    + string.Join(", ", NEW_THEMES)));')
assert old in s, '로그'
s = s.replace(old, new, 1)

io.open(p, 'w', encoding='utf-8').write(s)
print('테마 N종 일반화 완료 (%d종)' % 9)
