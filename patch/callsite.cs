// 지목한 메서드가 어디서 몇 번 불리는지 센다.
using System; using System.Collections.Generic; using System.Linq;
using Mono.Cecil; using Mono.Cecil.Cil;
class S { static void Main(string[] a){
  var res = new DefaultAssemblyResolver(); res.AddSearchDirectory(a[1]);
  var m = ModuleDefinition.ReadModule(a[0], new ReaderParameters{AssemblyResolver=res});
  Func<TypeDefinition, IEnumerable<TypeDefinition>> all = null;
  all = x => new[]{x}.Concat(x.NestedTypes.SelectMany(y=>all(y)));
  var want = a[2];
  var byType = new Dictionary<string,int>();
  int n = 0;
  foreach (var t in m.Types.SelectMany(x=>all(x)))
    foreach (var me in t.Methods) {
      if (!me.HasBody) continue;
      foreach (var ins in me.Body.Instructions) {
        var mr = ins.Operand as MethodReference;
        if (mr == null || !mr.FullName.Contains(want)) continue;
        n++;
        var k = t.FullName.Split('/')[0];
        byType[k] = byType.ContainsKey(k) ? byType[k]+1 : 1;
      }
    }
  Console.WriteLine(want + " : 호출 " + n + "곳");
  foreach (var kv in byType.OrderByDescending(x=>x.Value))
    Console.WriteLine("   " + kv.Value + "  " + kv.Key);
}}
