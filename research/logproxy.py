"""
전량 기록용 HTTP 프록시.
목적: 차차차 클라이언트가 실제로 어느 호스트/경로를 호출하는지 확인한다.
(정적 분석으로는 게임 서버 주소가 APK 안에 없어 알 수 없었던 부분)

CONNECT(HTTPS)도 호스트명만 기록하고 끊는다 -> 어떤 도메인을 쓰는지는 드러난다.
"""
import socketserver, threading, datetime, sys, os

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "proxy_hits.log")
lock = threading.Lock()

def log(msg):
    line = "%s  %s" % (datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3], msg)
    with lock:
        print(line, flush=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")

class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            self.request.settimeout(15)
            data = b""
            # 헤더 끝까지 읽기
            while b"\r\n\r\n" not in data and len(data) < 65536:
                chunk = self.request.recv(4096)
                if not chunk:
                    break
                data += chunk
            if not data:
                return

            head, _, rest = data.partition(b"\r\n\r\n")
            lines = head.decode("latin-1").split("\r\n")
            reqline = lines[0]
            headers = {}
            for l in lines[1:]:
                if ":" in l:
                    k, v = l.split(":", 1)
                    headers[k.strip().lower()] = v.strip()

            parts = reqline.split(" ")
            method = parts[0] if parts else "?"
            target = parts[1] if len(parts) > 1 else "?"

            if method == "CONNECT":
                log("CONNECT  %s   (HTTPS - 호스트만 기록하고 종료)" % target)
                self.request.sendall(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n")
                return

            host = headers.get("host", "?")
            log("%-6s %s" % (method, target))
            log("         Host: %s   UA: %s   CT: %s"
                % (host, headers.get("user-agent", "-"), headers.get("content-type", "-")))

            # 바디 읽기
            clen = int(headers.get("content-length", "0") or 0)
            body = rest
            while len(body) < clen:
                chunk = self.request.recv(min(8192, clen - len(body)))
                if not chunk:
                    break
                body += chunk
            if body:
                try:
                    shown = body.decode("utf-8")
                except UnicodeDecodeError:
                    shown = repr(body[:400])
                log("         BODY(%d): %s" % (len(body), shown[:600]))

            # 클라이언트가 다음 단계로 넘어가도록 최소 성공 응답
            payload = b'{"success":true,"errorCode":null,"token":123456789}'
            self.request.sendall(
                b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
                b"Content-Length: " + str(len(payload)).encode() + b"\r\n"
                b"Connection: close\r\n\r\n" + payload)
        except Exception as e:
            log("  [err] %s" % e)
        finally:
            try:
                self.request.close()
            except Exception:
                pass

class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8888
    log("=== 프록시 시작 0.0.0.0:%d  (로그: %s) ===" % (port, LOG))
    Server(("0.0.0.0", port), Handler).serve_forever()
