# -*- coding: utf-8 -*-
"""ChangePlayerModel 절단 지점 바로 앞에 차량(body) 진단 로그를 심는다."""
import io

p = 'dbhook.cs'
s = io.open(p, encoding='utf-8').read()

old = '''                var cut = Instruction.Create(OpCodes.Ret);
                cip2.InsertAfter(mc, cut);
                Console.WriteLine("  ChangePlayerModel: {0} 대입 뒤에서 종료", cutAfter);'''

new = '''                var cut = Instruction.Create(OpCodes.Ret);
                cip2.InsertAfter(mc, cut);
                Console.WriteLine("  ChangePlayerModel: {0} 대입 뒤에서 종료", cutAfter);

                // 진단: 차량 모델(body)이 실제로 만들어졌는지 절단 직전에 찍는다.
                if (debugLog != null)
                {
                    var bodyFld = cpm2.DeclaringType.Fields.FirstOrDefault(f => f.Name == "body");
                    if (bodyFld != null)
                    {
                        bodyFld.Attributes = (bodyFld.Attributes & ~FieldAttributes.FieldAccessMask)
                                             | FieldAttributes.Public;
                        var uObjD = Def(unityEngine, "UnityEngine.Object");
                        var goD = Def(unityEngine, "UnityEngine.GameObject");
                        var trD = Def(unityEngine, "UnityEngine.Transform");
                        var rendD = Def(unityEngine, "UnityEngine.Renderer");
                        var strD = Def(mscorlib, "System.String");
                        var nameM = Import(uObjD.Methods.First(m => m.Name == "get_name"));
                        var transM = Import(goD.Methods.First(m => m.Name == "get_transform"));
                        var posM = Import(trD.Methods.First(m => m.Name == "get_position"));
                        var cicM = Import(goD.Methods.First(
                            m => m.Name == "GetComponentsInChildren" && m.Parameters.Count == 1
                                 && m.Parameters[0].ParameterType.FullName == "System.Type"));
                        var ccss = Import(strD.Methods.First(m => m.Name == "Concat"
                            && m.Parameters.Count == 2
                            && m.Parameters[0].ParameterType.FullName == "System.String"
                            && m.Parameters[1].ParameterType.FullName == "System.String"));
                        var ccoo = Import(strD.Methods.First(m => m.Name == "Concat"
                            && m.Parameters.Count == 2
                            && m.Parameters[0].ParameterType.FullName == "System.Object"
                            && m.Parameters[1].ParameterType.FullName == "System.Object"));
                        var v3D = mod.ImportReference(Def(unityEngine, "UnityEngine.Vector3"));
                        var i32D = mod.ImportReference(Def(mscorlib, "System.Int32"));

                        var logNull = Instruction.Create(OpCodes.Ldstr, "[CHACAR] body=null");
                        Action<Instruction> put = x => cip2.InsertBefore(cut, x);
                        put(Instruction.Create(OpCodes.Ldarg_0));
                        put(Instruction.Create(OpCodes.Ldfld, bodyFld));
                        put(Instruction.Create(OpCodes.Brfalse, logNull));
                        put(Instruction.Create(OpCodes.Ldstr, "[CHACAR] "));
                        put(Instruction.Create(OpCodes.Ldarg_0));
                        put(Instruction.Create(OpCodes.Ldfld, bodyFld));
                        put(Instruction.Create(OpCodes.Callvirt, nameM));
                        put(Instruction.Create(OpCodes.Call, ccss));
                        put(Instruction.Create(OpCodes.Ldarg_0));
                        put(Instruction.Create(OpCodes.Ldfld, bodyFld));
                        put(Instruction.Create(OpCodes.Callvirt, transM));
                        put(Instruction.Create(OpCodes.Callvirt, posM));
                        put(Instruction.Create(OpCodes.Box, v3D));
                        put(Instruction.Create(OpCodes.Call, ccoo));
                        put(Instruction.Create(OpCodes.Ldstr, " 렌더러="));
                        put(Instruction.Create(OpCodes.Call, ccss));
                        put(Instruction.Create(OpCodes.Ldarg_0));
                        put(Instruction.Create(OpCodes.Ldfld, bodyFld));
                        put(Instruction.Create(OpCodes.Ldtoken, mod.ImportReference(rendD)));
                        put(Instruction.Create(OpCodes.Call, getTypeFromHandle));
                        put(Instruction.Create(OpCodes.Callvirt, cicM));
                        put(Instruction.Create(OpCodes.Ldlen));
                        put(Instruction.Create(OpCodes.Conv_I4));
                        put(Instruction.Create(OpCodes.Box, i32D));
                        put(Instruction.Create(OpCodes.Call, ccoo));
                        put(Instruction.Create(OpCodes.Call, debugLog));
                        put(Instruction.Create(OpCodes.Br, cut));
                        put(logNull);
                        put(Instruction.Create(OpCodes.Call, debugLog));
                        Console.WriteLine("  ChangePlayerModel 절단 직전에 차량 진단 로그 삽입");
                    }
                }'''

assert old in s
s = s.replace(old, new, 1)
io.open(p, 'w', encoding='utf-8').write(s)
print('dbhook.cs 차량 진단 패치 완료')
