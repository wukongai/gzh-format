#!/usr/bin/env python3
"""为一篇已绑定文章提供本机编辑预览和直接保存草稿。

只监听 127.0.0.1；文件权限来自启动参数绑定的 manifest，不接受 HTTP 文件路径。
保存使用共享修订模型和原稿备份，不访问微信、凭证或外部网络。
"""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import threading

import edit_model
from wrap_preview import render_preview

MAX_BODY = 5 * 1024 * 1024


class PreviewServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, manifest_path, port=0):
        self.manifest_path = Path(manifest_path).resolve()
        initial = edit_model.load_manifest(self.manifest_path)
        # 每次请求都验证同一绑定，不能通过篡改 manifest 把已授权服务换成另一文章。
        self.bound_paths = {key: Path(initial[key]).resolve() for key in ('source_md', 'html_file', 'preview_file')}
        self.article_id = initial['article_id']
        self.edit_session = edit_model.EditSession(self.manifest_path)
        self.state_lock = threading.RLock()
        self.session_token = secrets.token_urlsafe(32)
        self.preview_path = '/' + secrets.token_urlsafe(24) + '/'
        super().__init__(('127.0.0.1', port), PreviewHandler)
        self.origin = f'http://127.0.0.1:{self.server_port}'
        self.preview_url = self.origin + self.preview_path

    def checked_state(self):
        raw = json.loads(edit_model.read_exact(self.manifest_path))
        for key, expected in self.bound_paths.items():
            if not isinstance(raw.get(key), str) or Path(raw[key]).resolve() != expected:
                raise ValueError('conflict: 当前保存服务的文章文件绑定发生变化，零写入')
        if raw.get('article_id') != self.article_id:
            raise ValueError('conflict: 当前保存服务的文章身份发生变化，零写入')
        return edit_model.load_manifest(self.manifest_path)


class PreviewHandler(BaseHTTPRequestHandler):
    server_version = 'GZHLocalPreview/1'
    sys_version = ''

    def log_message(self, format, *args):
        # 默认日志会打印带秘密会话路径的 URL；启动时只输出一次给本机调用方。
        pass

    def _respond(self, status, value, content_type='application/json; charset=utf-8'):
        body = (json.dumps(value, ensure_ascii=False).encode('utf-8')
                if content_type.startswith('application/json') else value.encode('utf-8'))
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Connection', 'close')
        self.end_headers()
        self.close_connection = True
        if self.command != 'HEAD':
            self.wfile.write(body)

    def _error(self, status, message):
        self._respond(status, {'status': 'error', 'error': message})

    def _host_ok(self):
        if self.headers.get_all('Host') != [self.server.origin.removeprefix('http://')]:
            self._error(403, '仅允许本机保存服务的准确 Host')
            return False
        return True

    def _token_ok(self, value):
        if not isinstance(value, str) or not value.isascii() or not secrets.compare_digest(value, self.server.session_token):
            self._error(403, '保存会话已失效或身份不符，请重新打开本机预览')
            return False
        return True

    def _model_error(self, exc):
        message = str(exc)
        self._error(409 if message.startswith('conflict:') else 400, message)

    def do_GET(self):
        if not self._host_ok():
            return
        if self.path not in {self.server.preview_path, '/api/state'}:
            self._error(404, '此服务只提供已绑定文章的编辑与保存')
            return
        if self.path == '/api/state' and (self.headers.get_all('X-GZH-Session') is None
                                         or len(self.headers.get_all('X-GZH-Session')) != 1
                                         or not self._token_ok(self.headers.get('X-GZH-Session'))):
            if self.headers.get_all('X-GZH-Session') is None or len(self.headers.get_all('X-GZH-Session')) != 1:
                self._error(403, '必须提供当前本机保存会话')
            return
        try:
            with self.server.state_lock:
                state = self.server.checked_state()
                if self.path == '/api/state':
                    self._respond(200, {'status': state['status'], 'revision': state['revision'],
                                        'package': self.server.edit_session.public_package()})
                else:
                    body, manifest = self.server.edit_session.snapshot()
                    bridge = {'save_url': '/api/save', 'state_url': '/api/state',
                              'session_token': self.server.session_token}
                    page = render_preview(body, self.server.bound_paths['html_file'].stem, manifest, save_bridge=bridge)
                    self._respond(200, page, 'text/html; charset=utf-8')
        except ValueError as exc:
            self._model_error(exc)
        except OSError:
            self._error(500, '本机文章读取失败，请检查文件后重新打开预览')

    def do_POST(self):
        if not self._host_ok():
            return
        if self.path != '/api/save':
            self._error(404, '未提供此保存入口')
            return
        if self.headers.get_all('Origin') != [self.server.origin]:
            self._error(403, '保存请求必须来自当前本机预览')
            return
        if self.headers.get_all('Content-Type') is None or len(self.headers.get_all('Content-Type')) != 1 or self.headers.get_content_type() != 'application/json':
            self._error(415, '保存请求必须使用 application/json')
            return
        lengths = self.headers.get_all('Content-Length')
        if self.headers.get('Transfer-Encoding') is not None or not lengths or len(lengths) != 1 or not lengths[0].isdigit():
            self._error(400, '保存请求必须提供唯一有效的 Content-Length')
            return
        length = int(lengths[0])
        if length > MAX_BODY:
            self._error(413, '本次修改超过 5MB，未写入文章')
            return
        if not length:
            self._error(400, '保存内容为空')
            return
        try:
            self.connection.settimeout(5)
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError('保存内容不完整')
            request = json.loads(raw.decode('utf-8'))
            if not isinstance(request, dict) or set(request) != {'session_token', 'package'}:
                raise ValueError('保存请求只允许 session_token 与 package，不接受文件路径')
        except (ValueError, UnicodeError) as exc:
            self._error(400, str(exc))
            return
        except OSError:
            self._error(400, '保存内容未完整收到，未写入文章')
            return
        if not self._token_ok(request['session_token']):
            return
        try:
            with self.server.state_lock:
                self.server.checked_state()
                result = self.server.edit_session.save(request['package'])
                # 只有共享事务实际提交后才返回 saved；新基线保留当前会话的稳定 block ID。
                result['package'] = self.server.edit_session.public_package()
                self._respond(200, result)
        except ValueError as exc:
            self._model_error(exc)
        except OSError:
            self._error(500, '保存未完成，未确认写入成功；请保留页面内容并检查本地文件')

    def do_OPTIONS(self):
        if self._host_ok():
            self._error(405, '本机保存服务不接受跨站或预检请求')

    def _unsupported_method(self):
        if self._host_ok():
            self._error(405, '仅允许读取预览、查询状态与保存草稿')

    do_HEAD = do_PUT = do_PATCH = do_DELETE = _unsupported_method


def create_server(manifest_path, port=0):
    """只允许选择空闲端口或本机指定端口，不暴露更换监听地址的入口。"""
    if not isinstance(port, int) or not 0 <= port <= 65535:
        raise ValueError('端口必须在 0 到 65535 之间')
    return PreviewServer(manifest_path, port)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, help='已绑定这一篇文章的本地编辑 manifest')
    parser.add_argument('--port', type=int, default=0, help='本机端口，默认 0 自动选择空闲端口')
    parser.add_argument('--ready-file', help='可选：新建含本机预览 URL 的就绪 JSON，供调用方读取')
    args = parser.parse_args()
    try:
        server = create_server(args.manifest, args.port)
        if args.ready_file:
            ready = {'url': server.preview_url, 'origin': server.origin, 'pid': os.getpid()}
            # 就绪文件包含会话秘密路径，只给当前用户读取；不覆盖已有文件。
            fd = os.open(Path(args.ready_file), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump(ready, stream, ensure_ascii=False)
                stream.write('\n')
        print(server.preview_url, flush=True)
        print('已启用本机保存草稿。结束服务请按 Ctrl+C；不会同步公众号。', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
    except (ValueError, OSError) as exc:
        parser.exit(1, f'本机预览未启动：{exc}\n')


if __name__ == '__main__':
    main()
