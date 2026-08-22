// 이미 패치된 Assembly-CSharp.dll 에 두 가지만 더 손본다.
//
//  1) Generic_Title::__ChaSetTunnel 을 통째로 다시 써서 터널 세트를 되살린다.
//     이식한 터널이 중국판 터널의 재질·메시를 끌어다 쓰던 문제(자산 이름 충돌)를
//     자산 쪽에서 해결했으므로, 빼 두었던 btunnel 을 다시 넣는다.
//     0 = 중국판 자신의 터널(건드리지 않음), 1 = gtunnel, 2 = btunnel
//
//  2) 에셋번들을 받아 오는 주소를 바꾼다.
//     PC 의 IP 는 망이 바뀌면 같이 바뀌므로 `adb reverse` 로 여는
//     127.0.0.1 을 쓴다.
//
// 본문을 통째로 갈아 끼우는 것은 실기에서 안전한 것으로 확인된 방식이다.
// (중간에 끼워 넣으면 모노 JIT 이 죽는다)
//
// 사용법: tunnelfix.exe <in.dll> <out.dll> <managed> [<번들URL>]
using System;
using System.Collections.Generic;
using System.Linq;
using Mono.Cecil;
using Mono.Cecil.Cil;

static class T
{
    // 중국판 자신의 터널(tunnel01~03)은 이 경로로는 맵이 비어 버린다.
    // 원래 빌드도 gtunnel 하나만 쓰고 있었으니(Random.Range(1,2)) 쓰지 않는다.
    // 자산 이름 충돌을 잡은 덕에 btunnel 을 다시 넣어 두 세트를 번갈아 쓴다.
    static readonly string[][] SETS = {
        new[] { "gtunnel01", "gtunnel02", "gtunnel03" },
        new[] { "btunnel01", "btunnel02", "btunnel03" },
    };

    static int Main(string[] a)
    {
        string url = a.Length > 3 ? a[3] : "http://127.0.0.1:8888/bundle/pack.unity3d";

        var res = new DefaultAssemblyResolver();
        res.AddSearchDirectory(a[2]);
        var mod = ModuleDefinition.ReadModule(
            a[0], new ReaderParameters { AssemblyResolver = res, ReadWrite = false });

        var title = mod.Types.First(t => t.Name == "Generic_Title");
        var bg = mod.Types.First(t => t.Name == "Background");
        var fld = bg.Fields.First(f => f.Name == "tunnelMapName");

        var ue = mod.AssemblyReferences.Any(r => r.Name == "UnityEngine")
            ? res.Resolve(mod.AssemblyReferences.First(r => r.Name == "UnityEngine")).MainModule
            : null;
        var rnd = mod.ImportReference(ue.GetType("UnityEngine.Random")
            .Methods.First(m => m.Name == "Range" && m.Parameters.Count == 2
                                && m.Parameters[0].ParameterType.Name == "Int32"));
        var dbg = mod.ImportReference(ue.GetType("UnityEngine.Debug")
            .Methods.First(m => m.Name == "Log" && m.Parameters.Count == 1));
        var strT = mod.TypeSystem.String;

        // 주소만 바꾸고 터널은 손대지 않는 모드(원인 가르기용)
        bool urlOnly = a.Length > 4 && a[4] == "urlonly";

        // --- 1) 터널 세트 --------------------------------------------------
        if (urlOnly) goto url;
        var me = title.Methods.First(m => m.Name == "__ChaSetTunnel");
        var body = me.Body;
        body.Instructions.Clear();
        body.ExceptionHandlers.Clear();
        body.Variables.Clear();
        var v = new VariableDefinition(mod.TypeSystem.Int32);
        body.Variables.Add(v);
        body.InitLocals = true;
        var il = body.GetILProcessor();

        // 확인용: 환경변수 CHA_TUNNEL 을 주면 그 세트만 나오게 고정한다
        int force = -1;
        {
            var t0 = Environment.GetEnvironmentVariable("CHA_TUNNEL");
            if (!string.IsNullOrEmpty(t0)) int.TryParse(t0, out force);
        }
        var end = Instruction.Create(OpCodes.Ret);
        il.Append(Instruction.Create(OpCodes.Ldc_I4, force >= 0 ? force : 0));
        il.Append(Instruction.Create(OpCodes.Ldc_I4,
            force >= 0 ? force + 1 : SETS.Length));
        il.Append(Instruction.Create(OpCodes.Call, rnd));
        il.Append(Instruction.Create(OpCodes.Stloc, v));

        for (int i = 0; i < SETS.Length; i++)
        {
            var names = SETS[i];
            var next = Instruction.Create(OpCodes.Nop);
            il.Append(Instruction.Create(OpCodes.Ldloc, v));
            il.Append(Instruction.Create(OpCodes.Ldc_I4, i));
            il.Append(Instruction.Create(OpCodes.Bne_Un, next));

            il.Append(Instruction.Create(OpCodes.Ldarg_0));
            il.Append(Instruction.Create(OpCodes.Ldc_I4, names.Length));
            il.Append(Instruction.Create(OpCodes.Newarr, strT));
            for (int k = 0; k < names.Length; k++)
            {
                il.Append(Instruction.Create(OpCodes.Dup));
                il.Append(Instruction.Create(OpCodes.Ldc_I4, k));
                il.Append(Instruction.Create(OpCodes.Ldstr, names[k]));
                il.Append(Instruction.Create(OpCodes.Stelem_Ref));
            }
            il.Append(Instruction.Create(OpCodes.Stfld, fld));
            il.Append(Instruction.Create(OpCodes.Ldstr, "[CNMAP] 터널 세트: " + names[0]));
            il.Append(Instruction.Create(OpCodes.Call, dbg));
            il.Append(Instruction.Create(OpCodes.Br, end));
            il.Append(next);
        }
        il.Append(end);
        Console.WriteLine("터널 세트 {0}가지: {1}", SETS.Length,
            string.Join(", ", SETS.Select(x => x[0]).ToArray()));

        // --- 2) 번들 주소 --------------------------------------------------
        url:
        int hit = 0;
        foreach (var t in mod.Types)
            foreach (var m in t.Methods)
            {
                if (!m.HasBody) continue;
                foreach (var ins in m.Body.Instructions)
                {
                    var s = ins.Operand as string;
                    if (ins.OpCode == OpCodes.Ldstr && s != null
                        && s.Contains("/bundle/pack.unity3d"))
                    {
                        ins.Operand = url;
                        hit++;
                    }
                }
            }
        Console.WriteLine("번들 주소 {0}곳 -> {1}", hit, url);

        if (!urlOnly)
        {
        // --- 3) 드라이버 배열 12칸 보장 -------------------------------------
        // CRSystem.UpdateDriverData 는 서버가 준 목록을 driver[characterNo] 로
        // 색인하는데, 그 앞에서 CreateDriver 를 부르는 건 "패킷이 널일 때"뿐이다.
        // 슬롯을 12개로 늘려 둔 상태라 배열이 그보다 짧으면 색인에서 터진다.
        // 메서드 첫머리에 CreateDriver 호출을 끼워 넣는다(입구 삽입은 안전한 방식).
        var crs = mod.Types.First(t => t.Name == "CRSystem");
        var create = crs.Methods.First(m => m.Name == "CreateDriver");
        var upd = crs.Methods.First(m => m.Name == "UpdateDriverData");
        var uil = upd.Body.GetILProcessor();
        var first = upd.Body.Instructions[0];
        uil.InsertBefore(first, Instruction.Create(OpCodes.Ldarg_0));
        uil.InsertBefore(first, Instruction.Create(OpCodes.Call, create));

        // CreateDriver 는 "널일 때만" 만든다. 길이가 모자란 경우도 다시 만들도록
        // 본문을 통째로 다시 쓴다(부분 삽입보다 안전하다).
        var drvFld = crs.Fields.First(f => f.Name == "driver");
        var drvType = ((ArrayType)drvFld.FieldType).ElementType;
        var drvDef = drvType.Resolve();
        var drvCtor = drvDef.Methods.First(m => m.Name == ".ctor" && m.Parameters.Count == 0);
        var setNo = drvDef.Methods.First(m => m.Name == "set_characterNo");
        var setHave = drvDef.Methods.First(m => m.Name == "set_haveDriver");
        var setSel = drvDef.Methods.First(m => m.Name == "set_isSelect");
        var playerT = mod.Types.First(t => t.Name == "Player");
        var pInst = playerT.Methods.First(m => m.Name == "get_instance");
        var pType = playerT.Methods.First(m => m.Name == "set_driverType");

        var cb = create.Body;
        cb.Instructions.Clear();
        cb.ExceptionHandlers.Clear();
        cb.Variables.Clear();
        var vi = new VariableDefinition(mod.TypeSystem.Int32);
        cb.Variables.Add(vi);
        cb.InitLocals = true;
        var q = cb.GetILProcessor();
        var ret = Instruction.Create(OpCodes.Ret);
        var build = Instruction.Create(OpCodes.Nop);

        q.Append(Instruction.Create(OpCodes.Ldarg_0));
        q.Append(Instruction.Create(OpCodes.Ldfld, drvFld));
        q.Append(Instruction.Create(OpCodes.Brfalse, build));
        q.Append(Instruction.Create(OpCodes.Ldarg_0));
        q.Append(Instruction.Create(OpCodes.Ldfld, drvFld));
        q.Append(Instruction.Create(OpCodes.Ldlen));
        q.Append(Instruction.Create(OpCodes.Conv_I4));
        q.Append(Instruction.Create(OpCodes.Ldc_I4, 12));
        q.Append(Instruction.Create(OpCodes.Bge, ret));
        q.Append(build);
        q.Append(Instruction.Create(OpCodes.Ldarg_0));
        q.Append(Instruction.Create(OpCodes.Ldc_I4, 12));
        q.Append(Instruction.Create(OpCodes.Newarr, drvType));
        q.Append(Instruction.Create(OpCodes.Stfld, drvFld));
        q.Append(Instruction.Create(OpCodes.Ldc_I4_0));
        q.Append(Instruction.Create(OpCodes.Stloc, vi));
        var loopTest = Instruction.Create(OpCodes.Ldloc, vi);
        var loopBody = Instruction.Create(OpCodes.Ldarg_0);
        q.Append(Instruction.Create(OpCodes.Br, loopTest));
        q.Append(loopBody);
        q.Append(Instruction.Create(OpCodes.Ldfld, drvFld));
        q.Append(Instruction.Create(OpCodes.Ldloc, vi));
        q.Append(Instruction.Create(OpCodes.Newobj, drvCtor));
        q.Append(Instruction.Create(OpCodes.Stelem_Ref));
        q.Append(Instruction.Create(OpCodes.Ldloc, vi));
        q.Append(Instruction.Create(OpCodes.Ldc_I4_1));
        q.Append(Instruction.Create(OpCodes.Add));
        q.Append(Instruction.Create(OpCodes.Stloc, vi));
        q.Append(loopTest);
        q.Append(Instruction.Create(OpCodes.Ldc_I4, 12));
        q.Append(Instruction.Create(OpCodes.Blt, loopBody));
        // 0번은 기본 드라이버
        q.Append(Instruction.Create(OpCodes.Ldarg_0));
        q.Append(Instruction.Create(OpCodes.Ldfld, drvFld));
        q.Append(Instruction.Create(OpCodes.Ldc_I4_0));
        q.Append(Instruction.Create(OpCodes.Ldelem_Ref));
        q.Append(Instruction.Create(OpCodes.Ldc_I4_0));
        q.Append(Instruction.Create(OpCodes.Callvirt, setNo));
        q.Append(Instruction.Create(OpCodes.Ldarg_0));
        q.Append(Instruction.Create(OpCodes.Ldfld, drvFld));
        q.Append(Instruction.Create(OpCodes.Ldc_I4_0));
        q.Append(Instruction.Create(OpCodes.Ldelem_Ref));
        q.Append(Instruction.Create(OpCodes.Ldc_I4_1));
        q.Append(Instruction.Create(OpCodes.Callvirt, setHave));
        q.Append(Instruction.Create(OpCodes.Ldarg_0));
        q.Append(Instruction.Create(OpCodes.Ldfld, drvFld));
        q.Append(Instruction.Create(OpCodes.Ldc_I4_0));
        q.Append(Instruction.Create(OpCodes.Ldelem_Ref));
        q.Append(Instruction.Create(OpCodes.Ldc_I4_1));
        q.Append(Instruction.Create(OpCodes.Callvirt, setSel));
        q.Append(Instruction.Create(OpCodes.Call, pInst));
        q.Append(Instruction.Create(OpCodes.Ldc_I4_0));
        q.Append(Instruction.Create(OpCodes.Callvirt, pType));
        q.Append(ret);
        Console.WriteLine("드라이버 배열이 12칸보다 짧으면 다시 만들도록 고침");

        // 4번은 기본으로 끈다. 이름표를 마지막 조각으로만 맞추다 보니
        // 게임 전체의 ResourceByOption 호출까지 가로채 차량 선택·주행이 깨졌다.
        // 번들이 안 열릴 때만(CHA_NAMETABLE=1) 임시로 켠다.
        // --- 4) 번들 자산을 이름표로 찾기 -----------------------------------
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
        //
        // 다만 "Character VOX/" 는 **번들을 먼저** 본다.
        // 기본 드라이버 4명(sara bin dokang nayoubi)의 보이스는 중국판 Resources 에도
        // 있지만 중국어 더빙이다. 한국어 클립을 번들에 같은 이름으로 넣어 두고
        // 이 경로만 번들이 이기게 한다. (다른 경로까지 번들 우선으로 바꾸면
        //  ResourceByOption 의 옵션 처리를 건너뛰어 차고 차량이 통째로 사라진다)
        var strTypeR = mod.ImportReference(typeof(string)).Resolve();
        var startsWithR = mod.ImportReference(strTypeR.Methods.First(
            m => m.Name == "StartsWith" && m.Parameters.Count == 1
                 && m.Parameters[0].ParameterType.Name == "String"));

        var resLoad = title.Methods.First(m => m.Name == "__ChaResLoad");
        var rb = resLoad.Body;
        rb.Instructions.Clear(); rb.ExceptionHandlers.Clear(); rb.Variables.Clear();
        var vR = new VariableDefinition(uoRef);
        rb.Variables.Add(vR); rb.InitLocals = true;
        var rp = rb.GetILProcessor();
        var rBundle = Instruction.Create(OpCodes.Ldarg_0);
        var rRes = Instruction.Create(OpCodes.Ldarg_0);
        // if (name.StartsWith("Character VOX/")) { v = pick(name); if (v) return v; }
        rp.Append(Instruction.Create(OpCodes.Ldarg_0));
        rp.Append(Instruction.Create(OpCodes.Ldstr, "Character VOX/"));
        rp.Append(Instruction.Create(OpCodes.Callvirt, startsWithR));
        rp.Append(Instruction.Create(OpCodes.Brfalse, rRes));
        rp.Append(Instruction.Create(OpCodes.Ldarg_0));
        rp.Append(Instruction.Create(OpCodes.Call, pick));
        rp.Append(Instruction.Create(OpCodes.Stloc, vR));
        rp.Append(Instruction.Create(OpCodes.Ldloc, vR));
        rp.Append(Instruction.Create(OpCodes.Brfalse, rRes));
        rp.Append(Instruction.Create(OpCodes.Ldloc, vR));
        rp.Append(Instruction.Create(OpCodes.Ret));
        // v = Resources.Load(name); if (v) return v; else return pick(name);
        rp.Append(rRes);
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

        mod.Write(a[1]);
        Console.WriteLine("저장: {0}", a[1]);
        return 0;
    }
}
