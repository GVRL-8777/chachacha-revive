// 중국판이 꺼 둔 모드를 켠다.
//
// Glocalization_Specification 의 기능 스위치들은 생성자에서 아예 대입되지
// 않아 전부 false 다. ContentsEnableController.IsEanble 이 이 값만 보고
// 허들·그랑프리·대전·글로벌랭킹 진입을 막는다.
// 게터 본문을 `ldc.i4.1; ret` 로 통째로 갈아 끼우면 켜진다(안전한 방식).
//
// 자산은 다 들어 있다. 허들만 해도 hurdle/ 40개와 127KB 짜리 hurdledb 가 있다.
// 다만 서버 응답이 따라와야 하고, 그랑프리·글로벌랭킹은 죽은 웹뷰를 부른다.
// 그래서 켤 것만 인자로 받는다.
//
// 사용법: modesfix.exe <in.dll> <out.dll> <켤것,켤것,...>
//   이름: hurdle, globalranking, tradecar, grandprix, invite, dummy
using System;
using System.Collections.Generic;
using System.Linq;
using Mono.Cecil;
using Mono.Cecil.Cil;

static class MF
{
    static readonly Dictionary<string, string> GETTER = new Dictionary<string, string>
    {
        { "hurdle", "get_enableHurdleMode" },
        { "globalranking", "get_enableGlobalRanking" },
        { "tradecar", "get_enableTradeCarEvent" },
        { "grandprix", "get_enableGrandPrix" },
        { "invite", "get_enableInviteFriendEvent" },
        { "dummy", "get_enableDummyUser" },
    };

    static int Main(string[] args)
    {
        var mod = ModuleDefinition.ReadModule(args[0]);
        var want = (args.Length > 2 ? args[2] : "hurdle")
            .Split(',').Select(x => x.Trim().ToLower()).Where(x => x.Length > 0);

        var spec = mod.GetTypes().First(t => t.Name == "Glocalization_Specification");
        int n = 0;
        foreach (var key in want)
        {
            if (!GETTER.ContainsKey(key))
            {
                Console.WriteLine("  모르는 이름: " + key);
                continue;
            }
            var m = spec.Methods.FirstOrDefault(x => x.Name == GETTER[key]);
            if (m == null) { Console.WriteLine("  게터 없음: " + GETTER[key]); continue; }
            var body = m.Body;
            body.Instructions.Clear();
            body.Variables.Clear();
            body.ExceptionHandlers.Clear();
            var il = body.GetILProcessor();
            il.Append(Instruction.Create(OpCodes.Ldc_I4_1));
            il.Append(Instruction.Create(OpCodes.Ret));
            body.MaxStackSize = 1;
            Console.WriteLine("  켬: " + key + " (" + GETTER[key] + ")");
            n++;
        }
        // 스위치만으로 안 열리는 것들: ContentsEnableController 의 판정 함수가
        // 스위치 AND 이벤트DB(isEventActive) 를 본다. 중국판은 이벤트DB 빌더가
        // 통째로 비어 있어(_BuildEventTradeCarDataBase 가 ret 하나) 영영 false 다.
        // 판정 함수 본문을 통째로 참으로 갈아 끼운다.
        var FORCE = new Dictionary<string, string>
        {
            { "tradecar", "_IsEnableTradeCar" },
        };
        var cec = mod.GetTypes().FirstOrDefault(t => t.Name == "ContentsEnableController");
        if (cec != null)
        {
            foreach (var key in (args.Length > 2 ? args[2] : "hurdle")
                     .Split(',').Select(x => x.Trim().ToLower()))
            {
                if (!FORCE.ContainsKey(key)) continue;
                var f = cec.Methods.FirstOrDefault(x => x.Name == FORCE[key]);
                if (f == null) { Console.WriteLine("  판정함수 없음: " + FORCE[key]); continue; }
                var fb = f.Body;
                fb.Instructions.Clear();
                fb.Variables.Clear();
                fb.ExceptionHandlers.Clear();
                var fil = fb.GetILProcessor();
                fil.Append(Instruction.Create(OpCodes.Ldc_I4_1));
                fil.Append(Instruction.Create(OpCodes.Ret));
                fb.MaxStackSize = 1;
                Console.WriteLine("  이벤트DB 조건 무시: " + FORCE[key]);
            }
        }

        if (n == 0) { Console.WriteLine("켠 것이 없다"); return 1; }
        mod.Write(args[1]);
        Console.WriteLine("모드 " + n + "개 켬 -> " + args[1]);
        return 0;
    }
}
