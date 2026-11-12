"""独立文章夹具验证保存与回填，绝不操作用户实稿。"""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import render_markdown as renderer


class EditablePreviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.md = self.root / 'article.md'
        self.html = self.root / 'article.html'
        self.source = ('---\ntitle: 独立测试\nrelated: ["[[测试]]"]\n---\n\n'
                       '# 独立测试\n\n<!-- 保留注释 -->\n\n## 一、问题\n\n'
                       + '\n\n'.join(f'### {i}. 小标题\n\n原文段落{i}，含有 **加粗** 和 [链接](https://example.org/a)。' for i in range(1, 12))
                       + '\n\n' + '\n\n'.join(f'![图{i}](https://example.org/{i}.png)' for i in range(16))
                       + '\n\n> 引用原句\n\n- 列表甲\n- 列表乙\n\n[[不可丢的双链]]\n')
        self.md.write_text(self.source, encoding='utf-8')
        self.html.write_text(renderer.render(self.source, 'minimal'), encoding='utf-8')

    def setup_edit(self):
        import edit_model
        self.model = edit_model
        manifest = edit_model.build_manifest(self.md, self.html)
        path = self.root / 'article.gzh-edit-manifest.json'
        path.write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')
        package = edit_model.public_package(manifest)
        package['saved_at'] = '2026-10-24T00:00:00Z'
        return manifest, path, package

    def test_windows_crlf_html_maps_and_saves_without_weakening_conflict_checks(self):
        # 在任何操作系统复现 Windows 文本写入；正文映射必须使用真实 CRLF 偏移。
        import edit_model
        source = self.source.replace('\n', '\r\n')
        body = renderer.render(source, 'minimal').replace('\n', '\r\n')
        self.md.write_bytes(source.encode('utf-8'))
        self.html.write_bytes(body.encode('utf-8'))
        state, path, package = self.setup_edit()
        paragraph = next(b for b in state['blocks'] if b['kind'] == 'paragraph')
        editable = edit_model.editable_body(body, state)
        node = next(n for n in edit_model.Tree(editable).root.walk()
                    if n.attrs.get('data-gzh-edit-id') == paragraph['id'])
        self.assertEqual(edit_model.node_runs(node), paragraph['runs'])
        import subprocess
        wrapper = Path(__file__).resolve().parents[1] / 'scripts/wrap_preview.py'
        preview = subprocess.run([sys.executable, str(wrapper), str(self.html),
                                  '--editable', '--source-md', str(self.md), '--manifest', str(path)],
                                 capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(preview.returncode, 0, preview.stderr)
        page = edit_model.read_exact(state['preview_file'])
        nodes = list(edit_model.Tree(page).root.walk())
        for block in state['blocks']:
            node = next(n for n in nodes
                        if n.attrs.get('data-gzh-edit-id') == block['id']
                        and n.attrs.get('data-gzh-edit-part') != 'number')
            self.assertEqual(edit_model.node_runs(node), block['runs'])
        self.html.write_bytes(body.replace('原文段落1', '不同正文').encode('utf-8'))
        with self.assertRaises(ValueError):
            edit_model.build_manifest(self.md, self.html)
        self.html.write_bytes(body.encode('utf-8'))
        package['title'] = 'Windows 标题修订'
        saved = edit_model.apply_package(package, path, apply=True)
        self.assertEqual(saved['status'], 'saved')
        self.assertEqual(self.html.read_bytes(), body.encode('utf-8'))
        package = edit_model.public_package(edit_model.load_manifest(path))
        block = next(b for b in package['blocks'] if b['kind'] == 'paragraph')
        block['runs'][0]['text'] = 'Windows 正文修订'
        saved = edit_model.apply_package(package, path, apply=True)
        self.assertEqual(saved['status'], 'saved')
        self.assertIn('Windows 正文修订', edit_model.read_exact(self.md))
        self.assertNotIn('\n', edit_model.read_exact(self.md).replace('\r\n', ''))
        self.assertEqual(Path(saved['backup_dir'], 'body.html').read_bytes(), body.encode('utf-8'))
        self.assertEqual(edit_model.preflight(path)['status'], 'saved')

    def test_save_delete_and_independent_styles_preserve_images_and_numbers(self):
        manifest, path, package = self.setup_edit()
        block = next(b for b in package['blocks'] if b['kind'] == 'paragraph')
        block['runs'] = [{'text': '人工保留', 'red': False, 'bold': True, 'href': '', 'marks': []},
                         {'text': '只红不粗', 'red': True, 'bold': False, 'href': '', 'marks': []}]
        second = [b for b in package['blocks'] if b['kind'] == 'paragraph'][1]
        second['runs'] = []
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        preview = self.model.apply_package(package, path)
        self.assertEqual(preview['status'], 'dry-run')
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})
        saved = self.model.apply_package(package, path, apply=True)
        self.assertEqual(saved['status'], 'saved')
        new_md = self.md.read_text(encoding='utf-8')
        new_html = self.html.read_text(encoding='utf-8')
        self.assertIn('<!-- 保留注释 -->', new_md)
        self.assertIn('[[不可丢的双链]]', new_md)
        self.assertNotIn('原文段落1，', new_md)
        self.assertNotIn('原文段落2，', new_html)
        self.assertEqual(manifest['images'], self.model.image_urls(new_html))
        self.assertEqual(manifest['headings'], self.model.heading_texts(new_html))
        self.assertEqual(Path(saved['backup_dir'], 'source.md').read_text(encoding='utf-8'), self.source)
        self.assertEqual(self.model.preflight(path)['status'], 'saved')
        self.assertEqual(self.model.apply_package(package, path, apply=True)['status'], 'already-imported')
        rerender = renderer.render(new_md, 'minimal', require_semantic_anchors=True)
        self.assertIn('人工保留', rerender)
        self.assertIn('color:#DC2626;font-weight:400', rerender)

    def test_manual_save_keeps_legacy_generic_anchor_compatible(self):
        import edit_model
        self.model = edit_model
        source = (
            '---\ntitle: 旧稿红标\nrelated: []\n---\n\n'
            '<!-- gzh-manual-revision:v1 -->\n\n'
            '## 一、旧稿章节\n\n'
            '系统运行记录已经确认这条判断来自旧稿，'
            '<mark data-gzh="semantic-anchor">因此这不是具体判断</mark>，'
            '后续内容继续说明旧稿中的人工标记需要原样保留，不能因为新规则升级而阻断保存。'
            '保存前还会继续核对来源、图片和标题编号，确保历史人工样式不会被新的自动门禁覆盖。\n'
        )
        md, html = self.root / 'legacy.md', self.root / 'legacy.html'
        md.write_text(source, encoding='utf-8')
        html.write_text(renderer.render(source, 'minimal'), encoding='utf-8')
        manifest = self.model.build_manifest(md, html)
        path = self.root / 'legacy.gzh-edit-manifest.json'
        path.write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')
        package = self.model.public_package(manifest)
        paragraph = next(block for block in package['blocks'] if block['kind'] == 'paragraph')
        paragraph['runs'][0]['text'] += ' 已复核。'
        saved = self.model.apply_package(package, path, apply=True)
        self.assertEqual(saved['status'], 'saved')
        self.assertIn('因此这不是具体判断', html.read_text(encoding='utf-8'))

    def test_conflicts_and_bad_packages_write_nothing(self):
        manifest, path, package = self.setup_edit()
        bad = copy.deepcopy(package)
        bad['blocks'][0]['runs'][0]['href'] = 'javascript:alert(1)'
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        with self.assertRaises(ValueError):
            self.model.apply_package(bad, path, apply=True)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})
        self.md.write_text(self.source + '\n后来改动\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'conflict|冲突|漂移'):
            self.model.apply_package(package, path, apply=True)
        self.assertFalse((self.root / '.gzh-edits').exists())

    def test_pending_package_and_source_drift_block_preflight(self):
        _, path, package = self.setup_edit()
        self.model.apply_package(package, path, apply=True)
        pending = copy.deepcopy(self.model.public_package(json.loads(path.read_text(encoding='utf-8'))))
        pending['blocks'][0]['runs'][0]['text'] += '未导入'
        (self.root / 'pending.gzh-edit.json').write_text(json.dumps(pending), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '未导入|pending'):
            self.model.preflight(path)
        (self.root / 'pending.gzh-edit.json').unlink()
        self.html.write_text(self.html.read_text(encoding='utf-8') + '\n变更', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'conflict|冲突|漂移'):
            self.model.preflight(path)

    def test_unedited_package_does_not_rewrite_source(self):
        _, path, package = self.setup_edit()
        self.model.apply_package(package, path, apply=True)
        self.assertEqual(self.md.read_text(encoding='utf-8'), self.source)

    def test_failed_save_can_retry_and_restores_current_files(self):
        from unittest.mock import patch
        _, path, package = self.setup_edit()
        before_md, before_html, before_manifest = self.md.read_bytes(), self.html.read_bytes(), path.read_bytes()
        # 模拟落盘后生成预览失败；必须恢复 MD/HTML，并允许用户原包再次保存。
        with patch('wrap_preview.render_preview', side_effect=OSError('模拟写入失败')):
            with self.assertRaises(OSError):
                self.model.apply_package(package, path, apply=True)
        self.assertEqual((self.md.read_bytes(), self.html.read_bytes(), path.read_bytes()), (before_md, before_html, before_manifest))
        self.assertEqual(self.model.apply_package(package, path, apply=True)['status'], 'saved')

    def test_newline_text_and_second_edit_round_trip(self):
        _, path, package = self.setup_edit()
        block = next(b for b in package['blocks'] if b['kind'] == 'paragraph')
        block['runs'] = [{'text': '第一行\n第二行<script>只是文字</script>', 'red': False, 'bold': False, 'href': '', 'marks': []}]
        self.model.apply_package(package, path, apply=True)
        self.assertNotIn('<script>', self.html.read_text(encoding='utf-8'))
        self.assertIn('<br>', self.html.read_text(encoding='utf-8'))
        state = json.loads(path.read_text(encoding='utf-8'))
        second = self.model.public_package(state)
        block = next(b for b in second['blocks'] if b['kind'] == 'paragraph')
        self.assertEqual(''.join(r['text'] for r in block['runs']), '第一行\n第二行<script>只是文字</script>')
        block['runs'][0]['red'] = True
        self.model.apply_package(second, path, apply=True)
        self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['revision'], 2)

    def test_safe_link_apostrophe_is_preserved_when_editing_paragraph(self):
        source = self.source.replace('https://example.org/a', "https://example.org/it's")
        self.md.write_text(source, encoding='utf-8')
        self.html.write_text(renderer.render(source, 'minimal'), encoding='utf-8')
        _, path, package = self.setup_edit()
        block = next(b for b in package['blocks'] if b['kind'] == 'paragraph')
        block['runs'][0]['text'] = '人工修改，'
        self.model.apply_package(package, path, apply=True)
        self.assertIn("https://example.org/it&#x27;s", self.html.read_text(encoding='utf-8'))

    def test_crlf_source_and_original_bytes_are_preserved(self):
        raw = self.source.replace('\n', '\r\n').encode('utf-8')
        self.md.write_bytes(raw)
        _, path, package = self.setup_edit()
        block = next(b for b in package['blocks'] if b['kind'] == 'paragraph')
        block['runs'][0]['text'] = '只改这一处，'
        saved = self.model.apply_package(package, path, apply=True)
        self.assertEqual(Path(saved['backup_dir'], 'source.md').read_bytes(), raw)
        result = self.md.read_bytes()
        self.assertIn(b'---\r\ntitle:', result)
        self.assertIn('<!-- 保留注释 -->\r\n'.encode(), result)
        self.assertIn('原文段落2'.encode(), result)
        self.assertNotIn(b'\n', result.replace(b'\r\n', b''))

    def test_custom_preview_is_refreshed_and_path_alias_is_rejected(self):
        import subprocess
        wrapper = Path(__file__).resolve().parents[1] / 'scripts/wrap_preview.py'
        custom = self.root / 'custom.html'
        generated = subprocess.run([sys.executable, str(wrapper), str(self.html), str(custom), '--editable', '--source-md', str(self.md)], capture_output=True)
        self.assertEqual(generated.returncode, 0, generated.stderr)
        state = json.loads((self.root / 'article.gzh-edit-manifest.json').read_text(encoding='utf-8'))
        package = self.model.public_package(state) if hasattr(self, 'model') else __import__('edit_model').public_package(state)
        __import__('edit_model').apply_package(package, self.root / 'article.gzh-edit-manifest.json', apply=True)
        self.assertTrue('"revision": 1' in custom.read_text(encoding='utf-8'), '自定义预览仍是旧修订')
        before = self.md.read_bytes()
        alias = self.root / 'alias.md'
        alias.symlink_to(self.md)
        bad = subprocess.run([sys.executable, str(wrapper), str(self.html), str(alias), '--editable', '--source-md', str(self.md)], capture_output=True)
        self.assertNotEqual(bad.returncode, 0)
        self.assertEqual(self.md.read_bytes(), before)

    def test_h3_heading_number_variants_can_be_edited(self):
        for prefix in ['（一）', '(1)', '01 ', '1. ', '一、']:
            with self.subTest(prefix=prefix):
                source = '## 标题\n\n### ' + prefix + '保护标题\n\n正文。\n'
                self.md.write_text(source, encoding='utf-8')
                self.html.write_text(renderer.render(source, 'minimal'), encoding='utf-8')
                _, path, package = self.setup_edit()
                heading = next(b for b in package['blocks'] if b['kind'] == 'h3')
                heading['runs'][0]['text'] = '保护标题'
                self.model.apply_package(package, path, apply=True)
                self.assertIn('### <span data-gzh="manual-style"', self.md.read_text(encoding='utf-8'))
                self.assertIn('保护标题', self.html.read_text(encoding='utf-8'))

    def test_h2_number_can_be_changed_and_deleted_independently(self):
        source = '---\ntitle: 序号编辑\nrelated: []\n---\n\n## 一、章节标题\n\n### 1. 子标题\n\n正文保留。\n'
        self.md.write_text(source, encoding='utf-8')
        self.html.write_text(renderer.render(source, 'minimal'), encoding='utf-8')
        _, path, package = self.setup_edit()
        h2 = next(b for b in package['blocks'] if b['kind'] == 'h2')
        h3 = next(b for b in package['blocks'] if b['kind'] == 'h3')
        h2['number'] = '07'
        h3['runs'][0]['text'] = '3. 子标题'
        self.model.apply_package(package, path, apply=True)
        saved_source = self.md.read_text(encoding='utf-8')
        saved_html = self.html.read_text(encoding='utf-8')
        self.assertIn('gzh-h2-number:07', saved_source)
        self.assertIn('>07</span>', saved_html)
        self.assertIn('3. 子标题', saved_source)

        _, path, package = self.setup_edit()
        h2 = next(b for b in package['blocks'] if b['kind'] == 'h2')
        h3 = next(b for b in package['blocks'] if b['kind'] == 'h3')
        h2['number'] = ''
        h3['runs'][0]['text'] = '子标题'
        self.model.apply_package(package, path, apply=True)
        self.assertIn('gzh-h2-number:', self.md.read_text(encoding='utf-8'))
        self.assertNotIn('>07</span>', self.html.read_text(encoding='utf-8'))
        self.assertIn('子标题', self.md.read_text(encoding='utf-8'))

    def test_explicit_empty_h2_and_h3_runs_remove_heading_rows(self):
        source = '---\ntitle: 标题删除\nrelated: ["[[测试]]"]\n---\n\n# 标题删除\n\n## 一、章节标题\n\n### 1. 子标题\n\n正文保留。\n'
        self.md.write_text(source, encoding='utf-8')
        self.html.write_text(renderer.render(source, 'minimal'), encoding='utf-8')
        _, path, package = self.setup_edit()
        for block in package['blocks']:
            if block['kind'] in {'h2', 'h3'}:
                block['runs'] = []
        self.model.apply_package(package, path, apply=True)
        self.assertNotIn('## 一、章节标题', self.md.read_text(encoding='utf-8'))
        self.assertNotIn('### 1. 子标题', self.md.read_text(encoding='utf-8'))
        self.assertNotIn('章节标题', self.html.read_text(encoding='utf-8'))
        self.assertNotIn('子标题', self.html.read_text(encoding='utf-8'))
        self.assertIn('正文保留', self.md.read_text(encoding='utf-8'))

    def test_micro_heading_keeps_component_type_after_edit(self):
        source = '## 标题\n\n第一，微标题。\n\n正文。\n'
        self.md.write_text(source, encoding='utf-8')
        self.html.write_text(renderer.render(source, 'minimal'), encoding='utf-8')
        _, path, package = self.setup_edit()
        micro = next(b for b in package['blocks'] if b['kind'] == 'micro')
        micro['runs'][0]['text'] = '第一，人工标题。'
        result = self.model.apply_package(package, path)
        self.assertTrue(result['changes'])
        self.model.apply_package(package, path, apply=True)
        self.assertIn('<h4 ', self.html.read_text(encoding='utf-8'))
        self.assertTrue(any(b['kind'] == 'micro' for b in json.loads(path.read_text(encoding='utf-8'))['blocks']))

    def test_metadata_refresh_rejects_body_edits(self):
        _, path, package = self.setup_edit()
        saved = self.model.apply_package(package, path, apply=True)
        state = json.loads(path.read_text(encoding='utf-8'))
        self.md.write_text(self.md.read_text(encoding='utf-8') + '\n不能借同步元数据回写吞掉正文改动。\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '正文|冲突|conflict'):
            self.model.refresh_sync_metadata(path, Path(saved['backup_dir'], 'source.md'), expected_revision=state['revision'],
                                             expected_source_sha256=state['source_sha256'], expected_html_sha256=state['html_sha256'], apply=True)

    def test_multiline_quoted_metadata_cannot_masquerade_as_digest(self):
        self.md.write_text('---\ntitle: "first\ndigest: old\nlast"\nrelated: []\n---\n\n正文。\n', encoding='utf-8')
        self.html.write_text(renderer.render(self.md.read_text(encoding='utf-8'), 'minimal'), encoding='utf-8')
        _, path, package = self.setup_edit()
        self.model.apply_package(package, path, apply=True)
        state = json.loads(path.read_text(encoding='utf-8'))
        backup = self.root / 'sync-before.md'
        backup.write_bytes(self.md.read_bytes())
        self.md.write_text(self.md.read_text(encoding='utf-8').replace('digest: old', 'digest: changed'), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '复杂|多行|conflict'):
            self.model.refresh_sync_metadata(path, backup, expected_revision=state['revision'],
                                             expected_source_sha256=state['source_sha256'], expected_html_sha256=state['html_sha256'], apply=True)


if __name__ == '__main__':
    unittest.main()
