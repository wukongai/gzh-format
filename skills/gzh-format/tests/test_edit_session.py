"""直接保存草稿保留稳定块身份，使保存后撤销的内容可以再次落盘。"""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import edit_model
import render_markdown


class EditSessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.md, self.html = self.root / 'article.md', self.root / 'article.html'
        self.source = '---\ntitle: 保存测试\nrelated: []\n---\n\n## 标题\n\n### 1. 小标题\n\n第一段，[链接](https://example.invalid/a)。\n\n可删除的一段。\n\n最后一段。\n'
        self.md.write_text(self.source, encoding='utf-8')
        self.html.write_text(render_markdown.render(self.source, 'minimal'), encoding='utf-8')
        self.path = edit_model.default_manifest(self.html)
        self.path.write_text(json.dumps(edit_model.build_manifest(self.md, self.html)), encoding='utf-8')

    def test_saved_deletion_can_be_undone_and_saved_with_stable_ids(self):
        session = edit_model.EditSession(self.path)
        initial = session.public_package()
        package = copy.deepcopy(initial)
        deleted = next(b for b in package['blocks'] if '可删除' in ''.join(r['text'] for r in b['runs']))
        deleted['runs'] = []
        saved = session.save(package)
        self.assertEqual(saved['status'], 'saved')
        self.assertNotIn('可删除的一段', self.md.read_text(encoding='utf-8'))
        self.assertEqual([b['id'] for b in saved['package']['blocks']], [b['id'] for b in initial['blocks']])
        self.assertEqual(saved['package']['blocks'][package['blocks'].index(deleted)]['runs'], [])
        restored = copy.deepcopy(saved['package'])
        restored['blocks'] = initial['blocks']
        session.save(restored)
        self.assertIn('可删除的一段', self.md.read_text(encoding='utf-8'))
        self.assertIn('href="https://example.invalid/a"', self.html.read_text(encoding='utf-8'))
        self.assertEqual(edit_model.preflight(self.path)['revision'], 2)

    def test_snapshot_rebinds_current_html_and_stable_empty_slots(self):
        session = edit_model.EditSession(self.path)
        package = session.public_package()
        paragraph = next(b for b in package['blocks'] if b['kind'] == 'paragraph')
        paragraph['runs'] = [{'text': '更长的人工文字', 'red': True, 'bold': False, 'href': '', 'marks': []}]
        last = package['blocks'][-1]
        last['runs'] = []
        session.save(package)
        body, manifest = session.snapshot()
        wrapped = edit_model.editable_body(body, manifest)
        number_parts = sum(len(block.get('extra_open_ends', [])) for block in manifest['blocks'])
        self.assertEqual(wrapped.count('data-gzh-edit-id='), len(package['blocks']) + number_parts)
        self.assertEqual(wrapped.count('data-gzh-edit-part="number"'), number_parts)
        self.assertIn('更长的人工文字', wrapped)
        self.assertIn('data-gzh-edit-empty="1"', wrapped)
        self.assertNotIn('第一段，', wrapped)

    def test_source_drift_and_stale_revision_write_nothing(self):
        session = edit_model.EditSession(self.path)
        package = session.public_package()
        session.save(package)
        package['blocks'][-1]['runs'][0]['text'] = '来自过期修订的改动'
        with self.assertRaisesRegex(ValueError, 'conflict|冲突'):
            session.save(package)
        latest = session.public_package()
        self.md.write_text(self.md.read_text(encoding='utf-8') + '\n别的会话改了源文。\n', encoding='utf-8')
        before = self.md.read_bytes()
        with self.assertRaisesRegex(ValueError, 'conflict|漂移'):
            session.save(latest)
        self.assertEqual(self.md.read_bytes(), before)

    def test_no_change_save_is_saved_without_new_revision(self):
        session = edit_model.EditSession(self.path)
        result = session.save(session.public_package())
        self.assertEqual(result['status'], 'saved')
        self.assertEqual(result['package']['revision'], 1)
        again = session.save(session.public_package())
        self.assertEqual(again['package']['revision'], 1)

    def test_response_lost_retry_with_new_timestamp_is_idempotent(self):
        session = edit_model.EditSession(self.path)
        package = session.public_package()
        package['saved_at'] = '2026-10-24T10:00:00Z'
        first = session.save(package)
        package['saved_at'] = '2026-10-24T10:01:00Z'
        retried = session.save(package)
        self.assertEqual(retried['status'], 'already-imported')
        self.assertEqual(retried['package']['revision'], first['package']['revision'])


if __name__ == '__main__':
    unittest.main()
