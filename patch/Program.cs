using chachacha_server.HTTP;
using System.Text;

namespace chachacha_server
{
    internal class Program
    {
        static void Main(string[] args)
        {
            Console.OutputEncoding = Encoding.UTF8;
            Console.InputEncoding = Encoding.UTF8;

            // 사용법: chachacha-server.exe [prefix] [captureDir]
            //   prefix 기본값 http://*:80/  (Windows 에서 * 바인딩은 관리자 권한 필요)
            //   권한 없이 테스트하려면 http://localhost:8080/ 처럼 지정
            string prefix = args.Length > 0 ? args[0] : "http://*:80/";
            string captureDir = args.Length > 1 ? args[1] : "capture";

            SchemaCollector.Init(captureDir);

            // Ctrl+C / 프로세스 종료 시 수집 결과를 확실히 flush
            Console.CancelKeyPress += (s, e) =>
            {
                e.Cancel = true;
                Shutdown();
                Environment.Exit(0);
            };
            AppDomain.CurrentDomain.ProcessExit += (s, e) => Shutdown();

            Console.WriteLine("=================================================");
            Console.WriteLine(" 차차차 사설 서버 + 요청 스키마 수집기");
            Console.WriteLine($" prefix : {prefix}");
            Console.WriteLine($" capture: {Path.GetFullPath(captureDir)}");
            Console.WriteLine("=================================================");

            try
            {
                HTTPProcessor processor = new HTTPProcessor(prefix);
                processor.StartListening();
            }
            catch (System.Net.HttpListenerException ex)
            {
                Console.WriteLine();
                Console.WriteLine($"[오류] 리스너 시작 실패 ({ex.Message})");
                Console.WriteLine("  - '*' 또는 80 포트 바인딩은 관리자 권한이 필요합니다.");
                Console.WriteLine("  - 관리자 콘솔에서 실행하거나, 인자로 다른 주소를 주세요:");
                Console.WriteLine("      chachacha-server.exe http://localhost:8080/");
                return;
            }

            Console.WriteLine("Enter 를 누르면 종료하며 수집 결과를 저장합니다.");
            Console.ReadLine();
            Shutdown();
        }

        private static bool shutdownDone = false;
        private static void Shutdown()
        {
            if (shutdownDone) return;
            shutdownDone = true;
            SchemaCollector.Save();
            SchemaCollector.PrintSummary();
        }
    }
}
