// 지목한 타입들의 메서드·필드 개수와 목록을 요약한다.
using System; using System.Linq; using Mono.Cecil;
class T {
  static void Main(string[] a) {
    var asm = AssemblyDefinition.ReadAssembly(a[0]);
    foreach (var name in a.Skip(1)) {
      var t = asm.MainModule.Types.FirstOrDefault(x => x.FullName == name);
      if (t == null) { Console.WriteLine(name + " : 타입 없음"); continue; }
      Console.WriteLine("== " + name + " : 메서드 " + t.Methods.Count + "개, 필드 " + t.Fields.Count + "개");
      foreach (var m in t.Methods.Take(40))
        Console.WriteLine("   " + m.Name + "(" + string.Join(",", m.Parameters.Select(p => p.ParameterType.Name).ToArray()) + ")");
    }
  }
}
