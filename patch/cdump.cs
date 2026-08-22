// Cecil 기반 범용 덤퍼 (잃어버린 파이썬 IL 도구 대체).
//   cdump <dll> <managed> types   <정규식>          타입 목록
//   cdump <dll> <managed> methods <타입정규식>      해당 타입의 메서드
//   cdump <dll> <managed> fields  <타입정규식>      해당 타입의 필드(타입/접근자 포함)
//   cdump <dll> <managed> strings <문자열정규식>    그 리터럴을 가진 메서드
//   cdump <dll> <managed> il      <메서드정규식>    IL 디스어셈블
//   cdump <dll> <managed> callers <메서드정규식>    호출자 찾기
using System; using System.Linq; using System.Text.RegularExpressions;
using Mono.Cecil; using Mono.Cecil.Cil;
static class C {
  static AssemblyDefinition asm;
  static System.Collections.Generic.IEnumerable<TypeDefinition> AllTypes(TypeDefinition t) {
    yield return t;
    foreach (var n in t.NestedTypes) foreach (var x in AllTypes(n)) yield return x;
  }
  static System.Collections.Generic.IEnumerable<TypeDefinition> Types() {
    return asm.MainModule.Types.SelectMany(AllTypes);
  }
  static int Main(string[] a) {
    if (a.Length < 4) { Console.Error.WriteLine("usage: cdump <dll> <managed> <cmd> <regex>"); return 2; }
    var r = new DefaultAssemblyResolver(); r.AddSearchDirectory(a[1]);
    asm = AssemblyDefinition.ReadAssembly(a[0], new ReaderParameters{AssemblyResolver=r});
    var rx = new Regex(a[3], RegexOptions.IgnoreCase);
    string cmd = a[2].ToLower();
    int n = 0;
    if (cmd == "types") {
      foreach (var t in Types().Where(t => rx.IsMatch(t.FullName)).OrderBy(t => t.FullName))
      { Console.WriteLine("  " + t.FullName); n++; }
    } else if (cmd == "methods") {
      foreach (var t in Types().Where(t => rx.IsMatch(t.FullName)))
        foreach (var m in t.Methods)
        { Console.WriteLine("  {0}::{1}({2})", t.FullName, m.Name,
            string.Join(", ", m.Parameters.Select(p => p.ParameterType.Name).ToArray())); n++; }
    } else if (cmd == "fields") {
      foreach (var t in Types().Where(t => rx.IsMatch(t.FullName)))
        foreach (var f in t.Fields)
        { Console.WriteLine("  {0}::{1,-34} {2} {3}", t.FullName, f.Name, f.FieldType.Name,
            f.IsPublic ? "public" : "private"); n++; }
    } else if (cmd == "strings") {
      foreach (var t in Types()) foreach (var m in t.Methods) {
        if (!m.HasBody) continue;
        var hit = m.Body.Instructions.Where(i => i.OpCode == OpCodes.Ldstr
                    && i.Operand is string && rx.IsMatch((string)i.Operand))
                  .Select(i => (string)i.Operand).Distinct().ToArray();
        if (hit.Length == 0) continue;
        Console.WriteLine("  {0}::{1}", t.FullName, m.Name);
        foreach (var h in hit) Console.WriteLine("       \"{0}\"", h.Length > 90 ? h.Substring(0,90) : h);
        n++;
      }
    } else if (cmd == "il") {
      foreach (var t in Types()) foreach (var m in t.Methods) {
        if (!m.HasBody || !rx.IsMatch(t.FullName + "::" + m.Name)) continue;
        Console.WriteLine("==== {0}::{1}  ({2} 명령)", t.FullName, m.Name, m.Body.Instructions.Count);
        foreach (var i in m.Body.Instructions) {
          string op = i.Operand == null ? "" :
            (i.Operand is string ? "\"" + (string)i.Operand + "\"" :
             i.Operand is Instruction ? "IL_" + ((Instruction)i.Operand).Offset.ToString("X4") :
             i.Operand.ToString());
          if (op.Length > 100) op = op.Substring(0, 100);
          Console.WriteLine("  IL_{0:X4}  {1,-12} {2}", i.Offset, i.OpCode.Name, op);
        }
        n++;
      }
    } else if (cmd == "callers") {
      foreach (var t in Types()) foreach (var m in t.Methods) {
        if (!m.HasBody) continue;
        var hit = m.Body.Instructions.Select(i => i.Operand as MethodReference)
                   .Where(x => x != null && rx.IsMatch(x.DeclaringType.FullName + "::" + x.Name))
                   .Select(x => x.DeclaringType.Name + "::" + x.Name).Distinct().ToArray();
        if (hit.Length == 0) continue;
        Console.WriteLine("  {0}::{1}  ->  {2}", t.FullName, m.Name, string.Join(", ", hit));
        n++;
      }
    }
    Console.WriteLine("[{0}건]", n);
    return 0;
  }
}
