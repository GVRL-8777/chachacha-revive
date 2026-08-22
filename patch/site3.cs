// 어떤 메서드를 부르는 메서드의 이름만 나열한다.
using System; using System.Collections.Generic; using System.Linq;
using Mono.Cecil; using Mono.Cecil.Cil;
class S3 { static void Main(string[] a){
  var res=new DefaultAssemblyResolver(); res.AddSearchDirectory(a[1]);
  var m=ModuleDefinition.ReadModule(a[0], new ReaderParameters{AssemblyResolver=res});
  Func<TypeDefinition,IEnumerable<TypeDefinition>> all=null;
  all=x=>new[]{x}.Concat(x.NestedTypes.SelectMany(y=>all(y)));
  foreach(var t in m.Types.SelectMany(x=>all(x))){
    if(t.FullName.Split('/')[0] != a[2]) continue;
    foreach(var me in t.Methods){
      if(!me.HasBody) continue;
      foreach(var ins in me.Body.Instructions){
        var mr=ins.Operand as MethodReference;
        if(mr!=null && mr.FullName.Contains(a[3]))
          Console.WriteLine("  " + t.FullName + "::" + me.Name);
      }
    }
  }
}}
