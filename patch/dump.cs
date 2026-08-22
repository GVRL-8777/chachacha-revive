// 이름이 특정 접두사로 시작하는 타입들의 IL 을 찍는다(기본 __Cha).
using System;
using System.Collections.Generic;
using System.Linq;
using Mono.Cecil;
using Mono.Cecil.Cil;

class D
{
    static void Main(string[] a)
    {
        var res = new DefaultAssemblyResolver();
        res.AddSearchDirectory(a[1]);
        var m = ModuleDefinition.ReadModule(a[0], new ReaderParameters { AssemblyResolver = res });
        string want = a.Length > 2 ? a[2] : "__Cha";
        Func<TypeDefinition, IEnumerable<TypeDefinition>> all = null;
        all = x => new[] { x }.Concat(x.NestedTypes.SelectMany(y => all(y)));
        foreach (var t in m.Types.SelectMany(x => all(x)))
        {
            foreach (var me in t.Methods)
            {
                if (!me.Name.Contains(want)) continue;
                Console.WriteLine("=== " + t.FullName + "::" + me.Name);
                if (!me.HasBody) { Console.WriteLine("   (본문 없음)"); continue; }
                foreach (var ins in me.Body.Instructions)
                    Console.WriteLine("   " + ins);
            }
        }
    }
}
