// 트로피 결제창을 원화로 고치고, 결제를 그 자리에서 끝낸다.
//
// 1) 가격 표시
//    중국판은 통화가 RMB(ePriceCurrency=3)로 잡혀 있다. 한국어 표에서
//    PriceCurrency_RMB 가 "원" 이라 "원4" 처럼 기호가 앞에 붙어 나온다.
//    ShopTrophy.Awake 는 통화가 KRW(0) 일 때만 Concat(가격, 기호) 순서로
//    쓰므로, 통화를 0 으로 바꾸면 "990원" 이 된다.
//    가격 숫자도 한국판 7.7.0 의 원화가로 갈아 끼운다(같은 트로피 수 기준).
//    전부 **피연산자만** 바꾸므로 명령 길이도 분기도 그대로다.
//
// 2) 즉시 결제
//    BillingPlatformFactory_NetmarbleS360.CreatePlatform 이 만드는 실물
//    결제 플랫폼을 BillingPlatform_Editor 로 바꾼다. 이 구현은 Purchase 를
//    부르는 즉시 성공 응답을 돌려주므로 스토어 창도, 로딩도 없다.
//    앞뒤의 서버 통신(raven/register -> raven/confirm)은 그대로 남아
//    트로피 지급은 서버가 한다.
//
// 사용법: shopfix.exe <in.dll> <out.dll>
using System;
using System.Collections.Generic;
using System.Linq;
using Mono.Cecil;
using Mono.Cecil.Cil;

static class SF
{
    // 상품코드 -> 원화가 (한국판 7.7.0 기준, 10개짜리는 비례해서 990원)
    static readonly Dictionary<string, float> WON = new Dictionary<string, float>
    {
        { "chacha_CN_001", 990f },    // 트로피 10
        { "chacha_CN_002", 2990f },   // 35
        { "chacha_CN_003", 4990f },   // 60
        { "chacha_CN_004", 9990f },   // 130
        { "chacha_CN_005", 29990f },  // 420
        { "chacha_CN_006", 49990f },  // 750
        { "chacha_CN_008", 2990f },   // 60 (할인)
        { "chacha_CN_009", 9900f },   // 170
    };

    static int Main(string[] args)
    {
        var mod = ModuleDefinition.ReadModule(args[0]);

        // --- 1. 통화·가격 ---------------------------------------------------
        var builder = mod.GetTypes().First(t => t.Name == "StorePayDataBaseBuilder");
        var build = builder.Methods.First(m => m.Name == "Build");
        var ins = build.Body.Instructions;
        string code = null;
        int prices = 0, currencies = 0;
        for (int i = 0; i < ins.Count; i++)
        {
            var op = ins[i];
            var lit = op.Operand as string;
            if (op.OpCode == OpCodes.Ldstr && lit != null && lit.StartsWith("chacha"))
                code = lit;

            // AddPriceData(통화, 가격) 의 통화 인자, 그리고 set_priceCurrencyType 인자
            if (op.OpCode == OpCodes.Ldc_I4_3)
            {
                bool isCurrency = false;
                if (i + 1 < ins.Count)
                {
                    if (ins[i + 1].OpCode == OpCodes.Ldc_R4) isCurrency = true;
                    var mr = ins[i + 1].Operand as MethodReference;
                    if (mr != null && mr.Name == "set_priceCurrencyType") isCurrency = true;
                }
                if (isCurrency) { op.OpCode = OpCodes.Ldc_I4_0; currencies++; }
            }

            if (op.OpCode == OpCodes.Ldc_R4 && code != null && WON.ContainsKey(code))
            {
                Console.WriteLine("  " + code + " : " + op.Operand + " -> " + WON[code] + "원");
                op.Operand = WON[code];
                prices++;
            }
        }
        Console.WriteLine("통화 " + currencies + "곳 KRW 로, 가격 " + prices + "개 원화로");

        // --- 2. 결제 플랫폼 -------------------------------------------------
        var editor = mod.GetTypes().First(t => t.Name == "BillingPlatform_Editor");
        var ector = editor.Methods.First(m => m.IsConstructor && m.Parameters.Count == 0);
        var factory = mod.GetTypes().First(
            t => t.Name == "BillingPlatformFactory_NetmarbleS360");
        var create = factory.Methods.First(m => m.Name == "CreatePlatform");
        var body = create.Body;
        body.Instructions.Clear();
        body.Variables.Clear();
        body.ExceptionHandlers.Clear();
        var il = body.GetILProcessor();
        il.Append(Instruction.Create(OpCodes.Newobj, ector));
        il.Append(Instruction.Create(OpCodes.Ret));
        body.MaxStackSize = 1;
        Console.WriteLine("결제 플랫폼 -> BillingPlatform_Editor (즉시 성공)");

        mod.Write(args[1]);
        Console.WriteLine("상점 보정 -> " + args[1]);
        return 0;
    }
}
