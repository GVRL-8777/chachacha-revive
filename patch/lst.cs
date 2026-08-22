// 타입의 public 메서드 목록을 인자 타입까지 붙여 찍는다.
using System; using System.Linq; using Mono.Cecil;
class L { static void Main(string[] a){
  var m = ModuleDefinition.ReadModule(a[0]);
  var t = m.GetTypes().FirstOrDefault(x => x.FullName == a[1]);
  if (t == null) { Console.WriteLine("no type"); return; }
  foreach (var x in t.Methods.Where(x=>x.IsPublic))
    Console.WriteLine("  " + x.Name + "(" + string.Join(",",
      x.Parameters.Select(p=>p.ParameterType.Name).ToArray()) + ")");
}}
