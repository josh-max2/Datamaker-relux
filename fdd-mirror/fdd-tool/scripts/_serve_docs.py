"""Tiny http server that serves docs/ at /Parser/ to match prod URL structure."""
import http.server
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2] / "docs"
PREFIX = "/Parser"


class H(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        # Strip the /Parser prefix before resolving against docs/
        if path.startswith(PREFIX):
            path = path[len(PREFIX):] or "/"
        return super().translate_path(path)


class Server(http.server.ThreadingHTTPServer):
    pass


if __name__ == "__main__":
    import os
    os.chdir(str(ROOT))
    s = Server(("127.0.0.1", 8765), H)
    print(f"serving {ROOT} at http://127.0.0.1:8765{PREFIX}/")
    s.serve_forever()
