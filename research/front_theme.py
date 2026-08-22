# -*- coding: utf-8 -*-
"""추가한 테마를 배열 맨 앞(index 0)에 놓아 첫 구간부터 보이게 한다.

기존 테마는 하나도 빠지지 않고 뒤로 밀릴 뿐이다(= 여전히 '추가').
CreateMap 이 mapThemeOrder[selectMapTheme(=0)] 로 시작하므로 index 0 이 첫 구간이다.
"""
import io

p = 'patchcn.cs'
s = io.open(p, encoding='utf-8').read()

# 복사 루프: new[i] = old[i]  ->  new[i+1] = old[i]
old = """                ap2.Append(Instruction.Create(OpCodes.Ldloc, vNew));
                ap2.Append(Instruction.Create(OpCodes.Ldloc, vI));
                ap2.Append(Instruction.Create(OpCodes.Ldloc, vOld));
                ap2.Append(Instruction.Create(OpCodes.Ldloc, vI));
                ap2.Append(Instruction.Create(OpCodes.Ldelem_Ref));
                ap2.Append(Instruction.Create(OpCodes.Stelem_Ref));"""
new = """                ap2.Append(Instruction.Create(OpCodes.Ldloc, vNew));
                ap2.Append(Instruction.Create(OpCodes.Ldloc, vI));
                ap2.Append(Instruction.Create(OpCodes.Ldc_I4_1));
                ap2.Append(Instruction.Create(OpCodes.Add));          // new[i+1] = old[i]
                ap2.Append(Instruction.Create(OpCodes.Ldloc, vOld));
                ap2.Append(Instruction.Create(OpCodes.Ldloc, vI));
                ap2.Append(Instruction.Create(OpCodes.Ldelem_Ref));
                ap2.Append(Instruction.Create(OpCodes.Stelem_Ref));"""
assert old in s
s = s.replace(old, new, 1)

# 새 테마를 index vN 이 아니라 0 에 넣는다
old2 = """                ap2.Append(Instruction.Create(OpCodes.Ldloc, vNew));
                ap2.Append(Instruction.Create(OpCodes.Ldloc, vN));
                ap2.Append(Instruction.Create(OpCodes.Newobj, mtdCtor));"""
new2 = """                ap2.Append(Instruction.Create(OpCodes.Ldloc, vNew));
                ap2.Append(Instruction.Create(OpCodes.Ldc_I4_0));     // 맨 앞에 넣는다
                ap2.Append(Instruction.Create(OpCodes.Newobj, mtdCtor));"""
assert old2 in s
s = s.replace(old2, new2, 1)

io.open(p, 'w', encoding='utf-8').write(s)
print('추가 테마를 index 0 으로')
