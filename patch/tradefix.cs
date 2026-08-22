// 되팔기 팝업(TradeCarPop)을 살린다.
//
// 중국판은 이 기능을 소스 수준에서 들어냈다. 스위치만 켜면 탭은 뜨지만,
// TradeCarPop.m_CarList (Dictionary) 를 **아무 데서도 생성하지 않아**
// Build() 의 첫 Add 에서 널참조로 죽는다. 생성자에 생성 코드를 붙인다.
// (필드 초기화는 원래 .ctor 에 들어가는 자리라, 여기에 넣는 게 정석이다)
//
// 사용법: tradefix.exe <in.dll> <out.dll>
using System;
using System.Linq;
using Mono.Cecil;
using Mono.Cecil.Cil;

static class TF
{
    static int Main(string[] args)
    {
        var mod = ModuleDefinition.ReadModule(args[0]);
        var t = mod.GetTypes().FirstOrDefault(x => x.Name == "TradeCarPop");
        if (t == null) { Console.WriteLine("TradeCarPop 없음"); return 1; }

        int n = 0;
        var ctor = t.Methods.First(m => m.Name == ".ctor");
        var il = ctor.Body.GetILProcessor();

        foreach (var f in t.Fields.Where(f => !f.IsStatic &&
                     f.FieldType is GenericInstanceType))
        {
            var git = (GenericInstanceType)f.FieldType;
            var name = git.ElementType.Name;
            if (name != "Dictionary`2" && name != "List`1") continue;

            // 매개변수 없는 생성자 참조. 닫힌 제네릭 타입을 그대로 선언타입으로
            // 쓴다(인자가 없으니 제네릭 인자 치환 문제가 생기지 않는다).
            var cref = new MethodReference(".ctor", mod.TypeSystem.Void, git)
            { HasThis = true };

            // ret 앞에 붙인다 (본문 중간 삽입을 피하는 안전한 방식)
            var ret = ctor.Body.Instructions.Last();
            il.InsertBefore(ret, Instruction.Create(OpCodes.Ldarg_0));
            il.InsertBefore(ret, Instruction.Create(OpCodes.Newobj, cref));
            il.InsertBefore(ret, Instruction.Create(OpCodes.Stfld, f));
            Console.WriteLine("  생성자에 초기화 추가: " + f.Name + " (" + git.FullName + ")");
            n++;
        }
        if (ctor.Body.MaxStackSize < 2) ctor.Body.MaxStackSize = 2;

        // m_TitleName 은 프리팹에 직렬화되지 않은 필드라 런타임에 늘 널이다.
        // Build() 첫 줄이 그 라벨의 text 를 건드려 팝업이 열리자마자 죽는다.
        // 그 한 문장(ldarg.0; ldfld; get_instance; ldstr; Get; set_text)을 들어낸다.
        // 제목은 프리팹에 구워진 기본 글자가 그대로 보인다.
        var build = t.Methods.FirstOrDefault(m => m.Name == "Build");
        if (build != null && build.Body.Instructions.Count > 6)
        {
            var ins = build.Body.Instructions;
            var fld = ins[1].Operand as FieldReference;
            if (ins[0].OpCode == OpCodes.Ldarg_0 && fld != null && fld.Name == "m_TitleName")
            {
                var bil = build.Body.GetILProcessor();
                for (int k = 0; k < 6; k++) bil.Remove(build.Body.Instructions[0]);
                Console.WriteLine("  Build() 의 널 제목라벨 문장 제거");
            }
            else Console.WriteLine("  Build() 첫 문장이 예상과 다르다 — 건너뛴다");
        }

        if (n == 0) { Console.WriteLine("초기화할 필드가 없다"); return 1; }
        mod.Write(args[1]);
        Console.WriteLine("되팔기 팝업 " + n + "곳 초기화 -> " + args[1]);
        return 0;
    }
}
