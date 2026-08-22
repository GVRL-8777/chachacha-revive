// 타입의 필드를 메타데이터 토큰·타입·static 여부까지 찍는다.
using System; using System.Linq; using Mono.Cecil;
static class FI {
  static int Main(string[] a){
    var mod = ModuleDefinition.ReadModule(a[0]);
    var t = mod.GetTypes().First(x=>x.Name==a[1]);
    foreach(var f in t.Fields)
      Console.WriteLine("{0:X8}  {1,-28} {2}  static={3}",
        f.MetadataToken.ToUInt32(), f.Name, f.FieldType.FullName, f.IsStatic);
    return 0;
  }
}
