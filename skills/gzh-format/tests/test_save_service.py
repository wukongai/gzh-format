"""单文章本机保存服务的真实 HTTP 验证，所有数据都来自独立临时夹具。"""
import copy
import http.client
import importlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import edit_model
import render_markdown as renderer


class SaveServiceTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('serve_preview'), '尚缺少直接保存草稿的本机服务')
        self.service = importlib.import_module('serve_preview')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.md, self.html = self.root / 'test.md', self.root / 'test.html'
        self.source = ('---\ntitle: 本机草稿夹具\nrelated: ["[[测试]]"]\n---\n\n'
                       '## 第一节\n\n### 1. 原编号\n\n第一段要保留。\n\n第二段可以删除。\n\n'
                       '![第一图](https://example.org/1.png)\n\n'
                       '### 2. 后续编号\n\n第三段含 **粗体**。\n\n'
                       '![第二图](https://example.org/2.png)\n')
        self.md.write_text(self.source, encoding='utf-8')
        self.html.write_text(renderer.render(self.source, 'minimal'), encoding='utf-8')
        self.manifest = edit_model.build_manifest(self.md, self.html)
        self.manifest_path = self.root / 'test.gzh-edit-manifest.json'
        self.manifest_path.write_text(json.dumps(self.manifest, ensure_ascii=False), encoding='utf-8')
        self.server = self.service.create_server(self.manifest_path)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)
        self.package = edit_model.public_package(self.manifest)

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def request(self, method, path, payload=None, headers=None, raw=None):
        body = raw if raw is not None else json.dumps(payload, ensure_ascii=False).encode('utf-8') if payload is not None else None
        sent = {'Host': self.server.origin.removeprefix('http://')}
        if method == 'POST':
            sent.update({'Origin': self.server.origin, 'Content-Type': 'application/json'})
        sent.update(headers or {})
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        self.addCleanup(conn.close)
        conn.request(method, path, body=body, headers=sent)
        response = conn.getresponse()
        content = response.read()
        data = json.loads(content) if content and response.getheader('Content-Type', '').startswith('application/json') else content.decode('utf-8')
        return response.status, dict(response.getheaders()), data

    def save(self, package=None, **kwargs):
        return self.request('POST', '/api/save', {'session_token': self.server.session_token,
                                                'package': package if package is not None else self.package}, **kwargs)

    def edit_paragraph(self, package, number=0, text='这是保存后的文字。'):
        block = [b for b in package['blocks'] if b['kind'] == 'paragraph'][number]
        block['runs'] = [{'text': text, 'red': True, 'bold': False, 'href': '', 'marks': []}]
        return block

    def test_loopback_preview_contains_live_save_bridge_and_no_disk_token(self):
        self.assertEqual(self.server.server_address[0], '127.0.0.1')
        self.assertGreater(self.server.server_port, 0)
        before = self.snapshot()
        status, headers, page = self.request('GET', self.server.preview_url.removeprefix(self.server.origin))
        self.assertEqual(status, 200)
        self.assertIn('第一段要保留。', page)
        self.assertIn('save_bridge', page)
        self.assertIn(self.server.session_token, page)
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertNotIn('Access-Control-Allow-Origin', headers)
        self.assertEqual(before, self.snapshot())
        self.assertFalse(any(self.server.session_token.encode() in data for data in before.values()))

    def test_save_writes_article_backup_and_sync_preflight_then_allows_second_save(self):
        self.edit_paragraph(self.package)
        self.edit_paragraph(self.package, 1)['runs'] = []
        status, _, data = self.save()
        self.assertEqual(status, 200, data)
        self.assertEqual(data['status'], 'saved')
        self.assertEqual(data['package']['revision'], 1)
        self.assertIn('这是保存后的文字。', self.md.read_text(encoding='utf-8'))
        self.assertNotIn('第二段可以删除', self.html.read_text(encoding='utf-8'))
        self.assertEqual(edit_model.image_urls(self.html.read_text(encoding='utf-8')), self.manifest['images'])
        self.assertEqual(edit_model.heading_texts(self.html.read_text(encoding='utf-8')), self.manifest['headings'])
        backups = list(self.root.glob('.gzh-edits/*/r*/source.md'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(encoding='utf-8'), self.source)
        self.assertEqual(edit_model.preflight(self.manifest_path)['revision'], 1)
        self.assertNotIn(self.server.session_token, self.md.read_text(encoding='utf-8') + self.html.read_text(encoding='utf-8') + self.manifest_path.read_text(encoding='utf-8'))
        second = data['package']
        self.edit_paragraph(second, text='第二次点击保存。')
        status, _, data = self.save(second)
        self.assertEqual(status, 200, data)
        self.assertEqual(data['package']['revision'], 2)
        self.assertIn('第二次点击保存。', self.md.read_text(encoding='utf-8'))
        self.assertEqual(edit_model.preflight(self.manifest_path)['revision'], 2)

    def test_save_then_undo_can_restore_deleted_paragraph(self):
        original = copy.deepcopy(self.package)
        self.edit_paragraph(self.package, 1)['runs'] = []
        status, _, data = self.save()
        self.assertEqual(status, 200, data)
        restored = copy.deepcopy(data['package'])
        # 客户端保留自己的历史；保存只更新修订基线，不能重排最初的 block ID。
        restored['blocks'] = original['blocks']
        status, _, data = self.save(restored)
        self.assertEqual(status, 200, data)
        self.assertIn('第二段可以删除。', self.html.read_text(encoding='utf-8'))
        self.assertEqual(data['package']['revision'], 2)

    def test_title_http_save_undo_and_reopen_preserve_body(self):
        original_body = self.html.read_bytes()
        self.package['title'] = 'HTTP 保存的新标题'
        status, _, data = self.save()
        self.assertEqual(status, 200, data)
        self.assertEqual(data['package']['title'], 'HTTP 保存的新标题')
        self.assertEqual(self.html.read_bytes(), original_body)
        status, _, page = self.request('GET', self.server.preview_url.removeprefix(self.server.origin))
        self.assertEqual(status, 200)
        self.assertIn('value="HTTP 保存的新标题"', page)
        restored = data['package']
        restored['title'] = '本机草稿夹具'
        status, _, data = self.save(restored)
        self.assertEqual(status, 200, data)
        self.assertEqual(data['package']['revision'], 2)
        self.assertEqual(edit_model.EditSession(self.manifest_path).public_package()['title'], '本机草稿夹具')
        self.assertEqual(self.html.read_bytes(), original_body)

    def test_invalid_title_http_request_writes_nothing(self):
        before = self.snapshot()
        for title in ('', '跨\n行'):
            package = copy.deepcopy(self.package)
            package['title'] = title
            self.assertEqual(self.save(package)[0], 400)
            self.assertEqual(self.snapshot(), before)

    def test_state_requires_token_and_returns_current_baseline(self):
        before = self.snapshot()
        self.assertEqual(self.request('GET', '/api/state')[0], 403)
        status, _, data = self.request('GET', '/api/state', headers={'X-GZH-Session': self.server.session_token})
        self.assertEqual(status, 200, data)
        self.assertEqual(data['package']['revision'], 0)
        self.assertEqual(data['package']['article_id'], self.package['article_id'])
        self.assertEqual(before, self.snapshot())

    def test_wrong_token_origin_host_and_non_json_never_write(self):
        before = self.snapshot()
        cases = [({'session_token': 'wrong', 'package': self.package}, {}, 403),
                 ({'session_token': self.server.session_token, 'package': self.package}, {'Origin': 'https://example.org'}, 403),
                 ({'session_token': self.server.session_token, 'package': self.package}, {'Origin': ''}, 403),
                 ({'session_token': self.server.session_token, 'package': self.package}, {'Host': 'example.org'}, 403),
                 ({'session_token': self.server.session_token, 'package': self.package}, {'Content-Type': 'text/plain'}, 415)]
        for payload, headers, expected in cases:
            with self.subTest(headers=headers):
                self.assertEqual(self.request('POST', '/api/save', payload, headers)[0], expected)
                self.assertEqual(before, self.snapshot())
        self.assertEqual(self.request('GET', self.server.preview_url.removeprefix(self.server.origin), headers={'Host': 'example.org'})[0], 403)

    def test_unicode_token_is_rejected_as_a_normal_request(self):
        before = self.snapshot()
        status, _, data = self.request('POST', '/api/save', {'session_token': '无效会话', 'package': self.package})
        self.assertEqual(status, 403, data)
        self.assertEqual(before, self.snapshot())

    def test_unknown_paths_query_paths_and_cors_are_rejected(self):
        before = self.snapshot()
        for path in ['/test.md', '/test.html', '/', '/api/save?path=test.md', '/api/state?token=' + self.server.session_token,
                     self.server.preview_url.removeprefix(self.server.origin) + '?anything=1', '/../test.md']:
            with self.subTest(path=path):
                self.assertEqual(self.request('GET', path)[0], 404)
        status, headers, _ = self.request('OPTIONS', '/api/save', headers={'Origin': 'https://example.org'})
        self.assertEqual(status, 405)
        self.assertNotIn('Access-Control-Allow-Origin', headers)
        self.assertEqual(before, self.snapshot())

    def test_other_methods_are_rejected_without_static_file_access(self):
        before = self.snapshot()
        for method in ['PUT', 'PATCH', 'DELETE', 'HEAD']:
            with self.subTest(method=method):
                status, headers, _ = self.request(method, '/test.md')
                self.assertEqual(status, 405)
                self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertEqual(before, self.snapshot())

    def test_invalid_json_fields_and_oversized_body_never_write(self):
        before = self.snapshot()
        for raw in [b'{', b'[]', b'{"session_token":"x","package":{},"source_md":"other.md"}']:
            self.assertEqual(self.request('POST', '/api/save', raw=raw)[0], 400)
            self.assertEqual(before, self.snapshot())
        self.assertEqual(self.request('POST', '/api/save', raw=b'{}', headers={'Content-Length': str(5 * 1024 * 1024 + 1)})[0], 413)
        self.assertEqual(self.request('POST', '/api/save', raw=b'{}', headers={'Content-Length': '-1'})[0], 400)
        self.assertEqual(before, self.snapshot())

    def test_invalid_package_or_source_drift_never_write(self):
        bad = copy.deepcopy(self.package)
        bad['source_md'] = str(self.root / 'unrelated.md')
        before = self.snapshot()
        self.assertEqual(self.save(bad)[0], 400)
        self.assertEqual(before, self.snapshot())
        self.md.write_text(self.source + '\n源文另有改动\n', encoding='utf-8')
        before = self.snapshot()
        self.assertEqual(self.save()[0], 409)
        self.assertEqual(self.request('GET', '/api/state', headers={'X-GZH-Session': self.server.session_token})[0], 409)
        self.assertEqual(before, self.snapshot())

    def test_manifest_cannot_be_rebound_to_another_article(self):
        other_md, other_html = self.root / 'other.md', self.root / 'other.html'
        other_md.write_text(self.source.replace('本机草稿夹具', '其它文章'), encoding='utf-8')
        other_html.write_text(renderer.render(other_md.read_text(encoding='utf-8'), 'minimal'), encoding='utf-8')
        rebound = edit_model.build_manifest(other_md, other_html)
        self.manifest_path.write_text(json.dumps(rebound), encoding='utf-8')
        before = self.snapshot()
        self.assertEqual(self.save()[0], 409)
        self.assertEqual(self.request('GET', self.server.preview_url.removeprefix(self.server.origin))[0], 409)
        self.assertEqual(before, self.snapshot())

    def test_stale_browser_revision_is_rejected_without_overwrite(self):
        stale = copy.deepcopy(self.package)
        self.edit_paragraph(self.package)
        self.assertEqual(self.save()[0], 200)
        self.edit_paragraph(stale, text='过期页面覆盖尝试')
        before = self.snapshot()
        self.assertEqual(self.save(stale)[0], 409)
        self.assertEqual(before, self.snapshot())


if __name__ == '__main__':
    unittest.main()
