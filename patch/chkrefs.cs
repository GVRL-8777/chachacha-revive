// ChaLocal.dll 이 부르는 모든 바깥 멤버가 게임의 Managed 폴더 안에
// **실제로 있는지** 검사한다. 전체 프레임워크로 컴파일한 뒤 Unity 의
// 축소된 mscorlib 위에서 돌릴 때 나는 MissingMethodException 을 미리 잡는다.
using System; using System.Linq; using Mono.Cecil;
class K {
  static int Main(string[] a){
    var res = new DefaultAssemblyResolver();
    res.AddSearchDirectory(a[1]);
    var m = ModuleDefinition.ReadModule(a[0],
              new ReaderParameters { AssemblyResolver = res });
    int bad = 0;
    foreach (var mr in m.GetMemberReferences()) {
      var dt = mr.DeclaringType;
      if (dt == null) continue;
      TypeDefinition td = null;
      try { td = dt.Resolve(); } catch {}
      if (td == null) { Console.WriteLine("MISS type   " + dt.FullName); bad++; continue; }
      bool ok;
      var meth = mr as MethodReference;
      // 제네릭 인스턴스는 매개변수 이름이 !0 / TKey 로 갈려 이름만 맞춘다
      bool generic = dt is GenericInstanceType;
      if (meth != null)
        ok = td.Methods.Any(x => x.Name == meth.Name
             && x.Parameters.Count == meth.Parameters.Count
             && (generic || Enumerable.Range(0, x.Parameters.Count).All(i =>
                  x.Parameters[i].ParameterType.FullName
                  == meth.Parameters[i].ParameterType.FullName)));
      else
        ok = td.Fields.Any(x => x.Name == mr.Name);
      if (!ok) { Console.WriteLine("MISS member " + mr.FullName); bad++; }
    }
    Console.WriteLine(bad == 0 ? "모든 참조가 풀린다." : ("풀리지 않는 참조 " + bad + "개"));
    return bad == 0 ? 0 : 1;
  }
}
