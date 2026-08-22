# -*- coding: utf-8 -*-
"""훅이 gbeach01 뿐 아니라 gbeach02 도 같은 자산으로 돌려주게 한다.

중국판 테마는 조각을 정확히 2개(01, 02)씩 쓴다. 하나만 주면 슬롯 하나가
비어서 차 앞 100유닛 구간이 통째로 사라진다.
"""
import io

p = 'patchcn.cs'
s = io.open(p, encoding='utf-8').read()

old_const = '        const string HOOK_PATH = "Background/gbeach01";'
assert old_const in s
s = s.replace(old_const, old_const + '\n'
              '        const string HOOK_PATH2 = "Background/gbeach02";', 1)

old = '''                hp.Append(Instruction.Create(OpCodes.Ldarg_0));
                hp.Append(Instruction.Create(OpCodes.Ldstr, HOOK_PATH));
                hp.Append(Instruction.Create(OpCodes.Call, strEq));
                hp.Append(Instruction.Create(OpCodes.Brfalse, nul));
                hp.Append(Instruction.Create(OpCodes.Ldsfld, fBundle));'''
new = '''                var load = Instruction.Create(OpCodes.Ldsfld, fBundle);
                hp.Append(Instruction.Create(OpCodes.Ldarg_0));
                hp.Append(Instruction.Create(OpCodes.Ldstr, HOOK_PATH));
                hp.Append(Instruction.Create(OpCodes.Call, strEq));
                hp.Append(Instruction.Create(OpCodes.Brtrue, load));
                hp.Append(Instruction.Create(OpCodes.Ldarg_0));
                hp.Append(Instruction.Create(OpCodes.Ldstr, HOOK_PATH2));
                hp.Append(Instruction.Create(OpCodes.Call, strEq));
                hp.Append(Instruction.Create(OpCodes.Brfalse, nul));
                hp.Append(load);'''
assert old in s
s = s.replace(old, new, 1)
io.open(p, 'w', encoding='utf-8').write(s)
print('훅 확장 완료: gbeach01 + gbeach02')
