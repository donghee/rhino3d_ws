"""Rhino MCP remote proxy.

Rhino's MCP server only accepts requests whose Host header is localhost/127.0.0.1,
so plain TCP port forwarding (netsh portproxy) fails with "400 Invalid Hostname".
This proxy listens on all interfaces and forwards to Rhino with Host rewritten.

Usage: python tools/rhino3d_mcp_proxy.py [listen_port] [rhino_port]  (started by tools/rhino3d_mcpstart.bat)
"""
import http.client
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LISTEN_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 10501
RHINO_PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 10500
RHINO_HOST = "127.0.0.1"

# Hop-by-hop headers must not be forwarded.
HOP_HEADERS = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "host", "content-length",
}


class Proxy(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _forward(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None

        headers = {k: v for k, v in self.headers.items() if k.lower() not in HOP_HEADERS}
        headers["Host"] = f"{RHINO_HOST}:{RHINO_PORT}"
        if body is not None:
            headers["Content-Length"] = str(len(body))

        conn = http.client.HTTPConnection(RHINO_HOST, RHINO_PORT, timeout=600)
        try:
            conn.request(self.command, self.path, body=body, headers=headers)
            resp = conn.getresponse()
        except OSError as e:
            self.send_error(502, f"Rhino MCP not reachable: {e}")
            conn.close()
            return

        self.send_response(resp.status, resp.reason)
        for k, v in resp.getheaders():
            if k.lower() not in HOP_HEADERS and k.lower() not in ("server", "date"):
                self.send_header(k, v)
        # Stream the response (works for both JSON and SSE) using chunked encoding.
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        try:
            while True:
                chunk = resp.read1(65536)
                if not chunk:
                    break
                self.wfile.write(b"%x\r\n%s\r\n" % (len(chunk), chunk))
                self.wfile.flush()
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            conn.close()

    do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = _forward

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s %s\n" % (self.log_date_time_string(), self.client_address[0], fmt % args))


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", LISTEN_PORT), Proxy)
    server.daemon_threads = True
    print(f"Rhino MCP proxy: 0.0.0.0:{LISTEN_PORT} -> {RHINO_HOST}:{RHINO_PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
