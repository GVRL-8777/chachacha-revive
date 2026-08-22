// 차차차 Assembly-CSharp.dll 패처 (Mono.Cecil)
//
// 1) AssetBundleManager.GetResourceDBFile 을 에셋 번들 대신 아래 순서로 읽게 바꾼다:
//      /sdcard/chachacha/<name>.json            (adb push 로 밸런스 즉시 교체)
//      <persistentDataPath>/chachacha/<name>.json
//      DLL 안에 ldstr 로 박아넣은 기본값
//    2014년 CDN 은 죽었고 Unity 4 는 번들 빌드가 Pro 전용이라, 번들 경로 자체를 없앤다.
//    원본은 번들.mainAsset 을 서버 발급 키로 AES 복호화했지만 어차피 키를 우리가 정하므로
//    암호화 계층은 통째로 걷어낸다.
//
// 2) 게스트 로그인 노출 + 하루 판수 제한 해제 (기존 patchil.py 와 동일한 효과).
//
// 사용법: dbhook.exe <in.dll> <out.dll> <managed폴더> <db폴더> [판수]
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Mono.Cecil;
using Mono.Cecil.Cil;

static class Program
{
    static ModuleDefinition mod;
    static AssemblyDefinition mscorlib, unityEngine;

    static int Main(string[] args)
    {
        if (args.Length < 4)
        {
            Console.Error.WriteLine("usage: dbhook <in.dll> <out.dll> <managed-dir> <db-dir> [playCount]");
            return 2;
        }
        string inDll = args[0], outDll = args[1], managed = args[2], dbDir = args[3];
        int playCount = args.Length > 4 ? int.Parse(args[4]) : 999999;

        var resolver = new DefaultAssemblyResolver();
        resolver.AddSearchDirectory(managed);
        var asm = AssemblyDefinition.ReadAssembly(inDll,
            new ReaderParameters { AssemblyResolver = resolver, ReadWrite = false });
        mod = asm.MainModule;
        Console.WriteLine("런타임: {0}, 참조 어셈블리: {1}", mod.RuntimeVersion,
            string.Join(", ", mod.AssemblyReferences.Select(r => r.Name).ToArray()));

        mscorlib = resolver.Resolve(mod.AssemblyReferences.First(r => r.Name == "mscorlib"));
        unityEngine = resolver.Resolve(mod.AssemblyReferences.First(r => r.Name == "UnityEngine"));

        // ---- 필요한 외부 메서드 참조 (스트리핑 생존 확인된 것만 사용) ----
        var tString = Def(mscorlib, "System.String");
        var opEq = Import(tString.Methods.First(m => m.Name == "op_Equality"));
        var concat2 = Import(Concat(tString, 2));
        var concat3 = Import(Concat(tString, 3));
        var concat4 = Import(Concat(tString, 4));

        var tFile = Def(mscorlib, "System.IO.File");
        var fileExists = Import(tFile.Methods.First(m => m.Name == "Exists"));
        var fileRead = Import(tFile.Methods.First(m => m.Name == "ReadAllBytes"));

        var tEnc = Def(mscorlib, "System.Text.Encoding");
        var encUtf8 = Import(tEnc.Methods.First(m => m.Name == "get_UTF8"));
        var encGetString = Import(tEnc.Methods.First(
            m => m.Name == "GetString" && m.Parameters.Count == 1));

        var tApp = Def(unityEngine, "UnityEngine.Application");
        var appPersist = Import(tApp.Methods.First(m => m.Name == "get_persistentDataPath"));

        MethodReference debugLog = null;
        var tDebug = unityEngine.MainModule.GetType("UnityEngine.Debug");
        if (tDebug != null)
        {
            var m = tDebug.Methods.FirstOrDefault(x => x.Name == "Log" && x.Parameters.Count == 1);
            if (m != null) debugLog = Import(m);
        }
        Console.WriteLine("Debug.Log 사용 가능: {0}", debugLog != null);

        var abm = mod.GetType("AssetBundleManager");
        if (abm == null) throw new Exception("AssetBundleManager 타입 없음");

        // ---- (1) DB 본문을 담는 정적 메서드 생성 ----
        var files = Directory.GetFiles(dbDir, "*.json").OrderBy(f => f).ToArray();
        if (files.Length == 0) throw new Exception("DB json 이 하나도 없음: " + dbDir);
        var dbGet = new MethodDefinition("__ChaDB",
            MethodAttributes.Public | MethodAttributes.Static | MethodAttributes.HideBySig,
            mod.TypeSystem.String);
        dbGet.Parameters.Add(new ParameterDefinition("name", ParameterAttributes.None, mod.TypeSystem.String));
        var g = dbGet.Body.GetILProcessor();
        long total = 0;
        foreach (var f in files)
        {
            string key = Path.GetFileNameWithoutExtension(f);
            string json = File.ReadAllText(f);
            total += json.Length;
            var next = Instruction.Create(OpCodes.Nop);
            g.Append(Instruction.Create(OpCodes.Ldarg_0));
            g.Append(Instruction.Create(OpCodes.Ldstr, key));
            g.Append(Instruction.Create(OpCodes.Call, opEq));
            g.Append(Instruction.Create(OpCodes.Brfalse, next));
            g.Append(Instruction.Create(OpCodes.Ldstr, json));
            g.Append(Instruction.Create(OpCodes.Ret));
            g.Append(next);
            Console.WriteLine("  내장 DB: {0,-24} {1,8:N0} 자", key, json.Length);
        }
        g.Append(Instruction.Create(OpCodes.Ldnull));
        g.Append(Instruction.Create(OpCodes.Ret));
        abm.Methods.Add(dbGet);
        Console.WriteLine("  -> __ChaDB {0}건 / {1:N0} 자 내장", files.Length, total);

        // ---- (2) GetResourceDBFile 본문 교체 ----
        var target = abm.Methods.First(m => m.Name == "GetResourceDBFile");
        var b = target.Body;
        b.Instructions.Clear(); b.Variables.Clear(); b.ExceptionHandlers.Clear();
        b.InitLocals = true;
        var vPath = new VariableDefinition(mod.TypeSystem.String);
        b.Variables.Add(vPath);
        var il = b.GetILProcessor();

        var lTry2 = Instruction.Create(OpCodes.Nop);
        var lBuiltin = Instruction.Create(OpCodes.Nop);

        // p = "/sdcard/chachacha/" + name + ".json"
        il.Append(Instruction.Create(OpCodes.Ldstr, "/sdcard/chachacha/"));
        il.Append(Instruction.Create(OpCodes.Ldarg_1));
        il.Append(Instruction.Create(OpCodes.Ldstr, ".json"));
        il.Append(Instruction.Create(OpCodes.Call, concat3));
        il.Append(Instruction.Create(OpCodes.Stloc, vPath));
        EmitReadIfExists(il, vPath, lTry2, fileExists, fileRead, encUtf8, encGetString, concat2, debugLog);

        // p = Application.persistentDataPath + "/chachacha/" + name + ".json"
        il.Append(lTry2);
        il.Append(Instruction.Create(OpCodes.Call, appPersist));
        il.Append(Instruction.Create(OpCodes.Ldstr, "/chachacha/"));
        il.Append(Instruction.Create(OpCodes.Ldarg_1));
        il.Append(Instruction.Create(OpCodes.Ldstr, ".json"));
        il.Append(Instruction.Create(OpCodes.Call, concat4));
        il.Append(Instruction.Create(OpCodes.Stloc, vPath));
        EmitReadIfExists(il, vPath, lBuiltin, fileExists, fileRead, encUtf8, encGetString, concat2, debugLog);

        // return __ChaDB(name);
        il.Append(lBuiltin);
        if (debugLog != null)
        {
            il.Append(Instruction.Create(OpCodes.Ldstr, "[CHADB] builtin "));
            il.Append(Instruction.Create(OpCodes.Ldarg_1));
            il.Append(Instruction.Create(OpCodes.Call, concat2));
            il.Append(Instruction.Create(OpCodes.Call, debugLog));
        }
        il.Append(Instruction.Create(OpCodes.Ldarg_1));
        il.Append(Instruction.Create(OpCodes.Call, dbGet));
        il.Append(Instruction.Create(OpCodes.Ret));
        Console.WriteLine("GetResourceDBFile 재작성 완료 ({0} 명령)", b.Instructions.Count);

        // ---- (2b) 에셋 번들 게터를 로컬 Resources 폴백으로 교체 ----
        var tRes = Def(unityEngine, "UnityEngine.Resources");
        var resLoad = Import(tRes.Methods.First(m => m.Name == "Load" && m.Parameters.Count == 2));
        var tUObj = Def(unityEngine, "UnityEngine.Object");
        var uObjRef = mod.ImportReference(tUObj);
        var tType = Def(mscorlib, "System.Type");
        var getTypeFromHandle = Import(tType.Methods.First(m => m.Name == "GetTypeFromHandle"));

        // static UnityEngine.Object __ChaRes(string bundle, string asset, System.Type t)
        var chaRes = new MethodDefinition("__ChaRes",
            MethodAttributes.Public | MethodAttributes.Static | MethodAttributes.HideBySig, uObjRef);
        chaRes.Parameters.Add(new ParameterDefinition("bundle", ParameterAttributes.None, mod.TypeSystem.String));
        chaRes.Parameters.Add(new ParameterDefinition("asset", ParameterAttributes.None, mod.TypeSystem.String));
        chaRes.Parameters.Add(new ParameterDefinition("t", ParameterAttributes.None, mod.ImportReference(tType)));
        chaRes.Body.InitLocals = true;
        var vObj = new VariableDefinition(uObjRef);
        chaRes.Body.Variables.Add(vObj);
        var r = chaRes.Body.GetILProcessor();
        var done = Instruction.Create(OpCodes.Nop);
        // Resources.Load(<prefix> + asset, t) 를 순서대로 시도한다.
        // 원본은 CDN 번들 이름/에셋 이름 2단 구조였지만 로컬 Resources 는 폴더 경로라
        // 접두사를 붙여가며 찾는다.
        string[] prefixes = { null, "UI/", "Car/", "Background/", "Hurdle/", "Item/",
                              "_Arts/", "Prefabs/", "StringTable/", "DataBase/", "AssetBundle/" };
        foreach (var pre in prefixes)
        {
            if (pre == null) r.Append(Instruction.Create(OpCodes.Ldarg_1));
            else
            {
                r.Append(Instruction.Create(OpCodes.Ldstr, pre));
                r.Append(Instruction.Create(OpCodes.Ldarg_1));
                r.Append(Instruction.Create(OpCodes.Call, concat2));
            }
            r.Append(Instruction.Create(OpCodes.Ldarg_2));
            r.Append(Instruction.Create(OpCodes.Call, resLoad));
            r.Append(Instruction.Create(OpCodes.Stloc, vObj));
            r.Append(Instruction.Create(OpCodes.Ldloc, vObj));
            r.Append(Instruction.Create(OpCodes.Brtrue, done));
        }
        // 마지막 수단: 에셋 이름 대신 번들 이름으로 (Background_Hurdle -> Background 같은 경우)
        r.Append(Instruction.Create(OpCodes.Ldarg_0));
        r.Append(Instruction.Create(OpCodes.Ldarg_2));
        r.Append(Instruction.Create(OpCodes.Call, resLoad));
        r.Append(Instruction.Create(OpCodes.Stloc, vObj));
        r.Append(done);
        if (debugLog != null)
        {
            r.Append(Instruction.Create(OpCodes.Ldstr, "[CHARES] "));
            r.Append(Instruction.Create(OpCodes.Ldarg_0));
            r.Append(Instruction.Create(OpCodes.Ldstr, "/"));
            r.Append(Instruction.Create(OpCodes.Ldarg_1));
            r.Append(Instruction.Create(OpCodes.Call, concat4));
            r.Append(Instruction.Create(OpCodes.Call, debugLog));
        }
        r.Append(Instruction.Create(OpCodes.Ldloc, vObj));
        r.Append(Instruction.Create(OpCodes.Ret));
        abm.Methods.Add(chaRes);

        // 각 게터를 __ChaRes 호출로 재작성한다. 반환 타입은 원본 본문의 isinst 피연산자에서 얻는다.
        // (bundle, asset) 2인자 게터와 (name) 1인자 게터를 구분해 처리.
        string[] two = { "GetResourceGameObject", "GetResourceAudioClip", "GetResourceUIAtlas", "GetResourceBasicObject" };
        foreach (var nm in two) RewriteGetter(abm, nm, true, chaRes, getTypeFromHandle);
        RewriteGetter(abm, "GetResourceTextFile", false, chaRes, getTypeFromHandle);

        // ---- (2d) 차량 모델에 PlayerCarData 컴포넌트가 없으면 붙여준다 ----
        // 원본 CDN 번들의 Player_<차명>_<등급> 프리팹에는 PlayerCarData 가 붙어 있었지만
        // APK 로컬 Resources 의 car/car_01/car_01 은 원본 메시라 컴포넌트가 없다.
        // 그대로 두면 OilGauge.Update 가 매 프레임 NRE 를 낸다.
        var pcd = mod.GetType("PlayerCarData");
        var tGO = Def(unityEngine, "UnityEngine.GameObject");
        var goGetComp = Import(tGO.Methods.First(
            m => m.Name == "GetComponent" && m.Parameters.Count == 1 && !m.HasGenericParameters));
        var goAddComp = Import(tGO.Methods.First(
            m => m.Name == "AddComponent" && m.Parameters.Count == 1 && !m.HasGenericParameters));
        var pcdRef = mod.ImportReference(pcd);

        var ensure = new MethodDefinition("__ChaPCD",
            MethodAttributes.Public | MethodAttributes.Static | MethodAttributes.HideBySig, pcdRef);
        ensure.Parameters.Add(new ParameterDefinition("go", ParameterAttributes.None, mod.ImportReference(tGO)));
        ensure.Body.InitLocals = true;
        var vC = new VariableDefinition(pcdRef);
        ensure.Body.Variables.Add(vC);
        var ep = ensure.Body.GetILProcessor();
        var retNull = Instruction.Create(OpCodes.Ldnull);
        var haveIt = Instruction.Create(OpCodes.Ldloc, vC);
        ep.Append(Instruction.Create(OpCodes.Ldarg_0));
        ep.Append(Instruction.Create(OpCodes.Brfalse, retNull));
        ep.Append(Instruction.Create(OpCodes.Ldarg_0));
        ep.Append(Instruction.Create(OpCodes.Ldtoken, pcdRef));
        ep.Append(Instruction.Create(OpCodes.Call, getTypeFromHandle));
        ep.Append(Instruction.Create(OpCodes.Callvirt, goGetComp));
        ep.Append(Instruction.Create(OpCodes.Isinst, pcdRef));
        ep.Append(Instruction.Create(OpCodes.Stloc, vC));
        ep.Append(Instruction.Create(OpCodes.Ldloc, vC));
        ep.Append(Instruction.Create(OpCodes.Brtrue, haveIt));
        ep.Append(Instruction.Create(OpCodes.Ldarg_0));
        ep.Append(Instruction.Create(OpCodes.Ldtoken, pcdRef));
        ep.Append(Instruction.Create(OpCodes.Call, getTypeFromHandle));
        ep.Append(Instruction.Create(OpCodes.Callvirt, goAddComp));
        ep.Append(Instruction.Create(OpCodes.Isinst, pcdRef));
        ep.Append(Instruction.Create(OpCodes.Stloc, vC));
        if (debugLog != null)
        {
            ep.Append(Instruction.Create(OpCodes.Ldstr, "[CHAPCD] PlayerCarData 컴포넌트 추가"));
            ep.Append(Instruction.Create(OpCodes.Call, debugLog));
        }
        ep.Append(haveIt);
        ep.Append(Instruction.Create(OpCodes.Ret));
        ep.Append(retNull);
        ep.Append(Instruction.Create(OpCodes.Ret));
        abm.Methods.Add(ensure);

        // ChangePlayerModel 의 GetComponent<PlayerCarData>() 호출을 __ChaPCD 로 갈아끼운다.
        // (스택 효과가 같아 한 명령만 바꾸면 된다: GameObject 하나 pop, PlayerCarData 하나 push)
        int pcdPatched = 0;
        foreach (var t in mod.Types)
            foreach (var m3 in t.Methods)
            {
                // 수신자가 GameObject 인 곳만 바꾼다. BaseData::ResetLink 등은
                // Component.GetComponent<T>() 라 인자 타입이 맞지 않는다.
                if (!m3.HasBody || m3.Name != "ChangePlayerModel") continue;
                var ins = m3.Body.Instructions;
                for (int k = 1; k < ins.Count; k++)
                {
                    var fr = ins[k].Operand as FieldReference;
                    if (ins[k].OpCode != OpCodes.Stfld || fr == null) continue;
                    if (fr.FieldType.FullName != "PlayerCarData") continue;
                    var prev = ins[k - 1];
                    if (prev.OpCode != OpCodes.Callvirt && prev.OpCode != OpCodes.Call) continue;
                    prev.OpCode = OpCodes.Call;
                    prev.Operand = ensure;
                    pcdPatched++;
                    Console.WriteLine("  PlayerCarData 보정: {0}::{1}", t.Name, m3.Name);
                }
            }
        if (pcdPatched == 0) Console.WriteLine("  [경고] PlayerCarData 대입 지점을 찾지 못했습니다");

        // ---- (2e) OilGauge 의 경고음 AudioSource 를 보장한다 ----
        // Awake 가 GetComponent<AudioSource>() 로 받는데 씬에 붙어 있지 않아 null 이고,
        // Update 가 매 프레임 그걸 Play() 해서 NRE 가 쏟아진다. 없으면 붙여준다.
        var tAudio = Def(unityEngine, "UnityEngine.AudioSource");
        var audioRef = mod.ImportReference(tAudio);
        var tComp = Def(unityEngine, "UnityEngine.Component");
        var compGetComp = Import(tComp.Methods.First(
            m => m.Name == "GetComponent" && m.Parameters.Count == 1 && !m.HasGenericParameters));
        var compGO = Import(tComp.Methods.First(m => m.Name == "get_gameObject"));

        var ensureAudio = new MethodDefinition("__ChaAudio",
            MethodAttributes.Public | MethodAttributes.Static | MethodAttributes.HideBySig, audioRef);
        ensureAudio.Parameters.Add(new ParameterDefinition("c", ParameterAttributes.None,
            mod.ImportReference(tComp)));
        ensureAudio.Body.InitLocals = true;
        var vA = new VariableDefinition(audioRef);
        ensureAudio.Body.Variables.Add(vA);
        var ap = ensureAudio.Body.GetILProcessor();
        var aNull = Instruction.Create(OpCodes.Ldnull);
        var aHave = Instruction.Create(OpCodes.Ldloc, vA);
        ap.Append(Instruction.Create(OpCodes.Ldarg_0));
        ap.Append(Instruction.Create(OpCodes.Brfalse, aNull));
        ap.Append(Instruction.Create(OpCodes.Ldarg_0));
        ap.Append(Instruction.Create(OpCodes.Ldtoken, audioRef));
        ap.Append(Instruction.Create(OpCodes.Call, getTypeFromHandle));
        ap.Append(Instruction.Create(OpCodes.Callvirt, compGetComp));
        ap.Append(Instruction.Create(OpCodes.Isinst, audioRef));
        ap.Append(Instruction.Create(OpCodes.Stloc, vA));
        ap.Append(Instruction.Create(OpCodes.Ldloc, vA));
        ap.Append(Instruction.Create(OpCodes.Brtrue, aHave));
        ap.Append(Instruction.Create(OpCodes.Ldarg_0));
        ap.Append(Instruction.Create(OpCodes.Callvirt, compGO));
        ap.Append(Instruction.Create(OpCodes.Ldtoken, audioRef));
        ap.Append(Instruction.Create(OpCodes.Call, getTypeFromHandle));
        ap.Append(Instruction.Create(OpCodes.Callvirt, goAddComp));
        ap.Append(Instruction.Create(OpCodes.Isinst, audioRef));
        ap.Append(Instruction.Create(OpCodes.Stloc, vA));
        if (debugLog != null)
        {
            ap.Append(Instruction.Create(OpCodes.Ldstr, "[CHAAUDIO] AudioSource 컴포넌트 추가"));
            ap.Append(Instruction.Create(OpCodes.Call, debugLog));
        }
        ap.Append(aHave);
        ap.Append(Instruction.Create(OpCodes.Ret));
        ap.Append(aNull);
        ap.Append(Instruction.Create(OpCodes.Ret));
        abm.Methods.Add(ensureAudio);

        int audioPatched = 0;
        foreach (var t in mod.Types)
            foreach (var m4 in t.Methods)
            {
                if (!m4.HasBody || m4.Name != "Awake" || t.Name != "OilGauge") continue;
                var ins = m4.Body.Instructions;
                for (int k = 1; k < ins.Count; k++)
                {
                    var fr = ins[k].Operand as FieldReference;
                    if (ins[k].OpCode != OpCodes.Stfld || fr == null) continue;
                    if (fr.FieldType.FullName != "UnityEngine.AudioSource") continue;
                    var prev = ins[k - 1];
                    if (prev.OpCode != OpCodes.Callvirt && prev.OpCode != OpCodes.Call) continue;
                    prev.OpCode = OpCodes.Call;
                    prev.Operand = ensureAudio;
                    audioPatched++;
                    Console.WriteLine("  AudioSource 보정: {0}::{1}", t.Name, m4.Name);
                }
            }
        if (audioPatched == 0) Console.WriteLine("  [경고] OilGauge AudioSource 지점을 찾지 못했습니다");

        // ---- (2f) PlayerCarData 가 없을 때 OilGauge.Update 가 매 프레임 NRE 를 내는 것을 막는다 ----
        // PlayerCarData 는 CDN 번들 프리팹에 붙어 있던 MonoBehaviour 라 로컬 모델엔 없고,
        // Unity 4 는 MonoScript 가 빌드에 없으면 AddComponent(Type) 도 실패한다
        // ("Can't add component because class '' doesn't exist!").
        // 따라서 데이터가 없으면 게이지 갱신을 건너뛰게만 한다.
        var carType = mod.GetType("Car");
        var pcdField = carType == null ? null :
            carType.Fields.FirstOrDefault(f => f.FieldType.FullName == "PlayerCarData");
        var playerType = mod.GetType("Player");
        var playerInst = playerType == null ? null :
            playerType.Methods.FirstOrDefault(m => m.Name == "get_instance");
        var oil = mod.GetType("OilGauge");
        var oilUpdate = oil == null ? null : oil.Methods.FirstOrDefault(m => m.Name == "Update");
        if (pcdField != null && playerInst != null && oilUpdate != null)
        {
            var body = oilUpdate.Body;
            var first = body.Instructions[0];
            var gil = body.GetILProcessor();
            var retIns = Instruction.Create(OpCodes.Ret);
            gil.InsertBefore(first, Instruction.Create(OpCodes.Call, playerInst));
            gil.InsertBefore(first, Instruction.Create(OpCodes.Brfalse, retIns));
            gil.InsertBefore(first, Instruction.Create(OpCodes.Call, playerInst));
            gil.InsertBefore(first, Instruction.Create(OpCodes.Ldfld, pcdField));
            gil.InsertBefore(first, Instruction.Create(OpCodes.Brtrue, first));
            gil.InsertBefore(first, retIns);
            Console.WriteLine("  OilGauge::Update 널 가드 삽입 (필드 {0})", pcdField.Name);
        }
        else Console.WriteLine("  [경고] OilGauge 널 가드를 넣지 못했습니다");

        // ---- (2c) 게스트 기본 차량 이름을 로컬 모델이 있는 차로 바꾼다 ----
        // Generic_Title::OnGuestPlayOk 가 CRSystem.carName 을 "AVEO" 로 하드코딩하는데,
        // AVEO 모델은 CDN 번들에만 있었다. DB/로컬 Resources 에 맞춰 CAR_01 로 돌린다.
        int swapped = 0;
        foreach (var t in mod.Types)
            foreach (var m2 in t.Methods)
            {
                if (!m2.HasBody) continue;
                foreach (var ins in m2.Body.Instructions)
                    if (ins.OpCode == OpCodes.Ldstr && (string)ins.Operand == "AVEO")
                    {
                        ins.Operand = GUEST_CAR;
                        Console.WriteLine("  기본차 문자열 교체: {0}::{1}  AVEO -> {2}",
                                          t.Name, m2.Name, GUEST_CAR);
                        swapped++;
                    }
            }
        if (swapped == 0) Console.WriteLine("  [경고] \"AVEO\" 리터럴을 찾지 못했습니다");

        // ---- (2g) mode=login: 게스트 버튼을 정식 게임서버 로그인으로 돌린다 ----
        // 게스트 모드는 /service/inspection/check/ 하나만 부르고 곧장 로컬 레이스로 가버려서
        // 로비/상점 엔드포인트를 하나도 타지 않는다. 카카오는 폐쇄돼 소셜 3단계를 통과할 수 없으므로
        // Generic_Title::OnGuestPlayOk 를 ServerLoginProcess(=LoginManager.GameServerLogin) 로 바꾼다.
        if (mode == "login")
        {
            var title = mod.GetType("Generic_Title");
            var slp = title.Methods.First(m => m.Name == "ServerLoginProcess");
            var ok = title.Methods.First(m => m.Name == "OnGuestPlayOk");
            var okb = ok.Body;
            okb.Instructions.Clear(); okb.Variables.Clear(); okb.ExceptionHandlers.Clear();
            var okil = okb.GetILProcessor();
            okil.Append(Instruction.Create(OpCodes.Ldarg_0));
            okil.Append(Instruction.Create(OpCodes.Call, slp));
            okil.Append(Instruction.Create(OpCodes.Ret));
            Console.WriteLine("  OnGuestPlayOk -> ServerLoginProcess (정식 서버 로그인)");

            // 넷마블 보안 모듈은 서버가 없으므로 건너뛴다
            ConstBody(mod.GetType("Glocalization_Specification").Methods
                         .First(m => m.Name == "get_isNotNetmarbleSecurity"),
                      Instruction.Create(OpCodes.Ldc_I4_1), "넷마블 보안 건너뜀");

            // 로그인 성공 후 로비 진입은
            //   OnClickSocialLoginButton -> BillingPlatformInitialize
            //   -> BillingPlatformInitializeProcess -> GameServerDataLoadingProcess
            //   -> isCompletedLogin=true -> Generic_Title.Update -> MoveLobbySceneProcess
            // 순서인데, 구글 결제 플랫폼 초기화는 이 환경에서 성공할 수 없고
            // 실패하면 RebootApplication 으로 빠진다. 결제 단계를 건너뛴다.
            var lm = mod.GetType("LoginManager");
            var billInit = lm.Methods.First(m => m.Name == "BillingPlatformInitialize");
            var dataProc = lm.Methods.First(m => m.Name == "GameServerDataLoadingProcess");
            var startCo = billInit.Body.Instructions
                .Select(x => x.Operand as MethodReference)
                .First(x => x != null && x.Name == "StartCoroutine");
            var bb = billInit.Body;
            bb.Instructions.Clear(); bb.Variables.Clear(); bb.ExceptionHandlers.Clear();
            var bil = bb.GetILProcessor();
            bil.Append(Instruction.Create(OpCodes.Ldarg_0));
            bil.Append(Instruction.Create(OpCodes.Ldarg_0));
            bil.Append(Instruction.Create(OpCodes.Call, dataProc));
            bil.Append(Instruction.Create(OpCodes.Call, startCo));
            bil.Append(Instruction.Create(OpCodes.Pop));
            bil.Append(Instruction.Create(OpCodes.Ret));
            Console.WriteLine("  BillingPlatformInitialize -> GameServerDataLoadingProcess (결제 건너뜀)");

            // 로그인 전 NetQuery 요청(/setting/control/ 등)은 이미 암호화되어 나간다.
            // Aes 의 3번째 생성자가 키=IV=OSPlatform.GetSystemSecretKey() 의 앞 16바이트를
            // 쓰는데, 이건 기기에서 파생되는 값이라 서버가 알 수 없다.
            // 클라이언트를 우리가 통제하므로 고정 키로 바꾼다.
            var osp = mod.GetType("OSPlatform").Methods.First(m => m.Name == "GetSystemSecretKey");
            var ob = osp.Body;
            ob.Instructions.Clear(); ob.Variables.Clear(); ob.ExceptionHandlers.Clear();
            var oil = ob.GetILProcessor();
            if (osp.ReturnType.FullName == "System.String")
            {
                oil.Append(Instruction.Create(OpCodes.Ldstr, PRELOGIN_KEY));
            }
            else
            {
                var encGetBytes = Import(tEnc.Methods.First(
                    m => m.Name == "GetBytes" && m.Parameters.Count == 1
                         && m.Parameters[0].ParameterType.FullName == "System.String"));
                oil.Append(Instruction.Create(OpCodes.Call, encUtf8));
                oil.Append(Instruction.Create(OpCodes.Ldstr, PRELOGIN_KEY));
                oil.Append(Instruction.Create(OpCodes.Callvirt, encGetBytes));
            }
            oil.Append(Instruction.Create(OpCodes.Ret));
            Console.WriteLine("  GetSystemSecretKey -> 고정키 \"{0}\" (반환형 {1})",
                              PRELOGIN_KEY, osp.ReturnType.Name);

            // Generic_HTTP 는 cryptoKey/initialVector 를 내부 Aes 로 "암호화해서 보관"한다
            //   set_cryptoKey(v) : field = aes.Encrypt(v)
            //   get_cryptoKey()  : return aes.Decrypt(field)
            // 이 왕복이 어긋나면 get 이 null 을 돌려주고, 이후 new Aes(null, null) 에서
            // ArgumentNullException 이 난다(/user/info/update/ 처리 중 실제로 발생).
            // 보관 암호화는 서버 통신과 무관하므로 평범한 필드 접근으로 바꾼다.
            var ghttp = mod.GetType("Generic_HTTP");
            foreach (var propName in new[] { "cryptoKey", "initialVector" })
            {
                var setter = ghttp.Methods.FirstOrDefault(m => m.Name == "set_" + propName);
                var getter = ghttp.Methods.FirstOrDefault(m => m.Name == "get_" + propName);
                if (setter == null || getter == null) continue;
                var fld = setter.Body.Instructions
                    .Where(x => x.OpCode == OpCodes.Stfld)
                    .Select(x => x.Operand as FieldReference).FirstOrDefault();
                if (fld == null) continue;

                var setB = setter.Body;
                setB.Instructions.Clear(); setB.Variables.Clear(); setB.ExceptionHandlers.Clear();
                var sp2 = setB.GetILProcessor();
                sp2.Append(Instruction.Create(OpCodes.Ldarg_0));
                sp2.Append(Instruction.Create(OpCodes.Ldarg_1));
                sp2.Append(Instruction.Create(OpCodes.Stfld, fld));
                sp2.Append(Instruction.Create(OpCodes.Ret));

                var getB = getter.Body;
                getB.Instructions.Clear(); getB.Variables.Clear(); getB.ExceptionHandlers.Clear();
                var gp2 = getB.GetILProcessor();
                gp2.Append(Instruction.Create(OpCodes.Ldarg_0));
                gp2.Append(Instruction.Create(OpCodes.Ldfld, fld));
                gp2.Append(Instruction.Create(OpCodes.Ret));
                Console.WriteLine("  Generic_HTTP.{0} -> 평문 보관 ({1})", propName, fld.Name);
            }

            // 카카오 버튼을 "로비 데이터 로딩" 트리거로 쓴다.
            // 로그인 코루틴이 끝난 뒤 눌러야 하므로 자동 연결 대신 버튼으로 분리한다.
            var socialPlay = title.Methods.First(m => m.Name == "OnClickSocialPlay");
            var loginBtn = title.Methods.First(m => m.Name == "OnClickSocialLoginButton");
            var sb = socialPlay.Body;
            sb.Instructions.Clear(); sb.Variables.Clear(); sb.ExceptionHandlers.Clear();
            var sil = sb.GetILProcessor();
            sil.Append(Instruction.Create(OpCodes.Ldarg_0));
            sil.Append(Instruction.Create(OpCodes.Call, loginBtn));
            sil.Append(Instruction.Create(OpCodes.Ret));
            Console.WriteLine("  OnClickSocialPlay -> OnClickSocialLoginButton (로비 데이터 로딩 트리거)");
        }

        // ---- (3) 게스트 모드 + 판수 제한 ----
        var spec = mod.GetType("Glocalization_Specification");
        if (spec == null) throw new Exception("Glocalization_Specification 없음");
        ConstBody(spec.Methods.First(m => m.Name == "get_enableGuestMode"),
                  Instruction.Create(OpCodes.Ldc_I4_1), "게스트 모드 = true");
        ConstBody(spec.Methods.First(m => m.Name == "get_allowGuestPlayCount"),
                  Instruction.Create(OpCodes.Ldc_I4, playCount), "판수 = " + playCount);

        asm.Write(outDll);
        Console.WriteLine("\n출력: {0} ({1:N0} bytes)", outDll, new FileInfo(outDll).Length);
        return 0;
    }

    // if (File.Exists(p)) return Encoding.UTF8.GetString(File.ReadAllBytes(p));
    static void EmitReadIfExists(ILProcessor il, VariableDefinition v, Instruction fallthrough,
        MethodReference exists, MethodReference read, MethodReference utf8,
        MethodReference getStr, MethodReference concat2, MethodReference debugLog)
    {
        il.Append(Instruction.Create(OpCodes.Ldloc, v));
        il.Append(Instruction.Create(OpCodes.Call, exists));
        il.Append(Instruction.Create(OpCodes.Brfalse, fallthrough));
        if (debugLog != null)
        {
            il.Append(Instruction.Create(OpCodes.Ldstr, "[CHADB] file "));
            il.Append(Instruction.Create(OpCodes.Ldloc, v));
            il.Append(Instruction.Create(OpCodes.Call, concat2));
            il.Append(Instruction.Create(OpCodes.Call, debugLog));
        }
        il.Append(Instruction.Create(OpCodes.Call, utf8));
        il.Append(Instruction.Create(OpCodes.Ldloc, v));
        il.Append(Instruction.Create(OpCodes.Call, read));
        il.Append(Instruction.Create(OpCodes.Callvirt, getStr));
        il.Append(Instruction.Create(OpCodes.Ret));
    }

    // 게터 본문을 "return (T)__ChaRes(bundle, asset, typeof(T));" 로 교체한다.
    // T 는 원본 본문 끝의 isinst 피연산자에서 그대로 가져온다 (GameObject / AudioClip / UIAtlas / TextAsset).
    static void RewriteGetter(TypeDefinition abm, string name, bool twoArgs,
                              MethodDefinition chaRes, MethodReference getTypeFromHandle)
    {
        var m = abm.Methods.FirstOrDefault(x => x.Name == name);
        if (m == null) { Console.WriteLine("  [건너뜀] {0} 없음", name); return; }
        var isinst = m.Body.Instructions.FirstOrDefault(x => x.OpCode == OpCodes.Isinst);
        if (isinst == null) { Console.WriteLine("  [건너뜀] {0}: isinst 없음", name); return; }
        var t = (TypeReference)isinst.Operand;
        var b = m.Body;
        b.Instructions.Clear(); b.Variables.Clear(); b.ExceptionHandlers.Clear();
        var il = b.GetILProcessor();
        il.Append(Instruction.Create(OpCodes.Ldarg_1));                       // bundle
        il.Append(Instruction.Create(OpCodes.Ldarg, twoArgs ? m.Parameters[1] : m.Parameters[0]));
        il.Append(Instruction.Create(OpCodes.Ldtoken, t));
        il.Append(Instruction.Create(OpCodes.Call, getTypeFromHandle));
        il.Append(Instruction.Create(OpCodes.Call, chaRes));
        il.Append(Instruction.Create(OpCodes.Isinst, t));
        il.Append(Instruction.Create(OpCodes.Ret));
        Console.WriteLine("  {0} -> Resources 폴백 ({1})", name, t.Name);
    }

    static void ConstBody(MethodDefinition m, Instruction load, string desc)
    {
        var b = m.Body;
        b.Instructions.Clear(); b.Variables.Clear(); b.ExceptionHandlers.Clear();
        var il = b.GetILProcessor();
        il.Append(load);
        il.Append(Instruction.Create(OpCodes.Ret));
        Console.WriteLine("  {0} -> {1}", m.Name, desc);
    }

    static TypeDefinition Def(AssemblyDefinition a, string full)
    {
        var t = a.MainModule.GetType(full);
        if (t == null) throw new Exception("타입 없음: " + full + " in " + a.Name.Name);
        return t;
    }

    static MethodDefinition Concat(TypeDefinition tString, int n)
    {
        var m = tString.Methods.FirstOrDefault(x => x.Name == "Concat"
            && x.Parameters.Count == n
            && x.Parameters.All(p => p.ParameterType.FullName == "System.String"));
        if (m == null) throw new Exception("String.Concat(" + n + " strings) 없음 (스트리핑됨)");
        return m;
    }

    static MethodReference Import(MethodDefinition m) { return mod.ImportReference(m); }
}
