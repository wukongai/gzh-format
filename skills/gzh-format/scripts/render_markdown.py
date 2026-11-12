#!/usr/bin/env python3
"""Render Markdown into WeChat Official Account compatible HTML.

This deterministic renderer covers the default `minimal` theme. Other themes in
`themes/<theme-id>/components.md` are complete component libraries for agent-led
assembly and can get dedicated render adapters later without changing SKILL.md.
"""

import argparse
import html
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

from _stdio import configure_utf8_stdio

configure_utf8_stdio()

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_THEME = "minimal"
DEFAULT_MODE = "default"
SUPPORTED_MODES = {DEFAULT_MODE, "ai-daily"}
AI_DAILY_REFERENCE_HEADING = "今日参考资料"
AI_DAILY_REFERENCE_ATTRIBUTION = "以下链接仅作信息来源和延伸阅读，整理来自青影星球，版权归原作者及原发布账号所有。"
# 旧稿源文里单独写的版权说明行,已被上面的单行归属句合并,解析时忽略。
AI_DAILY_REFERENCE_LEGACY_INTRO_MARKERS = ("仅作信息来源", "版权归原作者")
AI_DAILY_AUDIO_PLACEHOLDER = "【请在此处插入本期 MP3 音频】"
RAW_AI_DAILY_FILENAME = re.compile(r"^\d{8}-AI日报\.md$")
PREPARED_AI_DAILY_FILENAME = re.compile(r"^\d{8}-AI日报-公众号正文\.md$")
SECTION_TITLES = re.compile(r"^[一二三四五六七八九十]+[、.．]\s*")
LIST_ITEM = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)、]\s+)(.*)$")
MICRO_HEADING = re.compile(
    r"^第[一二三四五六七八九十]+(?:[，,、]\s*[^。！？!?]{2,80}[。！？!?]?|层是[^。！？!?]{2,40}[。！？!?]?)$"
)
EXAMPLE_ITEM = re.compile(r"^(?:比如|例如|譬如)(?![：:]\s*$).+")
ACTION_ITEM = re.compile(r"^(?:新增|复制|修改|登记|运行|校验|生成|同步|回写|上传|创建|删除|补|跑|在)[^。！？!?]{2,28}[。！!]$")
QUESTION_ITEM = re.compile(r"^[^。！？!?]{2,120}[？?]$")
FIXED_RED_BOLD_PHRASE = re.compile(r"学习\s*AI\s*底层能力和实操干货")
FIXED_RED_BOLD_COLOR = "#DC2626"
SEMANTIC_ANCHOR_OPEN = '<mark data-gzh="semantic-anchor">'
SEMANTIC_ANCHOR_CLOSE = "</mark>"
SEMANTIC_ANCHOR = re.compile(
    re.escape(SEMANTIC_ANCHOR_OPEN) + r"(.+?)" + re.escape(SEMANTIC_ANCHOR_CLOSE)
)
MANUAL_REVISION_MARKER = "<!-- gzh-manual-revision:v1 -->"
MANUAL_STYLE = re.compile(
    r'<span data-gzh="manual-style" data-red="(?P<red>[01])" data-bold="(?P<bold>[01])"'
    r'(?: data-href="(?P<href>[^"<>\n]*)")?'
    r'(?: data-marks="(?P<marks>[^"<>\n]*)")?>(?P<text>[^<>\n]*)</span>'
)
MANUAL_STYLE_ATTRIBUTE = re.compile(r'<span\b[^>]*\bdata-gzh\s*=\s*[\"\']manual-style\b')
MANUAL_STYLE_MARKS = {"code", "underline", "strike", "highlight"}
PROTECTED_INLINE = re.compile(
    r"(" + MANUAL_STYLE.pattern + r"|!?\[[^\]]+\]\([^)]+\)|`.+?`|\*\*.+?\*\*|==.+?==|"
    r"<u>.+?</u>|\+\+.+?\+\+|~~.+?~~)"
)
INLINE_MARKUP_PATTERN = re.compile(
    r"(" + MANUAL_STYLE.pattern + r"|<mark data-gzh=\"semantic-anchor\">.+?</mark>|!?\[[^\]]+\]\([^)]+\)|"
    r"`.+?`|\*\*.+?\*\*|==.+?==|<u>.+?</u>|\+\+.+?\+\+|~~.+?~~)"
)
SEMANTIC_ANCHOR_MIN_PARAGRAPH_CHARS = 60
SEMANTIC_ANCHOR_LONG_PARAGRAPH_CHARS = 120
SEMANTIC_ANCHOR_MIN_PHRASE_CHARS = 4
SEMANTIC_ANCHOR_MAX_PHRASE_CHARS = 18
SEMANTIC_ANCHOR_MAX_PER_PARAGRAPH = 2
SEMANTIC_ANCHOR_MAX_RATIO = 0.16
SEMANTIC_ANCHOR_MAX_DOCUMENT_RATIO = 0.08
# 扫读锚点必须落在判断句内部；句首连接词和泛化主语本身不是关键词。
SEMANTIC_ANCHOR_GENERIC_PREFIX = re.compile(
    r"^(?:我们|你们|他们|这|那|其|因此|所以|同时|如果|因为|通过|对于|在|当|可以|需要|"
    r"一种|一个|这个|这些|作为|随着|而且|但是|然而|其实|目前|首先|其次|最后)"
    r"(?:[，,、:：\s]|(?=[\u4e00-\u9fff])|$)"
)
H2_NUMBER_OVERRIDE = re.compile(r"^\s*<!--\s*gzh-h2-number:(?P<number>[^<>\n]*?)\s*-->\s*")
AUTHOR_FOOTER_START = "<!-- gzh-author-footer:start -->"
AUTHOR_FOOTER_END = "<!-- gzh-author-footer:end -->"
AUTHOR_FOOTER_PREFIX = "艾笑："
AUTHOR_BIO_EMPHASIS = "让 AI 好好干活，让我们好好生活。"
AUTHOR_BIO_LEGACY_SUFFIX = "一起吧。"
AUTHOR_ROADMAP_TEXT = "成为 AI Native 的进阶地图"
AUTHOR_ROADMAP_URL = (
    "https://mp.weixin.qq.com/s?__biz=MzkxMTc0MjQ2MA%3D%3D"
    "&mid=2247484737&idx=1&sn=8b1ea66df383ce5da4952f906e3ae120"
)


def frontmatter_values(text):
    values = {}
    match = re.match(r'\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)', text, flags=re.S)
    if not match:
        return values
    for line in match.group(1).splitlines():
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*?)\s*$", line)
        if match:
            values[match.group(1)] = match.group(2).strip("\"'")
    return values


def strip_frontmatter(text):
    match = re.match(r'\A---\r?\n.*?\r?\n---(?:\r?\n|$)', text, flags=re.S)
    if match:
        return text[match.end():].lstrip()
    return text


def starts_html_comment(line):
    return line.lstrip().startswith("<!--")


def skip_html_comment(lines, index):
    while index < len(lines):
        if "-->" in lines[index]:
            return index + 1
        index += 1
    return index


def heading_number_info(text):
    """返回 H2 的“序号、是否显式、标题正文”，支持人工清空序号。"""
    raw = text.strip()
    override = H2_NUMBER_OVERRIDE.match(raw)
    if override:
        number = override.group("number").strip()
        return number, True, raw[override.end():].strip()
    heading = SECTION_TITLES.sub("", raw)
    # AI 日报正文常把章节序号直接写进 H2（如“01治理与长期路线”）。
    # 章节组件会再次生成视觉序号，因此这里需要去掉源标题中的阿拉伯数字序号，
    # 同时避免误伤“1.0”等版本号。
    heading = re.sub(
        r"^\d{1,2}(?:\s*[、.．)）:：-]\s*(?=\D)|\s+|(?=[\u4e00-\u9fff]))",
        "",
        heading,
    )
    # 旧稿里的“一、/01”等只是源文习惯写法，继续由排版器生成 01/02…；
    # 只有编辑器写入的显式注释才覆盖自动序号。
    return None, False, heading.strip()


def clean_heading(text):
    return heading_number_info(text)[2]


def normalize_text(text):
    chars = []
    double_open = True
    single_open = True
    for ch in text:
        if ch == '"':
            chars.append("“" if double_open else "”")
            double_open = not double_open
        elif ch == "'":
            chars.append("‘" if single_open else "’")
            single_open = not single_open
        else:
            chars.append(ch)
    return "".join(chars)


def leaf(text, normalize=True):
    if normalize:
        text = normalize_text(text)
    return f'<span leaf="">{html.escape(text, quote=False)}</span>'


def inline_plain(text):
    """Render plain inline text, including the account's fixed closing CTA."""
    parts = []
    pos = 0
    for match in FIXED_RED_BOLD_PHRASE.finditer(text):
        if match.start() > pos:
            parts.append(leaf(text[pos : match.start()]))
        parts.append(
            f'<strong style="color:{FIXED_RED_BOLD_COLOR};font-weight:800;">'
            f"{leaf(match.group(0))}</strong>"
        )
        pos = match.end()
    if pos < len(text):
        parts.append(leaf(text[pos:]))
    return "".join(parts)


def visible_text(text):
    """Return readable source text with Markdown wrappers removed for ratio checks."""
    text = SEMANTIC_ANCHOR.sub(lambda match: match.group(1), text)
    text = MANUAL_STYLE.sub(lambda match: match.group("text"), text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"==(.+?)==", r"\1", text)
    text = re.sub(r"<u>(.+?)</u>", r"\1", text)
    text = re.sub(r"\+\+(.+?)\+\+", r"\1", text)
    text = re.sub(r"~~(.+?)~~", r"\1", text)
    return html.unescape(text)


def compact_char_count(text):
    return len(re.sub(r"\s+", "", visible_text(text)))


def semantic_anchor_error(message):
    raise SystemExit(f"invalid semantic anchor: {message}")


def semantic_anchor_at_sentence_start(text, start):
    """判断锚点前是否只有段首或句末标点，避免把句首套成关键词。"""
    prefix = text[:start]
    # 句首判断不应被 Markdown 的链接、加粗等语法字符干扰；受保护范围
    # 仍由调用方单独校验，这里只提取可见的边界字符。
    prefix = re.sub(r"[`*_~=]+", "", prefix)
    prefix = re.sub(r"\s+$", "", prefix)
    return not prefix or bool(re.search(r"(?:^|[。！？!?；;：:\n])[\s「『“\"（(【\[]*$", prefix))


def validate_semantic_anchors(text, require_coverage=False, allow_legacy=False):
    """Enforce the cross-theme semantic-anchor contract before HTML rendering."""
    anchors = list(SEMANTIC_ANCHOR.finditer(text))
    open_count = text.count(SEMANTIC_ANCHOR_OPEN)
    close_count = text.count(SEMANTIC_ANCHOR_CLOSE)
    if open_count != len(anchors) or close_count != len(anchors):
        semantic_anchor_error("marker must use a complete <mark data-gzh=\"semantic-anchor\">…</mark> pair")
    paragraph_chars = compact_char_count(text)
    if (
        require_coverage
        and paragraph_chars >= SEMANTIC_ANCHOR_LONG_PARAGRAPH_CHARS
        and not anchors
    ):
        semantic_anchor_error(
            "a long ordinary paragraph requires 1-2 semantic anchors "
            f"when it has at least {SEMANTIC_ANCHOR_LONG_PARAGRAPH_CHARS} visible characters"
        )
    if not anchors:
        return
    if len(anchors) > SEMANTIC_ANCHOR_MAX_PER_PARAGRAPH:
        semantic_anchor_error(
            f"an ordinary paragraph may contain at most {SEMANTIC_ANCHOR_MAX_PER_PARAGRAPH} semantic anchors"
        )

    if paragraph_chars < SEMANTIC_ANCHOR_MIN_PARAGRAPH_CHARS:
        semantic_anchor_error(
            "semantic anchor requires an ordinary paragraph with at least "
            f"{SEMANTIC_ANCHOR_MIN_PARAGRAPH_CHARS} visible characters"
        )

    protected_spans = [match.span() for match in PROTECTED_INLINE.finditer(text)]
    phrases = []
    total_phrase_chars = 0
    for anchor in anchors:
        if any(anchor.start() < end and anchor.end() > start for start, end in protected_spans):
            semantic_anchor_error("semantic anchor cannot overlap existing inline markup")
        phrase = anchor.group(1)
        if "\n" in phrase or "<" in phrase or ">" in phrase:
            semantic_anchor_error("phrase must be plain inline source text")
        phrase_chars = compact_char_count(phrase)
        if not SEMANTIC_ANCHOR_MIN_PHRASE_CHARS <= phrase_chars <= SEMANTIC_ANCHOR_MAX_PHRASE_CHARS:
            semantic_anchor_error(
                "each phrase must contain "
                f"{SEMANTIC_ANCHOR_MIN_PHRASE_CHARS}-"
                f"{SEMANTIC_ANCHOR_MAX_PHRASE_CHARS} visible characters"
            )
        if not allow_legacy:
            if semantic_anchor_at_sentence_start(text, anchor.start()):
                semantic_anchor_error("semantic anchor cannot start a paragraph or sentence")
            if SEMANTIC_ANCHOR_GENERIC_PREFIX.match(phrase.strip()):
                semantic_anchor_error("semantic anchor must name a concrete judgment, not a generic lead-in")
        if FIXED_RED_BOLD_PHRASE.search(phrase):
            semantic_anchor_error("the fixed account CTA must use its existing automatic rule")
        normalized_phrase = re.sub(r"\s+", "", phrase)
        if normalized_phrase in phrases:
            semantic_anchor_error("duplicate phrases are not useful scan anchors")
        phrases.append(normalized_phrase)
        total_phrase_chars += phrase_chars

    if total_phrase_chars / paragraph_chars > SEMANTIC_ANCHOR_MAX_RATIO:
        semantic_anchor_error(
            f"total highlighted text may not exceed {SEMANTIC_ANCHOR_MAX_RATIO:.0%} "
            "of the paragraph"
        )


def validate_document_semantic_anchor_density(md):
    """Cap document-wide red emphasis while ignoring literal examples in code fences."""
    visible_lines = []
    in_code = False
    for line in strip_frontmatter(md).splitlines():
        if line.startswith("```"):
            in_code = not in_code
            continue
        if not in_code:
            visible_lines.append(line)
    visible_source = "\n".join(visible_lines)
    anchors = list(SEMANTIC_ANCHOR.finditer(visible_source))
    if not anchors:
        return
    document_chars = compact_char_count(visible_source)
    anchor_chars = sum(compact_char_count(anchor.group(1)) for anchor in anchors)
    if document_chars and anchor_chars / document_chars > SEMANTIC_ANCHOR_MAX_DOCUMENT_RATIO:
        semantic_anchor_error(
            f"total highlighted text may not exceed {SEMANTIC_ANCHOR_MAX_DOCUMENT_RATIO:.0%} "
            "of the document"
        )


def reject_semantic_anchor_outside_paragraph(text):
    if SEMANTIC_ANCHOR_OPEN in text or SEMANTIC_ANCHOR_CLOSE in text:
        semantic_anchor_error("semantic anchor is only allowed in long ordinary body paragraphs")


def validate_manual_styles(text):
    """只接受编辑器合同中的纯文字 span，拒绝额外属性、嵌套 HTML 与危险链接。"""
    if MANUAL_STYLE_ATTRIBUTE.search(MANUAL_STYLE.sub("", text)):
        raise SystemExit("invalid manual style: use the complete plain-text span contract")
    for match in MANUAL_STYLE.finditer(text):
        marks = html.unescape(match.group("marks") or "").split()
        if not set(marks) <= MANUAL_STYLE_MARKS:
            raise SystemExit("invalid manual style: unsupported decoration")
        if match.group("href") is not None:
            href = html.unescape(match.group("href"))
            try:
                # 撇号是 URI 合法字符；输出属性仍由 html.escape(quote=True) 转义。
                valid = bool(re.fullmatch(r'https?://[^\s<>"]+', href) and urlsplit(href).hostname)
            except ValueError:
                valid = False
            if not valid:
                raise SystemExit("invalid manual style: link must use an absolute http(s) URL")


def manual_style_inline(match, link_color, text_color="#4d4f46"):
    """颜色、字重分别写明，避免取消样式后从标题或引用父级继承回来。"""
    href = html.unescape(match.group("href")) if match.group("href") is not None else None
    color = FIXED_RED_BOLD_COLOR if match.group("red") == "1" else (link_color if href else text_color)
    weight = "800" if match.group("bold") == "1" else "400"
    style = f"color:{color};font-weight:{weight};"
    marks = set((match.group("marks") or "").split())
    if "code" in marks:
        style += (
            "background:#eeefe9;padding:2px 6px;border-radius:4px;"
            "font-family:ui-monospace,Menlo,Monaco,Consolas,monospace;"
            "font-size:13px;border:1px solid #b6b7af;"
        )
    elif "highlight" in marks:
        style += "background:#eeefe9;padding:1px 5px;border-radius:4px;border:1px solid #bfc1b7;"
    decorations = []
    if "underline" in marks:
        decorations.append("underline")
    if "strike" in marks:
        decorations.append("line-through")
    if decorations:
        style += f'text-decoration:{" ".join(decorations)};'
    # 编辑器的换行实体须成为真实 br，否则普通 HTML 会折叠成空格。
    text = html.unescape(match.group("text"))
    leaves = '<br>'.join(leaf(line, normalize=False) for line in text.split('\n'))
    content = f'<span style="{style}">{leaves}</span>'
    if href:
        return (
            f'<a href="{html.escape(href, quote=True)}" target="_blank" '
            f'style="color:{color};text-decoration:underline;">{content}</a>'
        )
    return content


def inline(
    text,
    link_color="#576b95",
    allow_semantic_anchor=False,
    require_semantic_anchor_coverage=False,
    allow_legacy_semantic_anchors=False,
    text_color="#4d4f46",
):
    validate_manual_styles(text)
    if allow_semantic_anchor:
        validate_semantic_anchors(
            text,
            require_coverage=require_semantic_anchor_coverage,
            allow_legacy=allow_legacy_semantic_anchors,
        )
    else:
        reject_semantic_anchor_outside_paragraph(text)
    parts = []
    pos = 0
    for match in INLINE_MARKUP_PATTERN.finditer(text):
        if match.start() > pos:
            parts.append(inline_plain(text[pos : match.start()]))
        token = match.group(0)
        image = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", token)
        link = re.match(r"(?<!!)\[([^\]]+)\]\((https?://[^)]+)\)", token)
        semantic_anchor = SEMANTIC_ANCHOR.fullmatch(token)
        manual_style = MANUAL_STYLE.fullmatch(token)
        if manual_style:
            parts.append(manual_style_inline(manual_style, link_color, text_color))
        elif semantic_anchor:
            parts.append(
                f'<strong style="color:{FIXED_RED_BOLD_COLOR};font-weight:800;">'
                f"{leaf(semantic_anchor.group(1))}</strong>"
            )
        elif image:
            parts.append(leaf(token))
        elif link:
            href = html.escape(link.group(2).strip(), quote=True)
            label = leaf(link.group(1))
            parts.append(
                f'<a href="{href}" target="_blank" '
                f'style="color:{link_color};text-decoration:underline;text-underline-offset:3px;">'
                f"{label}</a>"
            )
        elif token.startswith("`"):
            parts.append(
                '<span style="background:#eeefe9;color:#23251d;padding:2px 6px;'
                "border-radius:4px;font-family:ui-monospace,Menlo,Monaco,Consolas,monospace;"
                f'font-size:13px;border:1px solid #b6b7af;">{leaf(token[1:-1])}</span>'
            )
        elif token.startswith("**"):
            content = token[2:-2]
            color = (
                FIXED_RED_BOLD_COLOR
                if FIXED_RED_BOLD_PHRASE.fullmatch(content)
                else "#23251d"
            )
            parts.append(f'<strong style="color:{color};font-weight:800;">{leaf(content)}</strong>')
        elif token.startswith("=="):
            parts.append(
                '<span style="background:#eeefe9;padding:1px 5px;border-radius:4px;'
                f'font-weight:600;color:#23251d;border:1px solid #bfc1b7;">{leaf(token[2:-2])}</span>'
            )
        elif token.startswith("<u>"):
            parts.append(underline(token[3:-4]))
        elif token.startswith("++"):
            parts.append(underline(token[2:-2]))
        elif token.startswith("~~"):
            parts.append(
                f'<span style="color:#9ea096;text-decoration:line-through;">{leaf(token[2:-2])}</span>'
            )
        pos = match.end()
    if pos < len(text):
        parts.append(inline_plain(text[pos:]))
    return "".join(parts)


def inline_with_breaks(text, text_color="#4d4f46"):
    return "<br>".join(inline(line, text_color=text_color) for line in text.splitlines())


def compact_blockquote_lines(text):
    """Collapse blank quote lines while preserving intentional line breaks."""
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def paragraph(text, require_semantic_anchors=False, allow_legacy_semantic_anchors=False):
    return (
        '<p style="margin:0 0 18px;font-size:15px;line-height:1.9;'
        f'text-align:justify;color:#4d4f46;padding:0 8px;">'
        f"{inline(text, allow_semantic_anchor=True, require_semantic_anchor_coverage=require_semantic_anchors, allow_legacy_semantic_anchors=allow_legacy_semantic_anchors)}</p>"
    )


def author_bio_inline(text):
    """Render the final brand highlight and hide the retired legacy suffix."""
    if text.endswith(AUTHOR_BIO_EMPHASIS + AUTHOR_BIO_LEGACY_SUFFIX):
        text = text[: -len(AUTHOR_BIO_LEGACY_SUFFIX)]
    start = text.find(AUTHOR_BIO_EMPHASIS)
    if start == -1:
        return inline(text)
    end = start + len(AUTHOR_BIO_EMPHASIS)
    return (
        f"{inline_plain(text[:start])}"
        '<strong style="background:#c7254e;color:#ffffff;font-weight:700;'
        'padding:1px 4px;">'
        f"{leaf(text[start:end])}</strong>"
        f"{inline_plain(text[end:])}"
    )


def author_footer_block(text):
    return (
        '<section data-gzh="author-footer" style="margin:42px 0 0;">'
        '<section style="display:flex;align-items:center;justify-content:center;'
        'margin:0 0 20px;">'
        '<span style="display:inline-block;font-family:Arial,sans-serif;font-size:12px;'
        'line-height:1;color:#dedede;letter-spacing:-1px;white-space:nowrap;'
        'margin-right:12px;"><span leaf="">────────</span></span>'
        '<span style="font-size:11px;line-height:1;color:#b2b2b2;letter-spacing:3px;'
        'font-weight:500;"><span leaf="">END</span></span>'
        '<span style="display:inline-block;font-family:Arial,sans-serif;font-size:12px;'
        'line-height:1;color:#dedede;letter-spacing:-1px;white-space:nowrap;'
        'margin-left:12px;"><span leaf="">────────</span></span>'
        "</section>"
        '<section style="padding:0 8px;">'
        '<p style="margin:0;font-size:13px;line-height:1.9;color:#8c8c8c;'
        f'text-align:justify;">{author_bio_inline(text)}</p>'
        '<section data-gzh="author-actions" style="margin:20px 0 0;">'
        '<p style="margin:0 0 6px;font-size:13px;line-height:1.8;color:#8c8c8c;">'
        '<span leaf="">点击查看： </span>'
        f'<a href="{html.escape(AUTHOR_ROADMAP_URL, quote=True)}" '
        'style="color:#c7254e;font-weight:700;text-decoration:none;'
        'border-bottom:1px solid #c7254e;">'
        f"{leaf(AUTHOR_ROADMAP_TEXT)}</a>"
        "</p>"
        '<p style="margin:0;font-size:13px;line-height:1.8;color:#8c8c8c;">'
        '<span leaf="">私信发送： </span>'
        '<strong style="color:#c7254e;font-weight:700;">'
        '<span leaf="">公众号主页私信“联系我”</span></strong>'
        '<span leaf="">，更多资料、深度链接交流、一起玩。</span>'
        "</p>"
        "</section>"
        "</section>"
        "</section>"
    )


def collect_author_footer(lines, index):
    body_lines = []
    index += 1
    while index < len(lines) and lines[index].strip() != AUTHOR_FOOTER_END:
        body_lines.append(lines[index].rstrip())
        index += 1
    if index >= len(lines):
        raise SystemExit("author footer end marker missing")
    paragraphs = markdown_paragraphs("\n".join(body_lines))
    if len(paragraphs) != 1:
        raise SystemExit("author footer must contain exactly one paragraph")
    text = " ".join(line.strip() for line in paragraphs[0].splitlines())
    if not text.startswith(AUTHOR_FOOTER_PREFIX):
        raise SystemExit(f"author footer must start with {AUTHOR_FOOTER_PREFIX}")
    return text, index + 1


def micro_heading(text):
    return (
        '<section style="margin:26px 0 10px;padding:0 8px;">'
        '<h4 style="margin:0;font-size:16px;font-weight:800;color:#23251d;'
        'line-height:1.65;letter-spacing:0;">'
        f"{inline(text)}</h4></section>"
    )


def example_list_block(items):
    rows = []
    for item in items:
        rows.append(
            '<section style="display:flex;align-items:flex-start;margin-bottom:6px;">'
            '<span style="display:inline-block;color:#ed7b2f;font-size:13px;'
            'font-weight:800;line-height:1.65;margin-right:9px;vertical-align:top;flex-shrink:0;">'
            f'{leaf("-")}</span>'
            f'<p style="font-size:13px;color:#4d4f46;margin:0;line-height:1.65;flex:1;text-align:justify;">{inline(item)}</p>'
            "</section>"
        )
    return (
        '<section style="margin:8px 0 18px;padding:0 8px;">'
        "<section style=\"font-family:'IBM Plex Sans',-apple-system,sans-serif;\">"
        + "".join(rows)
        + "</section></section>"
    )


def question_list_block(items):
    rows = []
    for idx, item in enumerate(items, start=1):
        border = "border-top:1px solid #dfe2d8;" if idx > 1 else ""
        rows.append(
            f'<section style="display:flex;align-items:flex-start;gap:10px;padding:12px 0;{border}">'
            '<span style="display:inline-block;min-width:34px;text-align:center;background:#1e1f23;'
            'color:#ffffff;border-radius:4px;padding:2px 0;font-size:11px;line-height:1.6;'
            f'font-weight:800;flex-shrink:0;">{leaf(f"{idx:02d}")}</span>'
            f'<p style="font-size:15px;color:#4d4f46;margin:0;line-height:1.7;flex:1;font-weight:700;text-align:justify;">{inline(item)}</p>'
            "</section>"
        )
    return (
        '<section style="margin:0 0 22px;padding:0 8px;">'
        '<section style="background:#fdfdf8;border:1px solid #bfc1b7;'
        "border-radius:6px;padding:4px 16px;font-family:'IBM Plex Sans',-apple-system,sans-serif;\">"
        + "".join(rows)
        + "</section></section>"
    )


def underline(text):
    return (
        '<span style="border-bottom:2px solid #ed7b2f;font-weight:600;color:#23251d;">'
        f"{leaf(text)}</span>"
    )


def quote_block(text, opening=False):
    manual_revision = bool(MANUAL_STYLE_ATTRIBUTE.search(text))
    content = text if manual_revision else text.strip("“”")
    if opening:
        content = compact_blockquote_lines(content)
        return (
            '<section style="margin-top:4px;margin-bottom:24px;padding:0 8px;">'
            '<section style="background:#f1f2ee;border-radius:8px;padding:14px 16px;'
            "font-family:'IBM Plex Sans',-apple-system,sans-serif;\">"
            f'<p style="margin:0;font-size:13px;line-height:1.75;color:#6b7067;font-weight:400;text-align:justify;">{inline_with_breaks(content, text_color="#6b7067")}</p>'
            "</section></section>"
        )
    quote_text = content if manual_revision else "「" + content.strip("「」") + "」"
    return (
        '<section style="margin:0 4px 24px;background:#eeefe9;border-radius:6px;'
        'border-left:4px solid #ed7b2f;padding:16px 18px;">'
        f'<p style="font-size:15px;font-weight:800;color:#23251d;margin:0;line-height:1.8;text-align:justify;">{inline_with_breaks(quote_text)}</p>'
        "</section>"
    )


def image_block(url):
    return (
        '<section style="margin:24px 0 18px;padding:0 8px;">'
        '<section style="background:#fdfdf8;border-radius:8px;padding:4px;'
        'border:1px solid #dfe2d8;">'
        '<figure style="margin:0;border-radius:6px;overflow:hidden;">'
        f'<span leaf=""><img src="{html.escape(url, quote=True)}" alt="图片" style="max-width:100%;height:auto;display:block;margin:0 auto;"></span>'
        "</figure></section></section>"
    )


def section_title(num, title, number_override=None):
    reject_semantic_anchor_outside_paragraph(title)
    # 编号/标题行的块级容器用 <p> 而不是 <section>，并在父级重复完整字体样式：
    # 微信草稿编辑器会重建 section 包裹链并重写叶子样式（同步后序号变小），
    # 而 <p> 的样式继承在草稿编辑器中已验证可靠（正文段落同款写法一直正常）。
    number_style = (
        "font-family:'Helvetica Neue',Arial,'PingFang SC','Hiragino Sans GB',"
        "'Microsoft YaHei',-apple-system,BlinkMacSystemFont,sans-serif;font-size:54px;"
        "font-weight:900;color:#23251d;line-height:0.95;letter-spacing:0.5px;"
    )
    title_style = (
        "font-size:23px;font-weight:900;color:#23251d;line-height:1.35;"
        "letter-spacing:0;text-align:left;"
    )
    title_html = (
        f'<span style="display:block;{title_style}">{inline(title)}</span>'
        if MANUAL_STYLE_ATTRIBUTE.search(title)
        else f'<span leaf="" style="display:block;{title_style}">{html.escape(normalize_text(title), quote=False)}</span>'
    )
    display_number = f"{num:02d}" if number_override is None else number_override
    number_display = "block" if display_number else "none"
    return (
        '<section style="margin-top:56px;margin-bottom:20px;padding:0 8px;">'
        "<section style=\"font-family:'PingFang SC','Hiragino Sans GB','Microsoft YaHei',-apple-system,BlinkMacSystemFont,sans-serif;text-align:left;\">"
        f'<p style="display:{number_display};margin:0 0 10px;{number_style}">'
        f'<span leaf="" style="display:block;{number_style}">{html.escape(display_number, quote=False)}</span>'
        '</p>'
        f'<p style="margin:0;{title_style}">'
        f'{title_html}'
        '</p>'
        "</section></section>"
    )


def ai_daily_audio_placeholder_block():
    # 音频位只留空白段落,不加虚线框或提示文字;用户在公众号后台该位置直接插入原生音频。
    return (
        '<p style="margin:16px 8px 28px;font-size:16px;line-height:1.75;color:#4d4f46;">'
        '<span leaf=""><br></span></p>'
    )


def ai_daily_reference_block(intro, items):
    rows = []
    for index, item in enumerate(items, start=1):
        rows.append(
            '<section style="display:flex;align-items:flex-start;margin:0 0 7px;">'
            '<span style="display:inline-block;min-width:24px;margin-right:5px;font-size:11px;'
            f'line-height:1.65;color:#a5a79f;flex-shrink:0;">{leaf(f"{index:02d}")}</span>'
            f'<p style="margin:0;font-size:11px;line-height:1.65;color:#898b82;flex:1;">{inline(item, link_color="#73766d")}</p>'
            '</section>'
        )
    intro_html = ""
    if intro:
        intro_html = (
            '<p style="margin:0 0 10px;font-size:11px;line-height:1.7;color:#9a9c93;">'
            f'{inline(" ".join(intro), link_color="#73766d")}</p>'
        )
    attribution_html = (
        '<p style="margin:0 0 6px;font-size:11px;line-height:1.7;color:#9a9c93;">'
        f'{leaf(AI_DAILY_REFERENCE_ATTRIBUTION)}</p>'
    )
    return (
        '<section style="margin:42px 8px 8px;padding-top:18px;border-top:1px solid #e3e4de;">'
        '<p style="margin:0 0 8px;font-size:13px;font-weight:700;line-height:1.6;color:#65675e;">'
        f'{leaf(AI_DAILY_REFERENCE_HEADING)}</p>'
        + attribution_html
        + intro_html
        + "".join(rows)
        + '</section>'
    )


def subheading(title):
    reject_semantic_anchor_outside_paragraph(title)
    # H3 不生成视觉序号，因此必须保留作者写在源标题中的编号。
    title_html = inline(title.strip()) if MANUAL_STYLE_ATTRIBUTE.search(title) else leaf(title.strip())
    return (
        '<section style="margin:24px 0 16px;padding:0 8px;">'
        "<h3 style=\"font-size:18px;font-weight:800;color:#23251d;margin:0;"
        'padding:0 2px;display:inline;line-height:1.55;'
        'box-shadow:inset 0 -0.5em 0 rgba(245,78,0,0.18);">'
        f"{title_html}</h3></section>"
    )


def list_block(items):
    rows = []
    for item in items:
        rows.append(
            '<section style="display:flex;align-items:flex-start;margin-bottom:4px;">'
            '<span style="display:inline-block;color:#1e1f23;opacity:0.68;font-size:12px;'
            'font-weight:500;line-height:1.55;margin-right:9px;vertical-align:top;flex-shrink:0;">'
            f'{leaf("-")}</span>'
            f'<p style="font-size:13px;color:#4d4f46;margin:0;line-height:1.55;flex:1;text-align:justify;">{inline(item)}</p>'
            "</section>"
        )
    return (
        '<section style="margin:0 0 16px;padding:0 8px;">'
        "<section style=\"font-family:'IBM Plex Sans',-apple-system,sans-serif;\">"
        + "".join(rows)
        + "</section></section>"
    )


def is_list_item(line):
    return bool(LIST_ITEM.match(line))


def list_item_text(line):
    match = LIST_ITEM.match(line)
    return match.group(1).strip() if match else line.strip()


def is_micro_heading(line):
    stripped = line.strip()
    if MANUAL_STYLE_ATTRIBUTE.search(stripped):
        stripped = visible_text(stripped)
    if len(stripped) > 90:
        return False
    return bool(MICRO_HEADING.match(stripped))


def is_example_item(line):
    stripped = line.strip()
    if MANUAL_STYLE_ATTRIBUTE.search(stripped):
        stripped = visible_text(stripped)
    return bool(EXAMPLE_ITEM.match(stripped) or ACTION_ITEM.match(stripped))


def is_question_item(line):
    stripped = line.strip()
    if stripped.startswith(("#", ">", "!", "|", "```")) or is_list_item(stripped):
        return False
    if MANUAL_STYLE_ATTRIBUTE.search(stripped):
        stripped = visible_text(stripped)
    return bool(QUESTION_ITEM.match(stripped))


def collect_consecutive_items(lines, index, predicate):
    items = []
    while index < len(lines):
        current_index = next_content_index(lines, index)
        if current_index >= len(lines):
            return items, current_index
        current = lines[current_index].rstrip()
        if not predicate(current):
            return items, current_index
        items.append(current.strip())
        index = current_index + 1
    return items, index


def next_content_index(lines, index):
    while index < len(lines) and not lines[index].strip():
        index += 1
    return index


def is_table_line(line):
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2


def is_table_separator(line):
    cells = split_table_row(line)
    return cells and all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells)


def split_table_row(line):
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def table_block(rows):
    if not rows:
        return ""
    header = rows[0]
    body = rows[1:]
    columns = max(len(header), *(len(row) for row in body)) if body else len(header)
    width = f"{100 / max(columns, 1):.4g}%"

    def cell(text, header_cell=False, is_first=False):
        style = (
            f"width:{width};padding:10px 12px;font-size:12px;"
            if header_cell
            else f"width:{width};padding:10px 12px;font-size:13px;"
        )
        style += "font-weight:800;color:#23251d;" if header_cell else "color:#4d4f46;"
        if not is_first:
            style += "border-left:1px solid #bfc1b7;"
        return f'<section style="{style}">{inline(text)}</section>'

    html_rows = [
        '<section style="display:flex;background:#eeefe9;border-bottom:1px solid #bfc1b7;">'
        + "".join(cell(header[i] if i < len(header) else "", True, i == 0) for i in range(columns))
        + "</section>"
    ]
    for row_index, row in enumerate(body):
        border = "border-bottom:1px solid #bfc1b7;" if row_index < len(body) - 1 else ""
        html_rows.append(
            f'<section style="display:flex;{border}">'
            + "".join(cell(row[i] if i < len(row) else "", False, i == 0) for i in range(columns))
            + "</section>"
        )
    return (
        '<section style="margin:0 0 22px;padding:0 8px;">'
        '<section style="border-radius:6px;overflow:hidden;border:1px solid #bfc1b7;'
        "background:#fdfdf8;font-family:'IBM Plex Sans',-apple-system,sans-serif;\">"
        + "".join(html_rows)
        + "</section></section>"
    )


def code_block(lines, lang):
    lang = lang or "text"
    rendered = []
    for raw in lines:
        line = raw.replace("    ", "　　")
        if not line:
            line = "\u00a0"
        rendered.append(
            '<p style="margin:0;font-family:\'SF Mono\',Consolas,Monaco,monospace;'
            "font-size:13px;line-height:1.6;color:#E2E8F0;"
            f'overflow-wrap:anywhere;word-break:break-word;">{leaf(line, normalize=False)}</p>'
        )
    return (
        '<section style="margin:0 0 22px;border-radius:8px;overflow:hidden;background:#1E293B;'
        'box-shadow:0 4px 16px -8px rgba(15,23,42,0.4);">'
        '<section style="display:flex;align-items:center;padding:9px 14px;background:#0F172A;">'
        '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#FF5F56;margin-right:7px;font-size:0;line-height:0;overflow:hidden;"><span leaf="">&nbsp;</span></span>'
        '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#FFBD2E;margin-right:7px;font-size:0;line-height:0;overflow:hidden;"><span leaf="">&nbsp;</span></span>'
        '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#27C93F;font-size:0;line-height:0;overflow:hidden;"><span leaf="">&nbsp;</span></span>'
        f'<span style="margin-left:12px;font-size:12px;color:#64748B;font-family:Consolas,Monaco,monospace;letter-spacing:1px;">{leaf(lang)}</span>'
        "</section>"
        '<section style="padding:11px 14px;">'
        + "".join(rendered)
        + "</section></section>"
    )


def ai_daily_reference_parts(lines, index):
    intro = []
    items = []
    while index < len(lines):
        line = lines[index].rstrip()
        if not line:
            index += 1
            continue
        if starts_html_comment(line):
            index = skip_html_comment(lines, index)
            continue
        if is_list_item(line):
            items.append(list_item_text(line))
        else:
            intro_line = line.strip()
            if all(marker in intro_line for marker in AI_DAILY_REFERENCE_LEGACY_INTRO_MARKERS):
                index += 1
                continue
            intro.append(intro_line)
        index += 1
    return intro, items


def markdown_paragraphs(text):
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    return [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]


def is_section_anchor_paragraph(block):
    first_line = block.splitlines()[0].lstrip()
    if (
        first_line.startswith(("#", ">", "!", "```", "|"))
        or is_list_item(first_line)
        or is_table_line(first_line)
    ):
        return False
    if compact_char_count(block) < SEMANTIC_ANCHOR_MIN_PARAGRAPH_CHARS:
        return False
    plain_source = PROTECTED_INLINE.sub("", SEMANTIC_ANCHOR.sub("", block))
    return len(re.sub(r"\s+", "", plain_source)) >= SEMANTIC_ANCHOR_MIN_PHRASE_CHARS


def validate_section_semantic_anchor_coverage(md):
    """Require one scan anchor in each substantial preface and H2 section."""
    body = strip_frontmatter(md)
    body = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
    body = re.sub(
        re.escape(AUTHOR_FOOTER_START)
        + r".*?"
        + re.escape(AUTHOR_FOOTER_END),
        "",
        body,
        flags=re.DOTALL,
    )
    parts = re.split(r"(?m)^##\s+(.+?)\s*$", body)
    sections = [("序言", parts[0])]
    sections.extend(
        (clean_heading(parts[index]), parts[index + 1])
        for index in range(1, len(parts), 2)
    )
    for label, content in sections:
        eligible = [
            block
            for block in markdown_paragraphs(content)
            if is_section_anchor_paragraph(block)
        ]
        if eligible and not any(SEMANTIC_ANCHOR.search(block) for block in eligible):
            semantic_anchor_error(
                f"section '{label}' requires at least 1 semantic anchor"
            )


def validate_ai_daily_source(md):
    body = strip_frontmatter(md)
    forbidden = {
        "HTML <audio>": r"<audio\b",
        "Obsidian MP3 embed": r"!\[\[[^\]]+\.mp3(?:\|[^\]]*)?\]\]",
        "local MP3 path": r"(?:file://|(?<![:/])/(?!/))[^\n]*\.mp3",
        "transcript callout": r"视频转写",
        "Pudding field": r"\bpudding_(?:id|url)\b",
    }
    for label, pattern in forbidden.items():
        if re.search(pattern, body, flags=re.IGNORECASE):
            raise SystemExit(f"ai-daily source contains forbidden {label}")

    headings = [clean_heading(value) for value in re.findall(r"^##\s+(.+?)\s*$", body, re.MULTILINE)]
    if headings.count(AI_DAILY_REFERENCE_HEADING) != 1:
        raise SystemExit("ai-daily source must contain exactly one final '## 今日参考资料'")
    if headings[-1] != AI_DAILY_REFERENCE_HEADING:
        raise SystemExit("ai-daily '## 今日参考资料' must be the final H2")
    chapters = [heading for heading in headings if heading != AI_DAILY_REFERENCE_HEADING]
    if not 4 <= len(chapters) <= 6:
        raise SystemExit("ai-daily source must contain 4-6 body H2 chapters")

    before_reference, reference = body.split("## 今日参考资料", 1)
    if re.search(r"https?://", before_reference):
        raise SystemExit("ai-daily external links belong in '今日参考资料', not the body")
    if not re.search(r"^\s*(?:[-*+]\s+|\d+[.)、]\s+).+https?://", reference, re.MULTILINE):
        raise SystemExit("ai-daily '今日参考资料' must contain at least one linked list item")

    before_first_h2 = body.split("## ", 1)[0]
    opening = [
        block
        for block in markdown_paragraphs(before_first_h2)
        if AI_DAILY_AUDIO_PLACEHOLDER not in block
    ]
    if len(opening) != 2:
        raise SystemExit("ai-daily source must contain exactly two opening paragraphs before the first H2")
    if body.count(AI_DAILY_AUDIO_PLACEHOLDER) > 1:
        raise SystemExit("ai-daily source may contain at most one native audio placeholder")


def is_audio_preface(text):
    """前置音频与音频占位不是正文，不消耗开篇引言位置。"""
    text = text.strip()
    return text == AI_DAILY_AUDIO_PLACEHOLDER or bool(re.fullmatch(
        r"<(audio|mpvoice)\b[^>]*>.*?</\1>", text, flags=re.S | re.I
    ))


def render_minimal(md, mode=DEFAULT_MODE, require_semantic_anchors=False, source_map=None):
    if mode == "ai-daily":
        validate_ai_daily_source(md)
    body = strip_frontmatter(md)
    lines = body.splitlines()
    # 位置基于完整原稿，前置 frontmatter 和原始换行长度均计入。
    source_offsets = [len(md) - len(body)]
    for raw_line in body.splitlines(keepends=True):
        source_offsets.append(source_offsets[-1] + len(raw_line))
    mapped_blocks = []
    allow_legacy_semantic_anchors = MANUAL_REVISION_MARKER in md
    require_semantic_anchors = require_semantic_anchors and not allow_legacy_semantic_anchors
    out = [
        "<section style=\"max-width:677px;margin:0 auto;padding:8px;box-sizing:border-box;"
        "background:#ffffff;color:#4d4f46;font-family:'IBM Plex Sans',-apple-system,system-ui,"
        "'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;line-height:1.75;\">"
    ]

    def emit(block, kind, start_index, end_index):
        if source_map is not None:
            while end_index > start_index and not lines[end_index - 1].strip():
                end_index -= 1
            mapped_blocks.append((kind, source_offsets[start_index], source_offsets[end_index], len(out)))
        out.append(block)

    i = 0
    chapter = 0
    first_content = True
    in_intro_hook = False
    author_footer_count = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line:
            i += 1
            continue
        if line.strip() == "---":
            i += 1
            continue
        if line.strip() == AUTHOR_FOOTER_START:
            author_footer_count += 1
            if author_footer_count > 1:
                raise SystemExit("author footer must appear at most once")
            author_bio, i = collect_author_footer(lines, i)
            out.append(author_footer_block(author_bio))
            first_content = False
            continue
        if line.strip() == AUTHOR_FOOTER_END:
            raise SystemExit("author footer start marker missing")
        if line.strip() == "<!-- article-hook:start -->":
            in_intro_hook = chapter == 0
            i += 1
            continue
        if line.strip() == "<!-- article-hook:end -->":
            in_intro_hook = False
            i += 1
            continue
        if starts_html_comment(line):
            i = skip_html_comment(lines, i)
            continue
        if line.startswith("```"):
            lang = line.strip("`").strip()
            block = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                block.append(lines[i].rstrip("\n"))
                i += 1
            i += 1
            out.append(code_block(block, lang))
            first_content = False
            continue
        if mode == "ai-daily" and line.strip() == AI_DAILY_AUDIO_PLACEHOLDER:
            out.append(ai_daily_audio_placeholder_block())
            i += 1
            continue
        if line.startswith("## "):
            number_override, _, heading = heading_number_info(line[3:])
            if mode == "ai-daily" and heading == AI_DAILY_REFERENCE_HEADING:
                intro, items = ai_daily_reference_parts(lines, i + 1)
                out.append(ai_daily_reference_block(intro, items))
                first_content = False
                i = len(lines)
                continue
            chapter += 1
            emit(section_title(chapter, heading, number_override), "h2", i, i + 1)
            first_content = False
            i += 1
            continue
        if line.startswith("### "):
            emit(subheading(line[4:]), "h3", i, i + 1)
            first_content = False
            i += 1
            continue
        if line.startswith("# "):
            reject_semantic_anchor_outside_paragraph(line[2:])
            i += 1
            continue
        if is_micro_heading(line):
            emit(micro_heading(line.strip()), "micro", i, i + 1)
            first_content = False
            i += 1
            continue
        if is_question_item(line):
            items, next_index = collect_consecutive_items(lines, i, is_question_item)
            if len(items) >= 2:
                emit(question_list_block(items), "list", i, next_index)
                first_content = False
                i = next_index
                continue
        if is_example_item(line):
            items, next_index = collect_consecutive_items(lines, i, is_example_item)
            if len(items) >= 2:
                emit(example_list_block(items), "list", i, next_index)
                first_content = False
                i = next_index
                continue
        if is_table_line(line):
            rows = []
            while i < len(lines) and is_table_line(lines[i]):
                if not is_table_separator(lines[i]):
                    rows.append(split_table_row(lines[i]))
                i += 1
            out.append(table_block(rows))
            first_content = False
            continue
        image = re.match(r"!\[[^\]]*\]\(([^)]+)\)", line)
        if image:
            reject_semantic_anchor_outside_paragraph(line)
            out.append(image_block(image.group(1)))
            first_content = False
            i += 1
            continue
        if line.startswith(">"):
            start_index = i
            q = [line.lstrip("> ").strip()]
            i += 1
            while i < len(lines) and lines[i].startswith(">"):
                q.append(lines[i].lstrip("> ").strip())
                i += 1
            emit(quote_block("\n".join(q), opening=first_content or (in_intro_hook and chapter == 0)), "quote", start_index, i)
            first_content = False
            continue
        if is_list_item(line):
            start_index = i
            items = []
            while i < len(lines) and is_list_item(lines[i]):
                items.append(list_item_text(lines[i]))
                i += 1
            emit(list_block(items), "list", start_index, i)
            first_content = False
            continue
        start_index = i
        para = [line.strip()]
        i += 1
        while i < len(lines):
            nxt = lines[i].rstrip()
            if (
                not nxt
                or nxt.startswith(("```", "#", ">", "!"))
                or starts_html_comment(nxt)
                or is_micro_heading(nxt)
                or is_question_item(nxt)
                or is_example_item(nxt)
                or is_list_item(nxt)
                or is_table_line(nxt)
            ):
                break
            para.append(nxt.strip())
            i += 1
        emit(
            paragraph(
                " ".join(para),
                require_semantic_anchors=require_semantic_anchors,
                allow_legacy_semantic_anchors=allow_legacy_semantic_anchors,
            ),
            "paragraph", start_index, i,
        )
        if not is_audio_preface(" ".join(para)):
            first_content = False
    if require_semantic_anchors:
        validate_section_semantic_anchor_coverage(md)
    validate_document_semantic_anchor_density(md)
    if mode == "ai-daily":
        # 文末固定留一个正文样式的空段落,方便用户在公众号后台回车插入页尾模板;
        # 没有它,回车会继承参考资料区的小字样式。
        out.append(
            '<p style="margin:16px 0 0;font-size:16px;line-height:1.75;color:#4d4f46;">'
            '<span leaf=""><br></span></p>'
        )
    out.append("</section>")
    if source_map is not None:
        html_offsets = [0]
        for block in out:
            html_offsets.append(html_offsets[-1] + len(block) + 1)
        source_map.extend(
            {"kind": kind, "start": start, "end": end,
             "html_start": html_offsets[index], "html_end": html_offsets[index] + len(out[index])}
            for kind, start, end, index in mapped_blocks
        )
    return "\n".join(out) + "\n"


def render(md, theme, mode=DEFAULT_MODE, require_semantic_anchors=False, source_map=None):
    if theme != DEFAULT_THEME:
        raise SystemExit(
            f"deterministic renderer currently supports theme '{DEFAULT_THEME}', got '{theme}'. "
            "Use the theme component library for agent-led assembly or add a renderer adapter."
        )
    if mode not in SUPPORTED_MODES:
        raise SystemExit(f"unsupported content mode: {mode}")
    return render_minimal(
        md,
        mode=mode,
        require_semantic_anchors=require_semantic_anchors,
        source_map=source_map,
    )


def default_output(input_path, theme, mode=DEFAULT_MODE):
    stem = Path(input_path).stem
    mode_suffix = f"-{mode}" if mode != DEFAULT_MODE else ""
    return Path.cwd() / f"{stem}-公众号排版-{theme}{mode_suffix}.html"


def resolve_mode(md, input_path, explicit_mode=None):
    values = frontmatter_values(md)
    declared = values.get("content_mode") or values.get("gzh_mode")
    if explicit_mode and declared and explicit_mode != declared:
        raise SystemExit(
            f"content mode conflict: --mode {explicit_mode!r} but frontmatter declares {declared!r}"
        )
    if RAW_AI_DAILY_FILENAME.fullmatch(Path(input_path).name):
        raise SystemExit(
            "raw AI daily is not a WeChat body; prepare YYYYMMDD-AI日报-公众号正文.md first"
        )
    mode = explicit_mode or declared
    if not mode and PREPARED_AI_DAILY_FILENAME.fullmatch(Path(input_path).name):
        mode = "ai-daily"
    mode = mode or DEFAULT_MODE
    if mode not in SUPPORTED_MODES:
        raise SystemExit(f"unsupported content mode: {mode}")
    return mode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="Markdown file path")
    ap.add_argument("output", nargs="?", help="Output HTML path")
    ap.add_argument("--theme", default=DEFAULT_THEME, help="Theme id, default: minimal")
    ap.add_argument("--mode", choices=sorted(SUPPORTED_MODES), help="Content mode; auto-detected when omitted")
    ap.add_argument(
        "--require-semantic-anchors",
        action="store_true",
        help=(
            "Reject 120+ character ordinary paragraphs and substantial preface/H2 sections "
            "when they lack semantic anchors."
        ),
    )
    args = ap.parse_args()

    src = Path(args.input)
    if not src.is_file():
        raise SystemExit(f"input not found: {src}")
    md = src.read_text(encoding="utf-8")
    mode = resolve_mode(md, src, args.mode)
    dst = Path(args.output) if args.output else default_output(src, args.theme, mode)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(
        render(
            md,
            args.theme,
            mode,
            require_semantic_anchors=args.require_semantic_anchors,
        ),
        encoding="utf-8",
    )
    print(dst)


if __name__ == "__main__":
    main()
