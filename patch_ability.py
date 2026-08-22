# -*- coding: utf-8 -*-
"""PlayerAbility::Init 을 try/catch 로 감싼다.

_Build 안에서 IndexOutOfRangeException(length < 0) 이 터지는데(난독화된 원본 코드의 결함,
안정 빌드에서도 동일하게 발생), 그 예외가 호출자인 Player::Init 까지 타고 올라가
**ChangePlayerModel 이 아예 실행되지 않아 차량이 생성되지 않는다**.
본문이 3개 명령뿐이라 통째로 다시 쓰는 게 가장 안전하다.
"""
import io

p = 'dbhook.cs'
s = io.open(p, encoding='utf-8').read()

anchor = '        // ---- Cutin::PlayVoice 비우기 ----'
add = '''        // ---- PlayerAbility::Init 을 try/catch 로 감싸기 ----
        // _Build 가 IndexOutOfRangeException(length < 0) 을 내는데(원본 결함, 안정 빌드도 동일),
        // 그게 Player::Init 까지 전파돼 **ChangePlayerModel 이 실행되지 않아 차량이 안 생긴다**.
        // 예외를 여기서 삼키면 Player::Init 이 끝까지 진행된다.
        {
            var pa = mod.GetType("PlayerAbility");
            var paInit = pa == null ? null : pa.Methods.FirstOrDefault(m => m.Name == "Init");
            var paBuild = pa == null ? null : pa.Methods.FirstOrDefault(m => m.Name == "_Build");
            if (paInit != null && paBuild != null && paInit.HasBody)
            {
                var ab = paInit.Body;
                ab.Instructions.Clear(); ab.Variables.Clear(); ab.ExceptionHandlers.Clear();
                var ap = ab.GetILProcessor();
                var tryStart = Instruction.Create(OpCodes.Ldarg_0);
                var callBuild = Instruction.Create(OpCodes.Call, paBuild);
                var endRet = Instruction.Create(OpCodes.Ret);
                var leaveTry = Instruction.Create(OpCodes.Leave, endRet);
                var handlerStart = Instruction.Create(OpCodes.Pop);
                var leaveHandler = Instruction.Create(OpCodes.Leave, endRet);
                ap.Append(tryStart);
                ap.Append(callBuild);
                ap.Append(leaveTry);
                ap.Append(handlerStart);
                ap.Append(leaveHandler);
                ap.Append(endRet);
                ab.ExceptionHandlers.Add(new ExceptionHandler(ExceptionHandlerType.Catch)
                {
                    TryStart = tryStart,
                    TryEnd = handlerStart,
                    HandlerStart = handlerStart,
                    HandlerEnd = endRet,
                    CatchType = mod.ImportReference(Def(mscorlib, "System.Exception")),
                });
                Console.WriteLine("  PlayerAbility::Init 을 try/catch 로 감쌈 (Player::Init 중단 방지)");
            }
        }

'''

assert anchor in s
s = s.replace(anchor, add + anchor, 1)
io.open(p, 'w', encoding='utf-8').write(s)
print('dbhook.cs PlayerAbility 패치 완료')
