"""Dependency-free local HTTP server. Run: python3 -m queens.server."""
import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from .service import dispatch
from .jobs import GenerationJobs

JOBS = GenerationJobs()

WEB = Path(__file__).parent / 'web'


def same_origin(origin, host):
    return origin is None or origin in ('http://' + host, 'https://' + host)


class Handler(BaseHTTPRequestHandler):
    def send(self, code, body, content_type='application/json; charset=utf-8'):
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body)

    def json(self, code, value):
        self.send(code, json.dumps(value, ensure_ascii=False).encode())

    def do_GET(self):
        path = self.path.split('?')[0]
        if path == '/api/algorithms':
            self.json(200, dispatch('algorithms', {}))
        elif path in ('/', '/app.js', '/style.css'):
            filename = {'/': 'index.html', '/app.js': 'app.js', '/style.css': 'style.css'}[path]
            mime = {'/': 'text/html', '/app.js': 'text/javascript', '/style.css': 'text/css'}[path]
            self.send(200, (WEB / filename).read_bytes(), mime + '; charset=utf-8')
        else:
            self.json(404, dict(error='Not found.'))

    def do_POST(self):
        if self.path not in ('/api/solve', '/api/generate', '/api/generation/start',
                             '/api/generation/status', '/api/generation/cancel'):
            self.json(404, dict(error='Not found.'))
            return
        # Support HTTPS termination at the hosting proxy, while rejecting other origins.
        origin = self.headers.get('Origin')
        if not same_origin(origin, self.headers.get('Host', '')):
            self.json(403, dict(error='Cross-origin requests are not allowed.'))
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 65536:
                raise ValueError('Request body must be between 1 and 65536 bytes.')
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError('Request must be a JSON object.')
            if self.path == '/api/generation/start':
                result = JOBS.start(data)
            elif self.path == '/api/generation/status':
                result = JOBS.status(data.get('job_id'))
            elif self.path == '/api/generation/cancel':
                result = JOBS.cancel(data.get('job_id'))
            else:
                result = dispatch(self.path.rsplit('/', 1)[-1], data)
            self.json(200, result)
        except (ValueError, TypeError, UnicodeError) as error:
            self.json(400, dict(error=str(error)))
        except Exception:
            import traceback
            traceback.print_exc()
            self.json(500, dict(error='Internal error; see server console.'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=int(os.environ.get('PORT', '8000')))
    parser.add_argument('--host', default='127.0.0.1')
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f'Queens Lab: http://{args.host}:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
