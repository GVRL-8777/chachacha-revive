// 8.apk(v1.3.1) 전용 패처.
//
// 카카오 플랫폼 폐쇄로 로그인이 불가능하다. 다행히 개발자용
//   static HTTP::LoginForEditor(GameObject, OnRequest, bool)
// 가 남아 있어 userId/accessToken 을 빈 문자열로 /user/auth/login 에 보낸다.
//
// 연결 방식:
//   1) Title::CompletedKakao 를 LoginForEditor 호출로 갈아끼운다.
//      (this.gameObject 를 콜백 대상으로 넘겨야 LoginCompleteServer 가 Title 에 도달한다)
//   2) Title::FailedKakaoLogin / SucceedKakaoLogin 을 CompletedKakao 로 돌린다.
//      카카오 SDK 가 실패 콜백을 주므로, 버튼을 누르면 결국 우리 로그인이 돈다.
//
// 주의: HTTP::Login / LoginForEditor 는 **정적 메서드**다.
//       HTTP.instance 를 스택에 올리면 스택 불균형으로 Mono 가
//       'Assertion at object.c:1710, condition `class` not met' 로 죽는다.
using System; using System.Linq; using Mono.Cecil; using Mono.Cecil.Cil;
static class P {
  static int Main(string[] a) {
    var r = new DefaultAssemblyResolver(); r.AddSearchDirectory(a[2]);
    var asm = AssemblyDefinition.ReadAssembly(a[0], new ReaderParameters{AssemblyResolver=r});
    var mod = asm.MainModule;
    var ue = r.Resolve(mod.AssemblyReferences.First(x => x.Name == "UnityEngine"));

    var http     = mod.GetType("HTTP");
    var httpRecv = mod.GetType("HTTP_Recv");
    var title    = mod.GetType("Title");
    var onReq    = http.NestedTypes.First(t => t.Name == "OnRequest");

    var loginEd   = http.Methods.First(m => m.Name == "LoginForEditor");
    var recvInst  = httpRecv.Methods.First(m => m.Name == "get_instance");
    var waitLogin = httpRecv.Methods.First(m => m.Name == "WaitForLogin");
    var onReqCtor = onReq.Methods.First(m => m.IsConstructor);
    var getGO = mod.ImportReference(ue.MainModule.GetType("UnityEngine.Component")
                    .Methods.First(m => m.Name == "get_gameObject"));

    Console.WriteLine("  LoginForEditor 정적여부: {0}", loginEd.IsStatic);

    // 1) CompletedKakao -> LoginForEditor
    var ck = title.Methods.First(m => m.Name == "CompletedKakao");
    var b = ck.Body;
    b.Instructions.Clear(); b.Variables.Clear(); b.ExceptionHandlers.Clear();
    var il = b.GetILProcessor();
    il.Append(Instruction.Create(OpCodes.Ldarg_0));
    il.Append(Instruction.Create(OpCodes.Call, getGO));          // [go]
    il.Append(Instruction.Create(OpCodes.Call, recvInst));       // [go, recv]
    il.Append(Instruction.Create(OpCodes.Ldftn, waitLogin));
    il.Append(Instruction.Create(OpCodes.Newobj, onReqCtor));    // [go, cb]
    il.Append(Instruction.Create(OpCodes.Ldc_I4_1));             // register = true
    il.Append(Instruction.Create(loginEd.IsStatic ? OpCodes.Call : OpCodes.Callvirt, loginEd));
    il.Append(Instruction.Create(OpCodes.Ret));
    Console.WriteLine("  Title::CompletedKakao -> HTTP::LoginForEditor");

    // 2) 카카오 콜백들을 CompletedKakao 로
    foreach (var nm in new[] { "FailedKakaoLogin", "SucceedKakaoLogin", "AreadyKakaoLogin" }) {
      var m2 = title.Methods.FirstOrDefault(x => x.Name == nm);
      if (m2 == null) continue;
      var b2 = m2.Body;
      b2.Instructions.Clear(); b2.Variables.Clear(); b2.ExceptionHandlers.Clear();
      var il2 = b2.GetILProcessor();
      il2.Append(Instruction.Create(OpCodes.Ldarg_0));
      il2.Append(Instruction.Create(OpCodes.Call, ck));
      il2.Append(Instruction.Create(OpCodes.Ret));
      Console.WriteLine("  Title::{0} -> CompletedKakao", nm);
    }

    asm.Write(a[1]);
    Console.WriteLine("출력: " + a[1]);
    return 0;
  }
}
