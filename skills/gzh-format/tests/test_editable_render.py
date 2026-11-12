"""人工预览改稿的渲染、样式与源片段映射合同。"""

import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("editable_render_markdown", SCRIPT_DIR / "render_markdown.py")
RENDERER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RENDERER)


def manual(text, red=0, bold=0, extra=""):
    return f'<span data-gzh="manual-style" data-red="{red}" data-bold="{bold}"{extra}>{text}</span>'


class EditableRenderTests(unittest.TestCase):
    def test_audio_preface_keeps_gray_intro_and_later_quote_separate(self):
        for preface in (
            RENDERER.AI_DAILY_AUDIO_PLACEHOLDER,
            '<audio src="https://example.com/episode.mp3" controls></audio>',
            '<mpvoice voice_encode_fileid="example"></mpvoice>',
        ):
            with self.subTest(preface=preface):
                source = preface + '\n\n> 开篇引言\n\n正文。\n\n> 正文观点\n'
                mapping = []
                rendered = RENDERER.render(source, 'minimal', source_map=mapping)
                quotes = [rendered[x['html_start']:x['html_end']] for x in mapping if x['kind'] == 'quote']
                self.assertEqual(len(quotes), 2)
                self.assertIn('background:#f1f2ee;', quotes[0])
                self.assertIn('font-size:13px;', quotes[0])
                self.assertIn('color:#6b7067;', quotes[0])
                self.assertIn('font-weight:400;', quotes[0])
                self.assertNotIn('border-left', quotes[0])
                self.assertNotIn('「', quotes[0])
                self.assertIn('border-left:4px solid #ed7b2f;', quotes[1])

    def test_explicit_opening_hook_retains_gray_background_after_preface(self):
        source = ('音频说明。\n\n<!-- article-hook:start -->\n> '
                  + manual('已保存的引言')
                  + '\n<!-- article-hook:end -->\n\n## 第一章\n\n> 正文引用\n')
        mapping = []
        rendered = RENDERER.render(source, 'minimal', source_map=mapping)
        quotes = [rendered[x['html_start']:x['html_end']] for x in mapping if x['kind'] == 'quote']
        self.assertIn('background:#f1f2ee;', quotes[0])
        self.assertIn('color:#6b7067;font-weight:400;', quotes[0])
        self.assertNotIn('border-left', quotes[0])
        self.assertIn('border-left', quotes[1])

    def test_opening_hook_does_not_override_explicit_manual_emphasis(self):
        source = '> ' + manual('作者显式标红加粗', 1, 1) + '\n'
        rendered = RENDERER.render(source, 'minimal')
        self.assertIn('background:#f1f2ee;', rendered)
        self.assertIn('color:#DC2626;font-weight:800;', rendered)

    def test_h3_keeps_author_numbering_while_h2_keeps_visual_number(self):
        rendered = RENDERER.render("## 一、主标题\n\n### 1、作者小标题\n", "minimal")
        self.assertIn('>主标题</span>', rendered)
        self.assertNotIn('>一、主标题</span>', rendered)
        self.assertIn('>1、作者小标题</span>', rendered)

    def test_manual_red_and_bold_are_four_independent_combinations(self):
        for red in (0, 1):
            for bold in (0, 1):
                with self.subTest(red=red, bold=bold):
                    rendered = RENDERER.render(manual('"User" &amp; AI', red, bold), "minimal")
                    color = "#DC2626" if red else "#4d4f46"
                    weight = "800" if bold else "400"
                    self.assertRegex(rendered, f'color:{color};font-weight:{weight};')
                    self.assertIn('>"User" &amp; AI</span>', rendered)
                    self.assertNotIn("“User”", rendered)

    def test_manual_markup_is_escaped_and_marks_are_retained(self):
        source = manual('&lt;mark data-gzh="semantic-anchor"&gt;**literal**&lt;/mark&gt;', 0, 0,
                        ' data-href="https://example.com/a?x=1&amp;y=2" data-marks="code underline strike highlight"')
        rendered = RENDERER.render(source, "minimal")
        self.assertIn('href="https://example.com/a?x=1&amp;y=2"', rendered)
        self.assertIn("text-decoration:underline line-through;", rendered)
        self.assertIn("font-family:ui-monospace", rendered)
        self.assertIn('&lt;mark data-gzh="semantic-anchor"&gt;**literal**&lt;/mark&gt;', rendered)
        self.assertNotIn('<mark data-gzh="semantic-anchor">', rendered)

    def test_manual_link_can_cancel_red_without_changing_bold(self):
        rendered = RENDERER.render(manual("链接", 0, 1, ' data-href="https://example.com"'), "minimal")
        self.assertIn("color:#576b95;font-weight:800;", rendered)
        self.assertNotIn("color:#DC2626", rendered)

    def test_rejects_nested_or_malformed_manual_markup_and_unsafe_link(self):
        invalid = [
            manual("<b>nested</b>"),
            manual("unsafe", extra=' data-href="javascript:alert(1)"'),
            manual("unknown", extra=' data-marks="blink"'),
            '<span data-gzh="manual-style" data-red="2" data-bold="0">x</span>',
        ]
        for source in invalid:
            with self.subTest(source=source), self.assertRaises(SystemExit):
                RENDERER.render(source, "minimal")

    def test_manual_inline_renders_in_all_editable_block_types(self):
        token = manual("保留手改", 1, 0)
        md = f"## {token}\n\n### 2、{token}\n\n> {token}\n\n- {token}\n\n第一，{token}。\n\n{token}\n"
        mapping = []
        rendered = RENDERER.render(md, "minimal", source_map=mapping)
        self.assertEqual([entry["kind"] for entry in mapping], ["h2", "h3", "quote", "list", "micro", "paragraph"])
        self.assertEqual(rendered.count("color:#DC2626;font-weight:400;"), 6)
        self.assertNotIn("&lt;span data-gzh", rendered)

    def test_manual_quote_does_not_reinsert_deleted_brackets(self):
        rendered = RENDERER.render("正文\n\n> " + manual("作者已删除括号") + "\n", "minimal")
        self.assertNotIn("「", rendered)
        self.assertNotIn("」", rendered)
        self.assertIn(">作者已删除括号</span>", rendered)

    def test_source_map_offsets_include_frontmatter_and_complete_source_lines(self):
        md = ("---\ntitle: 测试\nrelated: []\n---\n\n"
              "## 主标题\n\n### 1、小标题\n\n首行\n第二行\n\n> 引文一\n> 引文二\n\n"
              "- 列表一\n- 列表二\n\n第一，微标题。\n\n```text\n只读代码\n```\n\n"
              "| 表头 |\n| --- |\n| 只读表格 |\n\n![图](https://example.com/a.png)\n")
        expected = [("h2", "## 主标题\n"), ("h3", "### 1、小标题\n"),
                    ("paragraph", "首行\n第二行\n"), ("quote", "> 引文一\n> 引文二\n"),
                    ("list", "- 列表一\n- 列表二\n"), ("micro", "第一，微标题。\n")]
        mapping = []
        rendered = RENDERER.render(md, "minimal", source_map=mapping)
        self.assertEqual(len(mapping), len(expected))
        for entry, (kind, source) in zip(mapping, expected):
            self.assertEqual(entry["kind"], kind)
            self.assertEqual(md[entry["start"]:entry["end"]], source)
            self.assertGreaterEqual(entry["start"], md.index("## 主标题"))
            block = rendered[entry["html_start"]:entry["html_end"]]
            self.assertTrue(block.startswith(("<section", "<p ")))
            self.assertTrue(block.endswith(("</section>", "</p>")))
            self.assertNotIn("\n", block)

    def test_map_collection_does_not_change_rendered_html(self):
        md = "## 主标题\n\n文字\n跨行\n\n- 第一项\n- 第二项\n"
        first_map, second_map = [], []
        plain = RENDERER.render(md, "minimal")
        self.assertEqual(RENDERER.render(md, "minimal", source_map=first_map), plain)
        self.assertEqual(RENDERER.render_minimal(md, source_map=second_map), plain)
        self.assertEqual(first_map, second_map)

    def test_source_map_preserves_crlf_and_final_line_without_newline(self):
        md = "## 主标题\r\n\r\n首行\r\n末行"
        mapping = []
        RENDERER.render(md, "minimal", source_map=mapping)
        self.assertEqual(md[mapping[0]["start"]:mapping[0]["end"]], "## 主标题\r\n")
        self.assertEqual(md[mapping[1]["start"]:mapping[1]["end"]], "首行\r\n末行")
        self.assertEqual(mapping[1]["end"], len(md))

    def test_question_group_map_keeps_internal_but_not_trailing_blank_lines(self):
        md = "第一个问题？\n\n第二个问题？\n\n后续正文。\n"
        mapping = []
        RENDERER.render(md, "minimal", source_map=mapping)
        self.assertEqual(mapping[0]["kind"], "list")
        self.assertEqual(md[mapping[0]["start"]:mapping[0]["end"]], "第一个问题？\n\n第二个问题？\n")
        self.assertEqual(md[mapping[1]["start"]:mapping[1]["end"]], "后续正文。\n")

    def test_manual_revision_skips_coverage_but_still_validates_semantic_markers(self):
        paragraph = "人工已确认这一段不需要自动标红，保存后必须保留作者选择。" * 8
        md = "<!-- gzh-manual-revision:v1 -->\n\n## 主标题\n\n" + paragraph
        rendered = RENDERER.render(md, "minimal", require_semantic_anchors=True)
        self.assertNotIn("color:#DC2626", rendered)
        with self.assertRaises(SystemExit):
            RENDERER.render(md + '\n\n<mark data-gzh="semantic-anchor">不完整', "minimal",
                            require_semantic_anchors=True)

    def test_manual_revision_keeps_existing_generic_anchor_save_compatible(self):
        paragraph = (
            '系统运行记录已经确认这条判断来自旧稿，'
            '<mark data-gzh="semantic-anchor">因此这不是具体判断</mark>，'
            '后续内容继续说明旧稿中的人工标记需要原样保留，不能因为新规则升级而阻断保存。'
            '保存前还会继续核对来源、图片和标题编号，确保历史人工样式不会被新的自动门禁覆盖。'
        )
        legacy = '<!-- gzh-manual-revision:v1 -->\n\n' + paragraph
        rendered = RENDERER.render(legacy, "minimal", require_semantic_anchors=True)
        self.assertIn('因此这不是具体判断', rendered)
        with self.assertRaisesRegex(SystemExit, 'generic lead-in'):
            RENDERER.render(paragraph, "minimal", require_semantic_anchors=True)

    def test_semantic_anchor_cannot_start_a_sentence(self):
        paragraph = (
            '<mark data-gzh="semantic-anchor">句首误标关键词</mark>。'
            '这段正文继续补充上下文，保证它达到语义锚点校验所需的长度，并且只描述测试边界。' * 2
        )
        with self.assertRaisesRegex(SystemExit, 'cannot start a paragraph or sentence'):
            RENDERER.render(paragraph, "minimal")

    def test_semantic_anchor_rejects_generic_leading_words(self):
        paragraph = (
            '这段正文用于验证泛化引导词不能冒充关键词，'
            '<mark data-gzh="semantic-anchor">因此这不是具体判断</mark>，'
            '后面继续补充上下文以满足普通长段落的长度门槛。' * 2
        )
        with self.assertRaisesRegex(SystemExit, 'generic lead-in'):
            RENDERER.render(paragraph, "minimal")


if __name__ == "__main__":
    unittest.main()
