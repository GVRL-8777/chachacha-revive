// 지목한 열거형 하나의 값 목록을 찍는다.
using System; using System.Linq; using Mono.Cecil;
class E { static void Main(string[] a){
  var m = ModuleDefinition.ReadModule(a[0]);
  Func<TypeDefinition, System.Collections.Generic.IEnumerable<TypeDefinition>> all=null;
  all = x => new[]{x}.Concat(x.NestedTypes.SelectMany(y=>all(y)));
  var t = m.Types.SelectMany(x=>all(x)).First(x=>x.FullName==a[1]);
  foreach (var f in t.Fields.Where(f=>f.HasConstant))
    Console.WriteLine("  " + f.Constant + "  " + f.Name);
}}
