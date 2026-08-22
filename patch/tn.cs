// 이름에 특정 낱말이 든 타입을 찾는다.
using System; using System.Linq; using Mono.Cecil;
class TN { static void Main(string[] a){
  var m = ModuleDefinition.ReadModule(a[0]);
  foreach (var t in m.Types.Where(x => x.Name.ToLower().Contains(a[1].ToLower())))
    Console.WriteLine("  " + t.FullName);
}}
