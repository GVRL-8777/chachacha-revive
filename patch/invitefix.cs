// 초대 목록을 소셜 플랫폼 없이도 채운다.
//
// RankManager.CreateInvite 는 초대 대상을
//   SocialPlatformDataBase.instance.friendDataList.noneAppFriendList
// 에서만 가져온다. 카카오·넷마블 SDK 가 채워 주는 목록이라 사설 서버에서는
// 영원히 비어 있고, 그래서 초대 화면이 빈 판으로 뜬다.
//
// get_noneAppFriendList 를 통째로 다시 써서, 목록이 비어 있을 때만
// 가짜 이웃 몇을 채워 넣는다. 이미 값이 있으면 손대지 않는다.
//
// 사용법: invitefix.exe <in.dll> <out.dll>
using System;
using System.Linq;
using Mono.Cecil;
using Mono.Cecil.Cil;

static class IF
{
    static readonly string[] NAMES = {
        "옆집 김씨", "택배 기사님", "동네 형", "단골 정비사", "우리 사장님",
    };

    static int Main(string[] args)
    {
        string inDll = args[0], outDll = args[1];
        var mod = ModuleDefinition.ReadModule(inDll);

        var listType = mod.GetTypes().First(
            t => t.Name == "SocialPlatformFriendDataList");
        var fld = listType.Fields.First(f => f.Name == "m_NoneAppFriendList");
        var gi = (GenericInstanceType)fld.FieldType;
        var elem = gi.GenericArguments[0];   // SocialPlatformNoneAppFriendData
        var elemDef = elem.Resolve();          // SocialPlatformNoneAppFriendData
        var friendDef = elemDef.BaseType.Resolve();   // SocialPlatformFriendData
        var userDef = friendDef.BaseType.Resolve();   // UserDataElement

        // List<T> 의 Add / get_Count 를 제네릭 인스턴스에 맞춰 만든다.
        // 매개변수 타입은 **정의 쪽의 제네릭 인자(!0)** 를 그대로 써야 한다.
        // 실제 타입으로 바꿔 넣으면 런타임이 메서드를 못 찾는다.
        var listDef = gi.ElementType.Resolve();
        var add = OnInstance(mod, listDef.Methods.First(
            m => m.Name == "Add" && m.Parameters.Count == 1), gi);
        var count = OnInstance(mod, listDef.Methods.First(
            m => m.Name == "get_Count" && m.Parameters.Count == 0), gi);

        var ctor = elemDef.Methods.First(m => m.IsConstructor && m.Parameters.Count == 0);
        // 상위 클래스의 필드는 private 이라 밖에서 직접 못 쓴다(FieldAccessException).
        // 공개 프로퍼티 setter 로 넣는다.
        var fNick = mod.ImportReference(userDef.Methods.First(m => m.Name == "set_nickName"));
        var fUid = mod.ImportReference(userDef.Methods.First(m => m.Name == "set_userID"));
        var fImg = mod.ImportReference(userDef.Methods.First(m => m.Name == "set_profileImageUrl"));
        var fGsid = mod.ImportReference(friendDef.Methods.First(m => m.Name == "set_gameServerUserID"));
        var fDev = mod.ImportReference(friendDef.Methods.First(m => m.Name == "set_isSupportedDevice"));
        var fBlk = mod.ImportReference(friendDef.Methods.First(m => m.Name == "set_isMessageBlocked"));
        var fSent = mod.ImportReference(friendDef.Methods.First(m => m.Name == "set_isSentInvitMessage"));

        var getter = listType.Methods.First(m => m.Name == "get_noneAppFriendList");
        var body = getter.Body;
        body.Instructions.Clear();
        body.Variables.Clear();
        body.ExceptionHandlers.Clear();
        var vList = new VariableDefinition(gi);
        var vOne = new VariableDefinition(elem);
        body.Variables.Add(vList);
        body.Variables.Add(vOne);
        body.InitLocals = true;
        var il = body.GetILProcessor();

        var done = Instruction.Create(OpCodes.Ldloc, vList);
        il.Append(Instruction.Create(OpCodes.Ldarg_0));
        il.Append(Instruction.Create(OpCodes.Ldfld, fld));
        il.Append(Instruction.Create(OpCodes.Stloc, vList));
        il.Append(Instruction.Create(OpCodes.Ldloc, vList));
        il.Append(Instruction.Create(OpCodes.Brfalse, done));   // 널이면 그대로
        il.Append(Instruction.Create(OpCodes.Ldloc, vList));
        il.Append(Instruction.Create(OpCodes.Callvirt, count));
        il.Append(Instruction.Create(OpCodes.Brtrue, done));    // 이미 있으면 그대로

        for (int i = 0; i < NAMES.Length; i++)
        {
            string uid = "guest" + (i + 1);
            il.Append(Instruction.Create(OpCodes.Newobj, ctor));
            il.Append(Instruction.Create(OpCodes.Stloc, vOne));
            Set(il, vOne, fNick, NAMES[i]);
            Set(il, vOne, fUid, uid);
            Set(il, vOne, fGsid, uid);
            Set(il, vOne, fImg, "");
            SetBool(il, vOne, fDev, true);
            SetBool(il, vOne, fBlk, false);
            SetBool(il, vOne, fSent, false);
            il.Append(Instruction.Create(OpCodes.Ldloc, vList));
            il.Append(Instruction.Create(OpCodes.Ldloc, vOne));
            il.Append(Instruction.Create(OpCodes.Callvirt, add));
        }

        il.Append(done);
        il.Append(Instruction.Create(OpCodes.Ret));
        body.MaxStackSize = 4;

        mod.Write(outDll);
        Console.WriteLine("초대 목록에 이웃 " + NAMES.Length + "명 채움 -> " + outDll);
        return 0;
    }

    // 제네릭 인스턴스 타입 위의 메서드 참조를 만든다
    static MethodReference OnInstance(ModuleDefinition mod, MethodDefinition def,
                                      GenericInstanceType inst)
    {
        var r = new MethodReference(def.Name, def.ReturnType, inst)
        {
            HasThis = def.HasThis,
            ExplicitThis = def.ExplicitThis,
            CallingConvention = def.CallingConvention,
        };
        foreach (var p in def.Parameters)
            r.Parameters.Add(new ParameterDefinition(p.ParameterType));
        foreach (var g in def.GenericParameters)
            r.GenericParameters.Add(new GenericParameter(g.Name, r));
        return mod.ImportReference(r);
    }

    static void Set(ILProcessor il, VariableDefinition v, MethodReference setter, string s)
    {
        il.Append(Instruction.Create(OpCodes.Ldloc, v));
        il.Append(Instruction.Create(OpCodes.Ldstr, s));
        il.Append(Instruction.Create(OpCodes.Callvirt, setter));
    }

    static void SetBool(ILProcessor il, VariableDefinition v, MethodReference setter, bool b)
    {
        il.Append(Instruction.Create(OpCodes.Ldloc, v));
        il.Append(Instruction.Create(b ? OpCodes.Ldc_I4_1 : OpCodes.Ldc_I4_0));
        il.Append(Instruction.Create(OpCodes.Callvirt, setter));
    }
}
