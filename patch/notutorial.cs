// 중국 배포판에만 있는 '도움말 팝업' 네 개를 띄우지 않는다.
//
//   UI/Prefabs/MyCarHouseTutorialPopup   내차고
//   UI/Prefabs/ShopTutorialPopup         상점
//   UI/Prefabs/DriverTutorialPopup       캐릭터
//   UI/Prefabs/GiftTutorialPopup         선물
//
// 이 프리팹들은 한국판·카카오판에는 아예 없다(중국 퍼블리셔가 덧붙인 것이다).
// 안내 문구도 그림도 전부 중국어로 구워져 있어 번역으로는 못 지운다.
//
// 팝업을 만드는 Create() 를 비우면 PopupResultCheck 코루틴이 isRecive 를
// 영원히 기다려 팝업 대기열이 멈춘다. 그래서 대신 코루틴
// <PopTutorial>c__IteratorNN::MoveNext 를 통째로
//     this.$PC = -1;  return false;
// 로 바꾼다. 조건 검사가 실패했을 때 원래 타던 길과 같아 안전하다.
//
// 사용법: notutorial.exe <in.dll> <out.dll>
using System;
using System.Linq;
using Mono.Cecil;
using Mono.Cecil.Cil;

static class NT
{
    // 각 팝업을 띄우는 코루틴 이름
    static readonly string[] COROUTINES = {
        "<PopTutorial>", "<PopShopTutorial>", "<PopDriverTutorial>",
        "<PopGiftTutorial>",
        // 레이스 끝나고 뜨는 "对结果不满意吗? 升级车辆更容易拿高分!" 광고.
        // 역시 중국판 전용이고 글자가 그림에 구워져 있다.
        "<PopUpgradeMessage>",
    };

    static int Main(string[] args)
    {
        string inDll = args[0], outDll = args[1];
        var mod = ModuleDefinition.ReadModule(inDll);

        int done = 0;
        foreach (var t in mod.GetTypes())
        {
            if (!COROUTINES.Any(c => t.Name.StartsWith(c + "c__Iterator")))
                continue;
            var mv = t.Methods.FirstOrDefault(m => m.Name == "MoveNext");
            if (mv == null || !mv.HasBody) continue;

            // $PC 필드는 int 하나뿐이다(나머지는 object/참조).
            var pc = t.Fields.FirstOrDefault(
                f => f.FieldType.FullName == "System.Int32" && f.Name.Contains("PC"));
            if (pc == null)
                pc = t.Fields.FirstOrDefault(f => f.FieldType.FullName == "System.Int32");
            if (pc == null) { Console.WriteLine("  $PC 못 찾음: " + t.Name); continue; }

            var body = mv.Body;
            body.Instructions.Clear();
            body.Variables.Clear();
            body.ExceptionHandlers.Clear();
            var il = body.GetILProcessor();
            il.Append(Instruction.Create(OpCodes.Ldarg_0));
            il.Append(Instruction.Create(OpCodes.Ldc_I4_M1));
            il.Append(Instruction.Create(OpCodes.Stfld, pc));
            il.Append(Instruction.Create(OpCodes.Ldc_I4_0));
            il.Append(Instruction.Create(OpCodes.Ret));
            body.MaxStackSize = 2;
            Console.WriteLine("  건너뜀: " + t.Name + " (" + pc.Name + ")");
            done++;
        }

        if (done == 0) { Console.WriteLine("아무것도 못 고쳤다"); return 1; }
        mod.Write(outDll);
        Console.WriteLine("중국어 도움말 팝업 " + done + "개 끔 -> " + outDll);
        return 0;
    }
}
