"""标题是独立纯文字状态；保存标题不能改变正文排版。"""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import edit_model
import render_markdown
from wrap_preview import render_preview


class ArticleTitleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.md, self.html = self.root / '真实文件名.md', self.root / 'rendered.html'
        self.path = edit_model.default_manifest(self.html)

    def setup_source(self, source):
        # 夹具可包含 CRLF，写入时保留给定字节，避免 Windows 再转换一次换行。
        self.md.write_bytes(source.encode('utf-8'))
        self.html.write_text(render_markdown.render(source, 'minimal'), encoding='utf-8')
        state = edit_model.build_manifest(self.md, self.html)
        self.path.write_text(json.dumps(state, ensure_ascii=False), encoding='utf-8')
        return state

    def test_frontmatter_title_precedes_h1_and_filename(self):
        state = self.setup_source('---\ntitle: "发布：标题 # 正文"\nrelated: []\n---\n\n# 旧 H1\n\n正文。\n')
        self.assertEqual(state['title'], '发布：标题 # 正文')
        self.assertEqual(edit_model.public_package(state)['title'], state['title'])

    def test_h1_and_markdown_filename_are_fallbacks(self):
        state = self.setup_source('# H1 标题\n\n正文。\n')
        self.assertEqual(state['title'], 'H1 标题')
        state = self.setup_source('正文。\n')
        self.assertEqual(state['title'], '真实文件名')

    def test_title_only_save_updates_title_and_h1_without_reflow(self):
        source = '---\r\ntitle: 旧标题\r\nrelated: []\r\n---\r\n\r\n# 旧标题\r\n\r\n**保留正文**。\r\n'
        self.setup_source(source)
        self.md.write_bytes(source.encode('utf-8'))
        state = edit_model.build_manifest(self.md, self.html)
        self.path.write_text(json.dumps(state, ensure_ascii=False), encoding='utf-8')
        before = self.html.read_bytes()
        package = edit_model.public_package(state)
        package['title'] = '新标题："引号" & <符号> #'
        result = edit_model.apply_package(package, self.path, apply=True)
        self.assertEqual(result['status'], 'saved')
        self.assertEqual(self.html.read_bytes(), before)
        updated = edit_model.read_exact(self.md)
        self.assertIn('# 新标题："引号" & <符号> #\r\n', updated)
        self.assertNotIn('\n', updated.replace('\r\n', ''))
        self.assertEqual(json.loads(self.path.read_text(encoding='utf-8'))['title'], package['title'])
        self.assertEqual(Path(result['backup_dir'], 'source.md').read_bytes(), source.encode('utf-8'))

    def test_no_h1_save_does_not_add_h1_or_rename_file(self):
        state = self.setup_source('---\ntitle: 旧标题\nrelated: []\n---\n\n正文。\n')
        package = edit_model.public_package(state)
        package['title'] = '新标题'
        edit_model.apply_package(package, self.path, apply=True)
        self.assertNotIn('\n# ', self.md.read_text(encoding='utf-8'))
        self.assertTrue(self.md.exists())

    def test_legacy_manifest_and_package_preserve_title(self):
        state = self.setup_source('---\ntitle: 兼容标题\nrelated: []\n---\n\n正文。\n')
        state.pop('title', None)
        self.path.write_text(json.dumps(state), encoding='utf-8')
        loaded = edit_model.load_manifest(self.path)
        self.assertEqual(loaded['title'], '兼容标题')
        package = edit_model.public_package(loaded)
        package.pop('title', None)
        edit_model.apply_package(package, self.path, apply=True)
        self.assertIn('title: 兼容标题', self.md.read_text(encoding='utf-8'))

    def test_invalid_titles_write_nothing(self):
        state = self.setup_source('---\ntitle: 原标题\nrelated: []\n---\n\n正文。\n')
        before = self.md.read_bytes()
        for title in ('', '  ', '跨\n行', '跨\r行', '控制\x00字', '控制\x85字', '控制\x9f字', ['非字符串']):
            with self.subTest(title=title):
                package = edit_model.public_package(state)
                package['title'] = title
                with self.assertRaisesRegex(ValueError, '标题|title'):
                    edit_model.apply_package(package, self.path, apply=True)
                self.assertEqual(self.md.read_bytes(), before)

    def test_yaml_key_trailing_whitespace_does_not_create_duplicate_title(self):
        for key in ('title ', 'title\t'):
            with self.subTest(key=key):
                state = self.setup_source('---\n' + key + ': 原题\nrelated: []\n---\n\n正文。\n')
                self.assertEqual(state['title'], '原题')
                package = edit_model.public_package(state)
                package['title'] = '修改后标题'
                edit_model.apply_package(package, self.path, apply=True)
                self.assertEqual(self.md.read_text(encoding='utf-8').count('title'), 1)
                self.assertEqual(edit_model.build_manifest(self.md, self.html)['title'], '修改后标题')

    def test_comments_and_false_fence_close_never_become_article_h1(self):
        examples = ('<!--\n# 内部注释标题\n-->\n\n正文。\n',
                    '开场正文。\n\n```markdown\n示例。\n```not-a-closing-fence\n# 代码内部标题\n```\n\n正文。\n')
        for source in examples:
            with self.subTest(source=source):
                state = self.setup_source(source)
                self.assertEqual(state['title'], self.md.stem)
                before = self.html.read_bytes()
                package = edit_model.public_package(state)
                package['title'] = '新增发布标题'
                edit_model.apply_package(package, self.path, apply=True)
                self.assertTrue(self.md.read_text(encoding='utf-8').endswith(source))
                self.assertEqual(self.html.read_bytes(), before)

    def test_inline_commented_h1_is_readonly_while_body_stays_editable(self):
        source = '---\ntitle: 原题\nrelated: []\n---\n\n# 原题 <!-- 标题说明 -->\n\n正文。\n'
        state = self.setup_source(source)
        self.assertFalse(state['title_editable'])
        self.assertRegex(state['title_warning'], 'H1|注释')
        package = edit_model.public_package(state)
        package['title'] = '不能只修改元数据的新题'
        with self.assertRaisesRegex(ValueError, 'H1|注释'):
            edit_model.apply_package(package, self.path, apply=True)
        self.assertEqual(self.md.read_text(encoding='utf-8'), source)
        package = edit_model.public_package(state)
        paragraph = next(block for block in package['blocks'] if block['kind'] == 'paragraph')
        paragraph['runs'][0]['text'] = '正文仍可正常修订。'
        edit_model.apply_package(package, self.path, apply=True)
        self.assertIn('# 原题 <!-- 标题说明 -->', self.md.read_text(encoding='utf-8'))
        self.assertIn('正文仍可正常修订。', self.md.read_text(encoding='utf-8'))

    def test_title_template_tokens_are_displayed_as_literal_text(self):
        title = '使用 {{TITLE_READONLY}} 和 {{TITLE_WARNING}} 配置'
        state = self.setup_source('---\ntitle: ' + json.dumps(title, ensure_ascii=False) + '\nrelated: []\n---\n\n正文。\n')
        page = render_preview(self.html.read_text(encoding='utf-8'), 'rendered', state)
        self.assertIn('<title>' + title + ' · 公众号排版预览</title>', page)
        self.assertIn('value="' + title + '"', page)

    def test_complex_title_yaml_edit_is_rejected_without_rewriting(self):
        for metadata in ('title: |\n  复杂标题', 'title: &anchor 复杂标题', 'title: [复杂, 标题]', 'title: 简单开头\n  跨行延续', 'title:\n  缩进标题'):
            with self.subTest(metadata=metadata):
                state = self.setup_source('---\n' + metadata + '\nrelated: []\n---\n\n正文。\n')
                before = self.md.read_bytes()
                package = edit_model.public_package(state)
                package['title'] = '新标题'
                with self.assertRaisesRegex(ValueError, '复杂|YAML|标题'):
                    edit_model.apply_package(package, self.path, apply=True)
                self.assertEqual(self.md.read_bytes(), before)

    def test_quoted_title_keys_and_unclosed_frontmatter_are_readonly(self):
        for source in ('---\n"title": 原题\nrelated: []\n---\n\n正文。\n',
                       "---\n'\u0074itle': 原题\nrelated: []\n---\n\n正文。\n",
                       '---\ntitle: 未闭合元数据\n\n正文。\n'):
            with self.subTest(source=source):
                state = self.setup_source(source)
                self.assertFalse(state['title_editable'])
                before = self.md.read_bytes()
                package = edit_model.public_package(state)
                package['title'] = '不应自动写入的标题'
                with self.assertRaisesRegex(ValueError, '复杂|YAML|闭合'):
                    edit_model.apply_package(package, self.path, apply=True)
                self.assertEqual(self.md.read_bytes(), before)

    def test_title_from_empty_frontmatter_and_legacy_session_keep_current_value(self):
        self.setup_source('---\nrelated: []\n---\n\n正文。\n')
        session = edit_model.EditSession(self.path)
        package = session.public_package()
        package['title'] = '添加到已有元数据的标题'
        first = session.save(package)
        self.assertIn('related: []', self.md.read_text(encoding='utf-8'))
        legacy = first['package']
        legacy.pop('title')
        legacy['blocks'][0]['runs'][0]['text'] = '旧客户端只修改正文。'
        session.save(legacy)
        self.assertEqual(session.public_package()['title'], '添加到已有元数据的标题')

    def test_saved_title_can_be_undone_saved_and_reopened(self):
        self.setup_source('---\ntitle: 原标题\nrelated: []\n---\n\n正文。\n')
        session = edit_model.EditSession(self.path)
        initial = session.public_package()
        package = copy.deepcopy(initial)
        package['title'] = '加工后的标题'
        saved = session.save(package)
        self.assertEqual(saved['package']['title'], package['title'])
        restored = copy.deepcopy(saved['package'])
        restored['title'] = initial['title']
        session.save(restored)
        reopened = edit_model.EditSession(self.path)
        self.assertEqual(reopened.public_package()['title'], '原标题')
        self.assertEqual(reopened.public_package()['revision'], 2)

    def test_preview_title_is_outside_body_and_escaped(self):
        state = self.setup_source('---\ntitle: "标题 <符号>"\nrelated: []\n---\n\n正文。\n')
        page = render_preview(self.html.read_text(encoding='utf-8'), 'rendered', state)
        self.assertIn('id="gzh-title"', page)
        self.assertIn('标题 &lt;符号&gt;', page)
        self.assertLess(page.index('id="gzh-title"'), page.index('id="gzh-content"'))
        self.assertNotIn('gzhCopyTitleBtn', page)
        self.assertNotIn('标题单独粘贴到公众号标题栏', page)


if __name__ == '__main__':
    unittest.main()
