# -*- coding: utf-8 -*-
"""tunnelfix.cs 의 4번 패치를 '번들 이름표' 방식으로 갈아 끼운다.

AssetBundle.Load(경로) 가 이 판본에서 우리 매니페스트를 못 읽는다.
대신 LoadAll 로 한 번 다 꺼내 이름표를 만들어 두고 거기서 찾는다.
컨테이너 항목 구조에 기대지 않으므로 판본 차이를 타지 않는다.
"""
import io

BLOCK = r'''        // --- 4) 번들 자산을 이름표로 찾기 -----------------------------------
        // AssetBundle.Load(경로) 가 이 판본에서는 우리 매니페스트를 못 읽는다.
        // 대신 LoadAll 로 한 번 다 꺼내 이름표를 만들어 두고 그 표에서 찾는다.
        var corlib = res.Resolve(mod.AssemblyReferences.First(x => x.Name == "mscorlib")).MainModule;
        var htType = corlib.GetType("System.Collections.Hashtable");
        var htRef = mod.ImportReference(htType);
        var htCtor = mod.ImportReference(htType.Methods.First(m => m.IsConstructor && m.Parameters.Count == 0));
        var htSet = mod.ImportReference(htType.Methods.First(m => m.Name == "set_Item"));
        var htGet = mod.ImportReference(htType.Methods.First(m => m.Name == "get_Item"));
        var strType = corlib.GetType("System.String");
        var toLower = mod.ImportReference(strType.Methods.First(
            m => m.Name == "ToLower" && m.Parameters.Count == 0));
        var lastIdx = mod.ImportReference(strType.Methods.First(
            m => m.Name == "LastIndexOf" && m.Parameters.Count == 1
                 && m.Parameters[0].ParameterType.Name == "Char"));
        var substr = mod.ImportReference(strType.Methods.First(
            m => m.Name == "Substring" && m.Parameters.Count == 1));
        var concat2 = mod.ImportReference(strType.Methods.First(
            m => m.Name == "Concat" && m.Parameters.Count == 2
                 && m.Parameters[0].ParameterType.Name == "String"
                 && m.Parameters[1].ParameterType.Name == "String"));
        var concatOO = mod.ImportReference(strType.Methods.First(
            m => m.Name == "Concat" && m.Parameters.Count == 2
                 && m.Parameters[0].ParameterType.Name == "Object"));
        var typeFromHandle = mod.ImportReference(corlib.GetType("System.Type")
            .Methods.First(m => m.Name == "GetTypeFromHandle"));
        var uoT = ue.GetType("UnityEngine.Object");
        var uoRef = mod.ImportReference(uoT);
        var getName = mod.ImportReference(uoT.Methods.First(m => m.Name == "get_name"));
        var resources = mod.ImportReference(ue.GetType("UnityEngine.Resources")
            .Methods.First(m => m.Name == "Load" && m.Parameters.Count == 1));
        var abT = ue.GetType("UnityEngine.AssetBundle");
        var abLoadAll = mod.ImportReference(abT.Methods.First(
            m => m.Name == "LoadAll" && m.Parameters.Count == 1));
        var bundleFld = title.Fields.First(f => f.Name == "__cnBundle");

        var mapFld = new FieldDefinition("__cnMap",
            FieldAttributes.Public | FieldAttributes.Static, htRef);
        title.Fields.Add(mapFld);

        var pick = new MethodDefinition("__ChaFromBundle",
            MethodAttributes.Public | MethodAttributes.Static, uoRef);
        pick.Parameters.Add(new ParameterDefinition("n", ParameterAttributes.None,
                                                    mod.TypeSystem.String));
        title.Methods.Add(pick);
        var pbody = pick.Body;
        var vAll = new VariableDefinition(new ArrayType(uoRef));
        var vI = new VariableDefinition(mod.TypeSystem.Int32);
        var vHit = new VariableDefinition(mod.TypeSystem.Object);
        pbody.Variables.Add(vAll); pbody.Variables.Add(vI); pbody.Variables.Add(vHit);
        pbody.InitLocals = true;
        var pp = pbody.GetILProcessor();
        var pNull = Instruction.Create(OpCodes.Ldnull);
        var pHave = Instruction.Create(OpCodes.Nop);

        pp.Append(Instruction.Create(OpCodes.Ldsfld, bundleFld));
        pp.Append(Instruction.Create(OpCodes.Brfalse, pNull));
        pp.Append(Instruction.Create(OpCodes.Ldsfld, mapFld));
        pp.Append(Instruction.Create(OpCodes.Brtrue, pHave));
        pp.Append(Instruction.Create(OpCodes.Newobj, htCtor));
        pp.Append(Instruction.Create(OpCodes.Stsfld, mapFld));
        pp.Append(Instruction.Create(OpCodes.Ldsfld, bundleFld));
        pp.Append(Instruction.Create(OpCodes.Ldtoken, uoRef));
        pp.Append(Instruction.Create(OpCodes.Call, typeFromHandle));
        pp.Append(Instruction.Create(OpCodes.Callvirt, abLoadAll));
        pp.Append(Instruction.Create(OpCodes.Stloc, vAll));
        pp.Append(Instruction.Create(OpCodes.Ldc_I4_0));
        pp.Append(Instruction.Create(OpCodes.Stloc, vI));
        var lTest = Instruction.Create(OpCodes.Ldloc, vI);
        var lBody = Instruction.Create(OpCodes.Ldsfld, mapFld);
        pp.Append(Instruction.Create(OpCodes.Br, lTest));
        pp.Append(lBody);
        pp.Append(Instruction.Create(OpCodes.Ldloc, vAll));
        pp.Append(Instruction.Create(OpCodes.Ldloc, vI));
        pp.Append(Instruction.Create(OpCodes.Ldelem_Ref));
        pp.Append(Instruction.Create(OpCodes.Callvirt, getName));
        pp.Append(Instruction.Create(OpCodes.Callvirt, toLower));
        pp.Append(Instruction.Create(OpCodes.Ldloc, vAll));
        pp.Append(Instruction.Create(OpCodes.Ldloc, vI));
        pp.Append(Instruction.Create(OpCodes.Ldelem_Ref));
        pp.Append(Instruction.Create(OpCodes.Callvirt, htSet));
        pp.Append(Instruction.Create(OpCodes.Ldloc, vI));
        pp.Append(Instruction.Create(OpCodes.Ldc_I4_1));
        pp.Append(Instruction.Create(OpCodes.Add));
        pp.Append(Instruction.Create(OpCodes.Stloc, vI));
        pp.Append(lTest);
        pp.Append(Instruction.Create(OpCodes.Ldloc, vAll));
        pp.Append(Instruction.Create(OpCodes.Ldlen));
        pp.Append(Instruction.Create(OpCodes.Conv_I4));
        pp.Append(Instruction.Create(OpCodes.Blt, lBody));
        // 같은 이름의 Transform 이 GameObject 를 덮어써 버린다.
        // (SetMapResources 는 GameObject 로 형변환하므로 Transform 이면 null 이 된다)
        // GameObject 만 한 번 더 훑어 이름표를 덮어쓴다.
        var goT = mod.ImportReference(ue.GetType("UnityEngine.GameObject"));
        pp.Append(Instruction.Create(OpCodes.Ldsfld, bundleFld));
        pp.Append(Instruction.Create(OpCodes.Ldtoken, goT));
        pp.Append(Instruction.Create(OpCodes.Call, typeFromHandle));
        pp.Append(Instruction.Create(OpCodes.Callvirt, abLoadAll));
        pp.Append(Instruction.Create(OpCodes.Stloc, vAll));
        pp.Append(Instruction.Create(OpCodes.Ldc_I4_0));
        pp.Append(Instruction.Create(OpCodes.Stloc, vI));
        var gTest = Instruction.Create(OpCodes.Ldloc, vI);
        var gBody = Instruction.Create(OpCodes.Ldsfld, mapFld);
        pp.Append(Instruction.Create(OpCodes.Br, gTest));
        pp.Append(gBody);
        pp.Append(Instruction.Create(OpCodes.Ldloc, vAll));
        pp.Append(Instruction.Create(OpCodes.Ldloc, vI));
        pp.Append(Instruction.Create(OpCodes.Ldelem_Ref));
        pp.Append(Instruction.Create(OpCodes.Callvirt, getName));
        pp.Append(Instruction.Create(OpCodes.Callvirt, toLower));
        pp.Append(Instruction.Create(OpCodes.Ldloc, vAll));
        pp.Append(Instruction.Create(OpCodes.Ldloc, vI));
        pp.Append(Instruction.Create(OpCodes.Ldelem_Ref));
        pp.Append(Instruction.Create(OpCodes.Callvirt, htSet));
        pp.Append(Instruction.Create(OpCodes.Ldloc, vI));
        pp.Append(Instruction.Create(OpCodes.Ldc_I4_1));
        pp.Append(Instruction.Create(OpCodes.Add));
        pp.Append(Instruction.Create(OpCodes.Stloc, vI));
        pp.Append(gTest);
        pp.Append(Instruction.Create(OpCodes.Ldloc, vAll));
        pp.Append(Instruction.Create(OpCodes.Ldlen));
        pp.Append(Instruction.Create(OpCodes.Conv_I4));
        pp.Append(Instruction.Create(OpCodes.Blt, gBody));

        pp.Append(Instruction.Create(OpCodes.Ldstr, "[CNPICK] 번들 이름표 "));
        pp.Append(Instruction.Create(OpCodes.Ldloc, vAll));
        pp.Append(Instruction.Create(OpCodes.Ldlen));
        pp.Append(Instruction.Create(OpCodes.Conv_I4));
        pp.Append(Instruction.Create(OpCodes.Box, mod.TypeSystem.Int32));
        pp.Append(Instruction.Create(OpCodes.Call, concatOO));
        pp.Append(Instruction.Create(OpCodes.Call, dbg));
        pp.Append(pHave);
        pp.Append(Instruction.Create(OpCodes.Ldsfld, mapFld));
        pp.Append(Instruction.Create(OpCodes.Ldarg_0));
        pp.Append(Instruction.Create(OpCodes.Ldarg_0));
        pp.Append(Instruction.Create(OpCodes.Ldc_I4, 47));
        pp.Append(Instruction.Create(OpCodes.Callvirt, lastIdx));
        pp.Append(Instruction.Create(OpCodes.Ldc_I4_1));
        pp.Append(Instruction.Create(OpCodes.Add));
        pp.Append(Instruction.Create(OpCodes.Callvirt, substr));
        pp.Append(Instruction.Create(OpCodes.Callvirt, toLower));
        pp.Append(Instruction.Create(OpCodes.Callvirt, htGet));
        pp.Append(Instruction.Create(OpCodes.Stloc, vHit));
        if (Environment.GetEnvironmentVariable("CHA_LOGREQ") == "1")
        {
            pp.Append(Instruction.Create(OpCodes.Ldstr, "[CNKEY] "));
            pp.Append(Instruction.Create(OpCodes.Ldarg_0));
            pp.Append(Instruction.Create(OpCodes.Ldarg_0));
            pp.Append(Instruction.Create(OpCodes.Ldc_I4, 47));
            pp.Append(Instruction.Create(OpCodes.Callvirt, lastIdx));
            pp.Append(Instruction.Create(OpCodes.Ldc_I4_1));
            pp.Append(Instruction.Create(OpCodes.Add));
            pp.Append(Instruction.Create(OpCodes.Callvirt, substr));
            pp.Append(Instruction.Create(OpCodes.Callvirt, toLower));
            pp.Append(Instruction.Create(OpCodes.Call, concat2));
            pp.Append(Instruction.Create(OpCodes.Ldstr, " -> "));
            pp.Append(Instruction.Create(OpCodes.Call, concat2));
            pp.Append(Instruction.Create(OpCodes.Ldloc, vHit));
            pp.Append(Instruction.Create(OpCodes.Call, concatOO));
            pp.Append(Instruction.Create(OpCodes.Call, dbg));
        }
        pp.Append(Instruction.Create(OpCodes.Ldloc, vHit));
        pp.Append(Instruction.Create(OpCodes.Brfalse, pNull));
        pp.Append(Instruction.Create(OpCodes.Ldloc, vHit));
        pp.Append(Instruction.Create(OpCodes.Castclass, uoRef));
        pp.Append(Instruction.Create(OpCodes.Ret));
        pp.Append(pNull);
        pp.Append(Instruction.Create(OpCodes.Ret));

        // __ChaResLoad = Resources.Load 먼저, 없으면 번들 이름표
        var resLoad = title.Methods.First(m => m.Name == "__ChaResLoad");
        var rb = resLoad.Body;
        rb.Instructions.Clear(); rb.ExceptionHandlers.Clear(); rb.Variables.Clear();
        var vR = new VariableDefinition(uoRef);
        rb.Variables.Add(vR); rb.InitLocals = true;
        var rp = rb.GetILProcessor();
        var rBundle = Instruction.Create(OpCodes.Ldarg_0);
        rp.Append(Instruction.Create(OpCodes.Ldarg_0));
        rp.Append(Instruction.Create(OpCodes.Call, resources));
        rp.Append(Instruction.Create(OpCodes.Stloc, vR));
        rp.Append(Instruction.Create(OpCodes.Ldloc, vR));
        rp.Append(Instruction.Create(OpCodes.Brfalse, rBundle));
        rp.Append(Instruction.Create(OpCodes.Ldloc, vR));
        rp.Append(Instruction.Create(OpCodes.Ret));
        rp.Append(rBundle);
        rp.Append(Instruction.Create(OpCodes.Call, pick));
        rp.Append(Instruction.Create(OpCodes.Ret));

        // __ChaMapHook 도 같은 표를 쓴다
        var mapHook = title.Methods.First(m => m.Name == "__ChaMapHook");
        var hb = mapHook.Body;
        hb.Instructions.Clear(); hb.ExceptionHandlers.Clear(); hb.Variables.Clear();
        hb.InitLocals = true;
        var hp = hb.GetILProcessor();
        // 진단: 무엇을 요청하는지 남긴다
        if (Environment.GetEnvironmentVariable("CHA_LOGREQ") == "1")
        {
            hp.Append(Instruction.Create(OpCodes.Ldstr, "[CNREQ] "));
            hp.Append(Instruction.Create(OpCodes.Ldarg_0));
            hp.Append(Instruction.Create(OpCodes.Call, concat2));
            hp.Append(Instruction.Create(OpCodes.Call, dbg));
        }
        // 원래 훅과 같은 범위만 가로챈다. 이 검사가 없으면 게임 전체의
        // ResourceByOption 호출을 마지막 이름 조각으로 가로채 차량 선택·주행이 깨진다.
        var startsWith = mod.ImportReference(strType.Methods.First(
            m => m.Name == "StartsWith" && m.Parameters.Count == 1
                 && m.Parameters[0].ParameterType.Name == "String"));
        var hUse = Instruction.Create(OpCodes.Ldarg_0);
        var hNull = Instruction.Create(OpCodes.Ldnull);
        hp.Append(Instruction.Create(OpCodes.Ldarg_0));
        hp.Append(Instruction.Create(OpCodes.Ldstr, "Background/"));
        hp.Append(Instruction.Create(OpCodes.Callvirt, startsWith));
        hp.Append(Instruction.Create(OpCodes.Brtrue, hUse));
        hp.Append(Instruction.Create(OpCodes.Ldarg_0));
        hp.Append(Instruction.Create(OpCodes.Ldstr, "Car/"));
        hp.Append(Instruction.Create(OpCodes.Callvirt, startsWith));
        hp.Append(Instruction.Create(OpCodes.Brfalse, hNull));
        hp.Append(hUse);
        hp.Append(Instruction.Create(OpCodes.Call, pick));
        hp.Append(Instruction.Create(OpCodes.Ret));
        hp.Append(hNull);
        hp.Append(Instruction.Create(OpCodes.Ret));
        Console.WriteLine("번들 자산을 이름표로 찾도록 고침");
        }

'''

p = 'tunnelfix.cs'
s = io.open(p, encoding='utf-8').read()
i = s.index('        // --- 4)')
j = s.index('        mod.Write(a[1]);', i)
io.open(p, 'w', encoding='utf-8').write(s[:i] + BLOCK + s[j:])
print('4번 패치 교체 완료')
