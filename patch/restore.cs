// UnityEngine.dll 에서 바이트코드 스트리퍼가 잘라낸 메서드 선언을 되살린다.
//
// 네이티브(libunity.so)에는 구현이 그대로 남아 있고 icall 테이블에도 등록돼 있다.
// (libunity.so 안에 "UnityEngine.Texture2D::LoadImage" 같은 문자열이 실재)
// 따라서 extern + InternalCall 선언만 다시 붙이면 Mono 가 JIT 때 연결해 준다.
//
// 사용법: restore.exe <UnityEngine.dll> <출력.dll>
using System;
using System.Linq;
using Mono.Cecil;

class R
{
    static ModuleDefinition mod;

    static TypeDefinition T(string full)
    {
        var t = mod.Types.FirstOrDefault(x => x.FullName == full);
        if (t == null) Console.WriteLine("  [경고] 타입 없음: " + full);
        return t;
    }

    // extern(InternalCall) 메서드를 추가한다. 이미 있으면 건너뛴다.
    static void AddIcall(TypeDefinition t, string name, TypeReference ret,
                         bool isStatic, params TypeReference[] ps)
    {
        if (t == null) return;
        if (t.Methods.Any(m => m.Name == name && m.Parameters.Count == ps.Length))
        {
            Console.WriteLine("  (이미 있음) " + t.Name + "::" + name);
            return;
        }
        var attrs = MethodAttributes.Public | MethodAttributes.HideBySig;
        if (isStatic) attrs |= MethodAttributes.Static;
        var m2 = new MethodDefinition(name, attrs, ret);
        m2.IsRuntime = false;
        m2.IsInternalCall = true;      // MethodImplOptions.InternalCall
        m2.IsManaged = true;
        m2.HasThis = !isStatic;
        for (int i = 0; i < ps.Length; i++)
            m2.Parameters.Add(new ParameterDefinition("a" + i, ParameterAttributes.None, ps[i]));
        t.Methods.Add(m2);
        Console.WriteLine("  복원: " + t.Name + "::" + name + "(" +
                          string.Join(",", ps.Select(x => x.Name).ToArray()) + ")");
    }

    static void Main(string[] a)
    {
        var asm = AssemblyDefinition.ReadAssembly(a[0]);
        mod = asm.MainModule;
        var ts = mod.TypeSystem;

        var tex2d = T("UnityEngine.Texture2D");
        var texBase = T("UnityEngine.Texture");
        var bundle = T("UnityEngine.AssetBundle");
        var byteArr = new ArrayType(ts.Byte);

        // --- Texture2D ---
        // Unity 4 의 Texture2D 는 ctor 가 Internal_Create 를 호출하는 구조다.
        AddIcall(tex2d, "Internal_Create", ts.Boolean, true,
                 tex2d, ts.Int32, ts.Int32, mod.ImportReference(T("UnityEngine.TextureFormat")) ?? (TypeReference)ts.Int32,
                 ts.Boolean, ts.Boolean);
        AddIcall(tex2d, "LoadImage", ts.Boolean, false, byteArr);
        AddIcall(tex2d, "Apply", ts.Void, false, ts.Boolean, ts.Boolean);

        // --- AssetBundle ---
        // CreateFromMemory 는 AssetBundleCreateRequest 를 돌려주지만,
        // 동기 로딩용 CreateFromMemoryImmediate 가 있으면 그쪽이 훨씬 쓰기 쉽다.
        AddIcall(bundle, "CreateFromMemoryImmediate", bundle, true, byteArr);
        AddIcall(bundle, "Load", mod.ImportReference(T("UnityEngine.Object")) ?? (TypeReference)ts.Object,
                 false, ts.String, mod.ImportReference(typeof(Type)));
        AddIcall(bundle, "Unload", ts.Void, false, ts.Boolean);

        asm.Write(a[1]);
        Console.WriteLine("출력: " + a[1]);
    }
}
