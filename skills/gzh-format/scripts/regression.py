#!/usr/bin/env python3
"""Run a small regression suite for gzh-format."""

import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

from _stdio import configure_utf8_stdio

configure_utf8_stdio()

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = Path(tempfile.mkdtemp(prefix="gzh-format-regression-"))
SAMPLE = ROOT / "assets" / "sample-article.md"
STRESS = ROOT / "tests" / "fixtures" / "stress-markdown.md"
AI_DAILY = ROOT / "tests" / "fixtures" / "ai-daily-markdown.md"
SEMANTIC_HIGHLIGHTS = ROOT / "tests" / "fixtures" / "semantic-highlights-markdown.md"
AUTHOR_FOOTER = ROOT / "tests" / "fixtures" / "author-footer-markdown.md"
AUTHOR_BIO = (
    "艾笑：不安分的前大学计算机教师，在互联网里扑腾十余年的创业狗，"
    "也是横跨技术、商业与人性的 AI Native 实践者兼教练。"
    "有过过亿营收的创业实战，也踩过坑、吃过屎；比起追热点，"
    "更喜欢把复杂问题拆成能够稳定交付的系统。"
    "3 分现实主义、4 分理想主义、2 分幽默，再加 4 分对人生和自然的诗意感受力，"
    "在荒谬的真相中依然保持热爱。人生下半场，想和一群清醒、有趣的人一起，"
    "让 AI 好好干活，让我们好好生活。"
)
AUTHOR_ROADMAP_ACTION = "点击查看： 成为 AI Native 的进阶地图"
AUTHOR_CONTACT_ACTION = "私信发送： 公众号主页私信“联系我”，更多资料、深度链接交流、一起玩。"
AUTHOR_END_LINE = "────────"
AUTHOR_BIO_EMPHASIS = "让 AI 好好干活，让我们好好生活。"
AUTHOR_ROADMAP_URL = (
    "https://mp.weixin.qq.com/s?__biz=MzkxMTc0MjQ2MA%3D%3D"
    "&mid=2247484737&idx=1&sn=8b1ea66df383ce5da4952f906e3ae120"
)


class ParagraphTextCollector(HTMLParser):
    """收集段落纯文本，用于证明新增样式没有改写原句。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.current = []
        self.paragraphs = []

    def handle_starttag(self, tag, attrs):
        if tag == "p":
            self.depth += 1

    def handle_endtag(self, tag):
        if tag != "p" or self.depth == 0:
            return
        self.depth -= 1
        if self.depth == 0:
            self.paragraphs.append("".join(self.current))
            self.current = []

    def handle_data(self, data):
        if self.depth:
            self.current.append(data)


def run(cmd):
    print("+ " + " ".join(str(c) for c in cmd))
    subprocess.run([str(c) for c in cmd], check=True)


def run_expect_failure(cmd, expected_error):
    print("+ expect failure: " + " ".join(str(c) for c in cmd))
    result = subprocess.run(
        [str(c) for c in cmd],
        check=False,
        capture_output=True,
        text=True,
        encoding='utf-8',
    )
    if result.returncode == 0:
        raise AssertionError(f"command unexpectedly succeeded: {cmd}")
    combined = result.stdout + result.stderr
    if expected_error not in combined:
        raise AssertionError(
            f"missing expected error {expected_error!r} in command output: {combined!r}"
        )


def assert_contains(path, needle):
    text = path.read_text(encoding="utf-8")
    if needle not in text:
        raise AssertionError(f"missing {needle!r} in {path}")


def assert_not_contains(path, needle):
    text = path.read_text(encoding="utf-8")
    if needle in text:
        raise AssertionError(f"unexpected {needle!r} in {path}")


def paragraph_texts(path):
    collector = ParagraphTextCollector()
    collector.feed(path.read_text(encoding="utf-8"))
    return collector.paragraphs


def main():
    # 保存回填是共享离线能力，常规回归必须覆盖，不依赖浏览器开发依赖。
    run([sys.executable, '-m', 'unittest', 'discover', '-s', str(ROOT / 'tests'), '-p', 'test_*.py'])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    html = OUT_DIR / "sample-minimal.html"
    preview = OUT_DIR / "sample-minimal_预览.html"
    stress_html = OUT_DIR / "stress-minimal.html"
    stress_preview = OUT_DIR / "stress-minimal_预览.html"
    ai_daily_html = OUT_DIR / "ai-daily-minimal.html"
    ai_daily_preview = OUT_DIR / "ai-daily-minimal_预览.html"
    semantic_html = OUT_DIR / "semantic-highlights-minimal.html"
    semantic_preview = OUT_DIR / "semantic-highlights-minimal_预览.html"
    author_footer_html = OUT_DIR / "author-footer-minimal.html"
    author_footer_preview = OUT_DIR / "author-footer-minimal_预览.html"
    raw_ai_daily = OUT_DIR / "20260714-AI日报.md"

    run([sys.executable, ROOT / "scripts" / "component_lint.py", ROOT])
    run([sys.executable, ROOT / "scripts" / "render_markdown.py", SAMPLE, html])
    run([sys.executable, ROOT / "scripts" / "validate_gzh_html.py", html])
    run([sys.executable, ROOT / "scripts" / "wrap_preview.py", html, preview])
    run([sys.executable, ROOT / "scripts" / "render_markdown.py", STRESS, stress_html])
    run([sys.executable, ROOT / "scripts" / "validate_gzh_html.py", stress_html])
    run([sys.executable, ROOT / "scripts" / "wrap_preview.py", stress_html, stress_preview])
    run(
        [
            sys.executable,
            ROOT / "scripts" / "render_markdown.py",
            AI_DAILY,
            ai_daily_html,
            "--theme",
            "minimal",
            "--mode",
            "ai-daily",
        ]
    )
    run([sys.executable, ROOT / "scripts" / "validate_gzh_html.py", ai_daily_html])
    run([sys.executable, ROOT / "scripts" / "wrap_preview.py", ai_daily_html, ai_daily_preview])
    run(
        [
            sys.executable,
            ROOT / "scripts" / "render_markdown.py",
            SEMANTIC_HIGHLIGHTS,
            semantic_html,
            "--require-semantic-anchors",
        ]
    )
    run([sys.executable, ROOT / "scripts" / "validate_gzh_html.py", semantic_html])
    run([sys.executable, ROOT / "scripts" / "wrap_preview.py", semantic_html, semantic_preview])
    run([sys.executable, ROOT / "scripts" / "render_markdown.py", AUTHOR_FOOTER, author_footer_html])
    run([sys.executable, ROOT / "scripts" / "validate_gzh_html.py", author_footer_html])
    run(
        [
            sys.executable,
            ROOT / "scripts" / "wrap_preview.py",
            author_footer_html,
            author_footer_preview,
        ]
    )
    run_expect_failure(
        [sys.executable, ROOT / "scripts" / "render_markdown.py", STRESS, "--target", "pudding"],
        "unrecognized arguments: --target",
    )
    raw_ai_daily.write_text(AI_DAILY.read_text(encoding="utf-8"), encoding="utf-8")
    run_expect_failure(
        [sys.executable, ROOT / "scripts" / "render_markdown.py", raw_ai_daily],
        "raw AI daily is not a WeChat body",
    )

    invalid_semantic_cases = {
        "sentence-start": (
            (
                '<mark data-gzh="semantic-anchor">句首误标关键词</mark>。'
                + (
                    "这段正文继续补充上下文，保证它达到语义锚点校验所需的长度，并且只描述测试边界。"
                    "后续文字继续补足长度，但不再增加其它标记。"
                )
                * 3
            ),
            "cannot start a paragraph or sentence",
        ),
        "generic-leading": (
            (
                "这段正文用于验证泛化引导词不能冒充关键词，"
                '<mark data-gzh="semantic-anchor">因此这不是具体判断</mark>，'
                + (
                    "后面继续补充上下文以满足普通长段落的长度门槛。"
                    "后续文字继续补足长度，但只保留这一处锚点。"
                )
                * 3
            ),
            "generic lead-in",
        ),
        "missing-anchor": (
            "这是一段达到长段落门槛的普通正文，用于验证排版编排不能漏掉红色扫读锚点。"
            "段落继续补充必要上下文，让可见字符数稳定超过一百二十个，同时保持为普通正文，"
            "没有标题、引用、代码、列表、图片或其它结构语义。"
            "如果这个段落没有任何语义锚点，读者面对连续论述时仍然找不到重点，"
            "因此渲染流程必须拒绝并要求编排层从原句中选择一到两个完整短语。",
            "requires 1-2 semantic anchors",
        ),
        "short": (
            '短段落只含<mark data-gzh="semantic-anchor">错误锚点</mark>。',
            "at least 60 visible characters",
        ),
        "too-many": (
            "这是一段足够长的普通正文，用于验证每段锚点数量上限。"
            "它会重复补充上下文，确保段落长度达到门槛，同时保持所有文字都属于测试说明。"
            "排版流程不能因为段落很长就把多个短语全部染红，"
            '<mark data-gzh="semantic-anchor">第一个锚点</mark>、'
            '<mark data-gzh="semantic-anchor">第二个锚点</mark>和'
            '<mark data-gzh="semantic-anchor">第三个锚点</mark>同时出现时必须拒绝。'
            "后续文字继续补足长度，但不能改变每段最多两个语义锚点的约束，也不能把整段当成强调区。",
            "at most 2 semantic anchors",
        ),
        "nested-bold": (
            "这是一段足够长的普通正文，用于验证语义锚点不能和普通加粗发生嵌套。"
            "测试会继续补充上下文，让段落达到长段落门槛，而且内容始终只是描述验证目的。"
            "如果把**"
            '<mark data-gzh="semantic-anchor">嵌套冲突短语</mark>'
            "**同时当作普通加粗和红色锚点，最终 HTML 会产生不必要的嵌套标签。"
            "因此 renderer 必须在装配前拒绝这种输入，并要求编排层重新选择没有显式标记的原文短语。",
            "cannot overlap existing inline markup",
        ),
        "heading": (
            '### 标题里的<mark data-gzh="semantic-anchor">错误锚点</mark>',
            "only allowed in long ordinary body paragraphs",
        ),
        "nested-link": (
            "这是一段足够长的普通正文，用于验证链接文本不能再次套入语义锚点。"
            "链接已经拥有独立的点击语义和颜色，如果额外嵌套红色加粗，会让公众号样式难以预测。"
            "所以这段继续补足必要长度，并放入["
            '<mark data-gzh="semantic-anchor">链接内锚点</mark>'
            "](https://example.com/conflict)作为错误示例。"
            "renderer 应该稳定拒绝，而不是在最终 HTML 阶段猜测应该保留链接还是红色强调。",
            "cannot overlap existing inline markup",
        ),
        "document-density": (
            "第一段用于验证全文标红比例限制。这里持续补充普通说明文字，让单段长度达到门槛，"
            "但所有内容仍然只是测试上下文，不承载新的事实或观点。排版时选择"
            '<mark data-gzh="semantic-anchor">第一段足够完整且较长的关键判断短语</mark>'
            "作为原文锚点，后面继续补足正文长度，确保单段比例本身没有超过百分之十六。"
            "这一段的末尾再补充一些文字，让边界计算稳定且容易复现。\n\n"
            "第二段同样用于验证全文标红比例限制。这里继续补充普通说明文字，让单段长度达到门槛，"
            "但所有内容仍然只是测试上下文，不承载新的事实或观点。排版时选择"
            '<mark data-gzh="semantic-anchor">第二段足够完整且较长的关键判断短语</mark>'
            "作为原文锚点，后面继续补足正文长度，确保单段比例本身没有超过百分之十六。"
            "这一段的末尾再补充一些文字，让边界计算稳定且容易复现。\n\n"
            "第三段继续用于验证全文标红比例限制。这里仍然补充普通说明文字，让单段长度达到门槛，"
            "但所有内容仍然只是测试上下文，不承载新的事实或观点。排版时选择"
            '<mark data-gzh="semantic-anchor">第三段足够完整且较长的关键判断短语</mark>'
            "作为原文锚点，后面继续补足正文长度，确保单段比例本身没有超过百分之十六。"
            "这一段的末尾再补充一些文字，让边界计算稳定且容易复现。",
            "8% of the document",
        ),
    }
    for name, (body, expected_error) in invalid_semantic_cases.items():
        source = OUT_DIR / f"semantic-invalid-{name}.md"
        invalid_output = OUT_DIR / f"semantic-invalid-{name}.html"
        source.write_text(f"# 测试\n\n## 正文\n\n{body}\n", encoding="utf-8")
        run_expect_failure(
            [
                sys.executable,
                ROOT / "scripts" / "render_markdown.py",
                source,
                invalid_output,
                "--require-semantic-anchors",
            ],
            expected_error,
        )

    missing_section_anchor_source = OUT_DIR / "semantic-missing-section-anchor.md"
    missing_section_anchor_output = OUT_DIR / "semantic-missing-section-anchor.html"
    missing_section_anchor_source.write_text(
        "# 测试\n\n"
        "这是一段足够长的序言，用于确认文章开场已经设置"
        '<mark data-gzh="semantic-anchor">序言扫读锚点</mark>'
        "。后续继续补充中性说明，让可见字符数稳定超过长段落门槛，"
        "同时保持锚点简短、连续且来自原文。读者进入文章时能够先抓住核心判断，"
        "而不是面对一整屏没有层次的灰黑文字。这里再补充一段关于开场阅读节奏的说明，"
        "确保旧版按单段长度执行的门禁不会先于章节覆盖检查触发，测试才能准确验证新增行为。\n\n"
        "## 第一章\n\n"
        "第一章包含多段完整论述，在手机上已经形成明显的大块内容，"
        "但这里故意不放任何红色扫读锚点，用来复现章节之间视觉覆盖不均的问题。"
        "即使每个自然段都没有达到一百二十字，整章也不能因此完全失去重点。\n\n"
        "## 第二章\n\n"
        "第二章同样是一段足够长的正文，并且已经包含"
        '<mark data-gzh="semantic-anchor">第二章扫读锚点</mark>'
        "。后续继续补充必要上下文，让可见字符数稳定超过长段落门槛，"
        "同时保持事实顺序和原句不变。这个章节应当通过覆盖检查，"
        "从而把失败准确定位到完全没有红字的第一章。这里继续补足与章节覆盖有关的中性说明，"
        "确保第二章在旧版单段长度规则下也是合法输入，不会掩盖真正需要修复的缺失章节问题。\n",
        encoding="utf-8",
    )
    run_expect_failure(
        [
            sys.executable,
            ROOT / "scripts" / "render_markdown.py",
            missing_section_anchor_source,
            missing_section_anchor_output,
            "--require-semantic-anchors",
        ],
        "section '第一章' requires at least 1 semantic anchor",
    )

    section_anchor_in_medium_paragraph_source = (
        OUT_DIR / "semantic-section-anchor-in-medium-paragraph.md"
    )
    section_anchor_in_medium_paragraph_output = (
        OUT_DIR / "semantic-section-anchor-in-medium-paragraph.html"
    )
    section_anchor_in_medium_paragraph_source.write_text(
        "# 测试\n\n"
        "## 第一章\n\n"
        "这一章的普通正文没有达到一百二十字，但在公众号手机端已经形成明显内容块，"
        "因此允许从原句中选择"
        '<mark data-gzh="semantic-anchor">本章核心判断</mark>'
        "作为扫读锚点。后续保留完整说明，并确保整段达到六十个可见字符。\n",
        encoding="utf-8",
    )
    run(
        [
            sys.executable,
            ROOT / "scripts" / "render_markdown.py",
            section_anchor_in_medium_paragraph_source,
            section_anchor_in_medium_paragraph_output,
            "--require-semantic-anchors",
        ]
    )

    many_anchor_source = OUT_DIR / "semantic-many-covered-paragraphs.md"
    many_anchor_output = OUT_DIR / "semantic-many-covered-paragraphs.html"
    many_anchor_body = "\n\n".join(
        (
            f"第{index:02d}段用于验证每个长段落都能拥有自己的红色扫读锚点。"
            "这一段持续补充普通说明文字，让可见字符数稳定达到长段落门槛，"
            "同时确保锚点本身只占很小比例，不会触发段落或全文密度限制。"
            "排版流程应该保留全部原句和事实顺序，只把"
            f'<mark data-gzh="semantic-anchor">第{index:02d}个锚点</mark>'
            "映射为固定红色加粗。后续继续补充一些中性说明，"
            "让每一段都具备相同结构，并证明长文不再受固定八个锚点的数量限制。"
        )
        for index in range(1, 10)
    )
    many_anchor_source.write_text(
        f"# 测试\n\n## 正文\n\n{many_anchor_body}\n",
        encoding="utf-8",
    )
    run(
        [
            sys.executable,
            ROOT / "scripts" / "render_markdown.py",
            many_anchor_source,
            many_anchor_output,
            "--require-semantic-anchors",
        ]
    )

    invalid_author_footer_cases = {
        "missing-end": (
            "<!-- gzh-author-footer:start -->\n"
            f"{AUTHOR_BIO}\n",
            "author footer end marker missing",
        ),
        "multiple-paragraphs": (
            "<!-- gzh-author-footer:start -->\n"
            f"{AUTHOR_BIO}\n\n"
            "这里不应该出现第二段作者介绍。\n"
            "<!-- gzh-author-footer:end -->\n",
            "author footer must contain exactly one paragraph",
        ),
    }
    for name, (body, expected_error) in invalid_author_footer_cases.items():
        source = OUT_DIR / f"author-footer-invalid-{name}.md"
        invalid_output = OUT_DIR / f"author-footer-invalid-{name}.html"
        source.write_text(f"# 测试\n\n## 正文\n\n正文。\n\n{body}", encoding="utf-8")
        run_expect_failure(
            [
                sys.executable,
                ROOT / "scripts" / "render_markdown.py",
                source,
                invalid_output,
            ],
            expected_error,
        )

    assert_contains(html, '<span leaf="" style="display:block;font-family:')
    assert_contains(html, "font-size:54px;font-weight:900;color:#23251d")
    assert_contains(html, "text-align:left")
    assert_contains(html, 'letter-spacing:0.5px;">01</span>')
    assert_not_contains(html, "PART")
    assert_not_contains(html, "CASE NOTES")
    assert_not_contains(html, "<script")
    assert_not_contains(html, "gzhCopyBtn")
    assert_contains(preview, 'id="gzhCopyBtn"')
    assert_contains(preview, 'id="gzh-content"')
    assert_contains(preview, html.read_text(encoding="utf-8"))

    assert_contains(stress_html, "第二行允许换行，但中间不能出现空白行。")
    assert_contains(stress_html, "</strong><span leaf=\"\"> 应该保留加粗。</span><br>")
    assert_not_contains(stress_html, "“开头引言")
    assert_not_contains(stress_html, "<br><br>")

    assert_contains(stress_html, "border-bottom:2px solid #ed7b2f")
    assert_contains(stress_html, "font-size:15px;line-height:1.9;text-align:justify;color:#4d4f46")
    assert_contains(
        stress_html,
        '<p style="margin:0 0 18px;font-size:15px;line-height:1.9;'
        'text-align:justify;color:#4d4f46;padding:0 8px;">'
        '<span leaf="">比如用户说「公众号排版」时触发。</span></p>',
    )
    assert_contains(stress_html, "text-decoration:line-through")
    assert_contains(stress_html, "inline_code")
    assert_contains(stress_html, 'href="https://aixiaoai.cloud/cases/demo"')
    assert_not_contains(stress_html, "[可点击链接](https://aixiaoai.cloud/cases/demo)")
    assert_contains(stress_html, "display:flex;background:#eeefe9")
    assert_contains(stress_html, "<span leaf=\"\">-</span>")
    assert_contains(stress_html, "比如 Markdown 到 HTML 的基础转换。")
    assert_contains(stress_html, "这个需求值得做吗？")
    assert_contains(stress_html, "该放在哪一层？")
    assert_contains(stress_html, "生成后怎么验证？")
    assert_contains(stress_html, "min-width:34px")
    assert_contains(stress_html, "<span leaf=\"\">03</span>")
    assert_contains(stress_html, "font-size:18px")
    assert_not_contains(stress_html, "平台标题不进入正文")
    assert_not_contains(stress_html, "==浅底高亮==")
    assert_not_contains(stress_html, "<u>显式下划线</u>")
    assert_not_contains(stress_html, "++双加号下划线++")
    assert_not_contains(stress_html, "~~旧说法~~")
    assert_contains(
        stress_html,
        '<strong style="color:#DC2626;font-weight:800;">'
        '<span leaf="">学习 AI 底层能力和实操干货</span></strong>',
    )
    assert_not_contains(stress_html, "<script")
    assert_not_contains(stress_html, "gzhCopyBtn")
    assert_contains(stress_preview, 'id="gzhCopyBtn"')
    assert_contains(stress_preview, stress_html.read_text(encoding="utf-8"))

    assert_not_contains(ai_daily_html, "微信原生音频位")
    assert_not_contains(ai_daily_html, "请在公众号后台插入本期音频后删除此占位")
    assert_not_contains(ai_daily_html, "border:1px dashed")
    assert_contains(ai_daily_html, "以下链接仅作信息来源和延伸阅读，整理来自青影星球，版权归原作者及原发布账号所有。")
    assert_not_contains(ai_daily_html, "参考资料整理来自青影星球</span>")
    assert_contains(ai_daily_html, '<span leaf=""><br></span>')
    assert_not_contains(ai_daily_html, "<audio")
    assert_not_contains(ai_daily_html, ".mp3")
    assert_contains(ai_daily_html, "font-size:13px;font-weight:700")
    assert_contains(ai_daily_html, "font-size:11px;line-height:1.7;color:#9a9c93")
    assert_contains(ai_daily_html, "border-top:1px solid #e3e4de")
    assert_contains(ai_daily_html, "企业 AI 落地观察")
    assert_contains(ai_daily_html, 'href="https://example.com/source-1"')
    assert_contains(ai_daily_html, 'letter-spacing:0.5px;">04</span>')
    assert_contains(
        ai_daily_html,
        'font-size:23px;font-weight:900;color:#23251d;line-height:1.35;'
        'letter-spacing:0;text-align:left;">一号位工程：企业 AI 不是普通采购</span>',
    )
    assert_not_contains(ai_daily_html, '>01 一号位工程：企业 AI 不是普通采购</span>')
    assert_not_contains(ai_daily_html, 'letter-spacing:0.5px;">05</span>')
    assert_not_contains(
        ai_daily_html,
        'font-size:23px;font-weight:900;color:#23251d;line-height:1.35;letter-spacing:0;'
        'text-align:left;"><span leaf="">今日参考资料',
    )
    assert_contains(ai_daily_preview, 'id="gzhCopyBtn"')
    assert_contains(ai_daily_preview, ai_daily_html.read_text(encoding="utf-8"))

    semantic_source = SEMANTIC_HIGHLIGHTS.read_text(encoding="utf-8")
    semantic_long_plain = (
        semantic_source.split("## 长段落只提炼原文短语\n\n", 1)[1]
        .split("\n\n", 1)[0]
        .replace('<mark data-gzh="semantic-anchor">', "")
        .replace("</mark>", "")
    )
    semantic_paragraphs = paragraph_texts(semantic_html)
    if semantic_long_plain not in semantic_paragraphs:
        raise AssertionError("semantic highlighting changed the original long paragraph text")
    assert_contains(
        semantic_html,
        '<strong style="color:#DC2626;font-weight:800;">'
        '<span leaf="">最关键的判断短语</span></strong>',
    )
    assert_contains(
        semantic_html,
        '<strong style="color:#DC2626;font-weight:800;">'
        '<span leaf="">能够独立理解的结果</span></strong>',
    )
    assert_contains(
        semantic_html,
        '<strong style="color:#DC2626;font-weight:800;">'
        '<span leaf="">原文关键短语</span></strong>',
    )
    assert_contains(
        semantic_html,
        '<strong style="color:#DC2626;font-weight:800;">'
        '<span leaf="">学习 AI 底层能力和实操干货</span></strong>',
    )
    assert_contains(semantic_html, "短段落保持原样，不自动标红。")
    assert_not_contains(
        semantic_html,
        '<strong style="color:#DC2626;font-weight:800;">'
        '<span leaf="">短段落保持原样，不自动标红。</span></strong>',
    )
    assert_contains(semantic_html, 'href="https://example.com/semantic-anchor"')
    assert_contains(semantic_html, "border-bottom:2px solid #ed7b2f")
    assert_contains(semantic_html, "inline_code")
    assert_not_contains(semantic_html, '<mark data-gzh="semantic-anchor">')
    assert_contains(
        semantic_html,
        "&lt;mark data-gzh=\"semantic-anchor\"&gt;代码里的示例标记保持代码文本&lt;/mark&gt;",
    )
    assert_contains(semantic_preview, 'id="gzhCopyBtn"')
    assert_contains(semantic_preview, semantic_html.read_text(encoding="utf-8"))

    assert_contains(author_footer_html, '<span leaf="">END</span>')
    author_footer_text = author_footer_html.read_text(encoding="utf-8")
    if author_footer_text.count(f'<span leaf="">{AUTHOR_END_LINE}</span>') != 2:
        raise AssertionError(
            "author END divider must render two non-empty text lines that survive paste cleanup"
        )
    assert_contains(
        author_footer_html,
        'data-gzh="author-footer" style="margin:42px 0 0;"',
    )
    assert_not_contains(author_footer_html, 'style="margin:42px 8px 0;"')
    assert_contains(author_footer_html, '<section style="padding:0 8px;">')
    assert_contains(author_footer_html, "font-size:13px;line-height:1.9;color:#8c8c8c")
    assert_contains(
        author_footer_html,
        '<strong style="background:#c7254e;color:#ffffff;font-weight:700;'
        'padding:1px 4px;">'
        f'<span leaf="">{AUTHOR_BIO_EMPHASIS}</span></strong>',
    )
    assert_not_contains(author_footer_html, "一起吧。")
    assert_contains(
        author_footer_html,
        f'href="{AUTHOR_ROADMAP_URL.replace("&", "&amp;")}"',
    )
    assert_contains(
        author_footer_html,
        "color:#c7254e;font-weight:700;text-decoration:none;"
        "border-bottom:1px solid #c7254e",
    )
    assert_not_contains(author_footer_html, "color:#576b95")
    assert_not_contains(author_footer_html, "查看关于走向 AI Native 的进阶地图")
    assert_not_contains(author_footer_html, "公众号主页对话框发送「联系我」。")
    assert_not_contains(author_footer_html, 'href=""')
    assert_not_contains(author_footer_html, "<!-- gzh-author-footer:")
    footer_paragraphs = paragraph_texts(author_footer_html)
    if footer_paragraphs.count(AUTHOR_BIO) != 1:
        raise AssertionError("author bio must render as exactly one paragraph")
    if footer_paragraphs.count(AUTHOR_ROADMAP_ACTION) != 1:
        raise AssertionError("author roadmap action must render exactly once")
    if footer_paragraphs.count(AUTHOR_CONTACT_ACTION) != 1:
        raise AssertionError("author contact action must render exactly once")
    if footer_paragraphs.index(AUTHOR_ROADMAP_ACTION) > footer_paragraphs.index(AUTHOR_CONTACT_ACTION):
        raise AssertionError("author roadmap action must render before contact action")
    if author_footer_text.count("<span leaf=\"\">END</span>") != 1:
        raise AssertionError("author footer must render exactly one END divider")
    assert_contains(author_footer_preview, 'id="gzhCopyBtn"')
    assert_contains(author_footer_preview, author_footer_html.read_text(encoding="utf-8"))

    copyable_html = OUT_DIR / "copyable-prompt.html"
    run([sys.executable, ROOT / "scripts" / "render_markdown.py",
         ROOT / "tests" / "fixtures" / "copyable-prompt-markdown.md", copyable_html])
    run([sys.executable, ROOT / "scripts" / "validate_gzh_html.py", copyable_html])
    assert_contains(copyable_html, '<span leaf="">prompt</span>')
    assert_contains(copyable_html, "background:#1E293B")
    assert_contains(copyable_html, "检查现有同步工具支持哪种代理。")
    assert_contains(copyable_html, "连接失败就停止，不改走其他网络。")
    assert_contains(copyable_html, "普通引用和章节过渡仍然保留引用样式。")
    assert_contains(copyable_html, "ssh -N -D 127.0.0.1:1080 example-host")
    assert_not_contains(copyable_html, "「检查现有同步工具")

    print(f"regression ok: {html}")
    print(f"preview: {preview}")
    print(f"stress regression ok: {stress_html}")
    print(f"stress preview: {stress_preview}")
    print(f"ai-daily regression ok: {ai_daily_html}")
    print(f"ai-daily preview: {ai_daily_preview}")
    print(f"semantic highlight regression ok: {semantic_html}")
    print(f"semantic highlight preview: {semantic_preview}")
    print(f"author footer regression ok: {author_footer_html}")
    print(f"author footer preview: {author_footer_preview}")


if __name__ == "__main__":
    main()
