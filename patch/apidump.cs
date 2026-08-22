// NetQuery / NetRecive 클래스에 중첩된 eType 열거형을 전부 덤프한다.
// 이 게임은 JSON 키를 ((eType)i).ToString() 으로 만들기 때문에
// 열거형 멤버 목록이 곧 각 엔드포인트의 요청/응답 스키마다.
//
// 사용법: apidump.exe <Assembly-CSharp.dll> <managed폴더>  > api_schema.txt
using System;
using System.IO;
using System.Linq;
using Mono.Cecil;

static class ApiDump
{
    static void Walk(TypeDefinition t, string prefix, TextWriter w)
    {
        foreach (var n in t.NestedTypes)
        {
            if (n.IsEnum)
            {
                var members = n.Fields.Where(f => f.Name != "value__").Select(f => f.Name).ToArray();
                if (members.Length > 0)
                    w.WriteLine("{0}{1}.{2} = {3}", prefix, t.FullName, n.Name, string.Join(", ", members));
            }
            Walk(n, prefix, w);
        }
    }

    static int Main(string[] args)
    {
        var resolver = new DefaultAssemblyResolver();
        resolver.AddSearchDirectory(args[1]);
        var asm = AssemblyDefinition.ReadAssembly(args[0],
            new ReaderParameters { AssemblyResolver = resolver });
        var w = Console.Out;
        foreach (var t in asm.MainModule.Types.OrderBy(x => x.FullName))
        {
            // 엔드포인트 경로 리터럴도 같이 뽑아 두면 매칭이 쉽다
            string path = null;
            foreach (var m in t.Methods)
            {
                if (!m.HasBody) continue;
                foreach (var i in m.Body.Instructions)
                {
                    var s = i.Operand as string;
                    if (s != null && s.Length > 2 && s[0] == '/' && s[s.Length - 1] == '/')
                    { path = s; break; }
                }
                if (path != null) break;
            }
            var hasEnum = t.NestedTypes.Any(n => n.IsEnum);
            if (path != null || hasEnum)
            {
                if (path != null) w.WriteLine("### {0}   PATH {1}", t.FullName, path);
                else w.WriteLine("### {0}", t.FullName);
                Walk(t, "    ", w);
                w.WriteLine();
            }
        }
        return 0;
    }
}
