#!/usr/bin/env python3
"""Render Markdown into WeChat Official Account compatible HTML.

This deterministic renderer covers the default `minimal` theme. Other themes in
`themes/<theme-id>/components.md` are complete component libraries for agent-led
assembly and can get dedicated render adapters later without changing SKILL.md.
"""

import argparse
import html
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_THEME = "minimal"
SECTION_TITLES = re.compile(r"^[一二三四五六七八九十]+[、.．]\s*")
LIST_ITEM = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)、]\s+)(.*)$")
MICRO_HEADING = re.compile(
    r"^第[一二三四五六七八九十]+(?:[，,、]\s*[^。！？!?]{2,80}[。！？!?]?|层是[^。！？!?]{2,40}[。！？!?]?)$"
)
EXAMPLE_ITEM = re.compile(r"^(?:比如|例如|譬如)(?![：:]\s*$).+")
ACTION_ITEM = re.compile(r"^(?:新增|复制|修改|登记|运行|校验|生成|同步|回写|上传|创建|删除|补|跑|在)[^。！？!?]{2,28}[。！!]$")
QUESTION_ITEM = re.compile(r"^[^。！？!?]{2,120}[？?]$")


def strip_frontmatter(text):
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[end + 5 :].lstrip()
    return text


def starts_html_comment(line):
    return line.lstrip().startswith("<!--")


def skip_html_comment(lines, index):
    while index < len(lines):
        if "-->" in lines[index]:
            return index + 1
        index += 1
    return index


def clean_heading(text):
    return SECTION_TITLES.sub("", text.strip())


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


def inline(text):
    parts = []
    pattern = re.compile(
        r"(!?\[[^\]]+\]\([^)]+\)|`.+?`|\*\*.+?\*\*|==.+?==|<u>.+?</u>|\+\+.+?\+\+|~~.+?~~)"
    )
    pos = 0
    for match in pattern.finditer(text):
        if match.start() > pos:
            parts.append(leaf(text[pos : match.start()]))
        token = match.group(0)
        image = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", token)
        link = re.match(r"(?<!!)\[([^\]]+)\]\((https?://[^)]+)\)", token)
        if image:
            parts.append(leaf(token))
        elif link:
            href = html.escape(link.group(2).strip(), quote=True)
            label = leaf(link.group(1))
            parts.append(
                f'<a href="{href}" target="_blank" '
                'style="color:#576b95;text-decoration:underline;text-underline-offset:3px;">'
                f"{label}</a>"
            )
        elif token.startswith("`"):
            parts.append(
                '<span style="background:#eeefe9;color:#23251d;padding:2px 6px;'
                "border-radius:4px;font-family:ui-monospace,Menlo,Monaco,Consolas,monospace;"
                f'font-size:13px;border:1px solid #b6b7af;">{leaf(token[1:-1])}</span>'
            )
        elif token.startswith("**"):
            parts.append(
                f'<strong style="color:#23251d;font-weight:800;">{leaf(token[2:-2])}</strong>'
            )
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
        parts.append(leaf(text[pos:]))
    return "".join(parts)


def inline_with_breaks(text):
    return "<br>".join(inline(line) for line in text.splitlines())


def compact_blockquote_lines(text):
    """Collapse blank quote lines while preserving intentional line breaks."""
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def paragraph(text):
    return (
        '<p style="margin:0 0 18px;font-size:15px;line-height:1.9;'
        f'text-align:justify;color:#4d4f46;padding:0 4px;">{inline(text)}</p>'
    )


def micro_heading(text):
    return (
        '<section style="margin:26px 0 10px;padding:0 4px;">'
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
        '<section style="margin:8px 0 18px;padding:0 4px;">'
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
        '<section style="margin:0 0 22px;padding:0 4px;">'
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
    content = text.strip("“”")
    if opening:
        content = compact_blockquote_lines(content)
        return (
            '<section style="margin-top:4px;margin-bottom:24px;padding:0 4px;">'
            '<section style="background:#f1f2ee;border-radius:8px;padding:14px 16px;'
            "font-family:'IBM Plex Sans',-apple-system,sans-serif;\">"
            f'<p style="margin:0;font-size:13px;line-height:1.75;color:#6b7067;text-align:justify;">{inline_with_breaks(content)}</p>'
            "</section></section>"
        )
    return (
        '<section style="margin:0 4px 24px;background:#eeefe9;border-radius:6px;'
        'border-left:4px solid #ed7b2f;padding:16px 18px;">'
        f'<p style="font-size:15px;font-weight:800;color:#23251d;margin:0;line-height:1.8;text-align:justify;">{inline_with_breaks("「" + content.strip("「」") + "」")}</p>'
        "</section>"
    )


def image_block(url):
    return (
        '<section style="margin:24px 0 18px;padding:0 4px;">'
        '<section style="background:#fdfdf8;border-radius:8px;padding:4px;'
        'border:1px solid #dfe2d8;">'
        '<figure style="margin:0;border-radius:6px;overflow:hidden;">'
        f'<span leaf=""><img src="{html.escape(url, quote=True)}" alt="图片" style="max-width:100%;height:auto;display:block;margin:0 auto;"></span>'
        "</figure></section></section>"
    )


def section_title(num, title):
    return (
        '<section style="margin-top:56px;margin-bottom:20px;padding:0 4px;">'
        "<section style=\"font-family:'PingFang SC','Hiragino Sans GB','Microsoft YaHei',-apple-system,BlinkMacSystemFont,sans-serif;text-align:left;\">"
        f'<p style="margin:0 0 10px;font-family:\'Helvetica Neue\',Arial,\'PingFang SC\',\'Hiragino Sans GB\',\'Microsoft YaHei\',-apple-system,BlinkMacSystemFont,sans-serif;font-size:54px;font-weight:900;color:#23251d;line-height:0.95;letter-spacing:0.5px;">{leaf(f"{num:02d}")}</p>'
        f'<p style="margin:0;font-size:23px;font-weight:900;color:#23251d;line-height:1.35;letter-spacing:0;text-align:left;">{leaf(title)}</p>'
        "</section></section>"
    )


def subheading(title):
    return (
        '<section style="margin:24px 0 16px;padding:0 4px;">'
        "<h3 style=\"font-size:18px;font-weight:800;color:#23251d;margin:0;"
        'padding:0 2px;display:inline;line-height:1.55;'
        'box-shadow:inset 0 -0.5em 0 rgba(245,78,0,0.18);">'
        f"{leaf(clean_heading(title))}</h3></section>"
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
        '<section style="margin:0 0 16px;padding:0 4px;">'
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
    if len(stripped) > 90:
        return False
    return bool(MICRO_HEADING.match(stripped))


def is_example_item(line):
    stripped = line.strip()
    return bool(EXAMPLE_ITEM.match(stripped) or ACTION_ITEM.match(stripped))


def is_question_item(line):
    stripped = line.strip()
    if stripped.startswith(("#", ">", "!", "|", "```")) or is_list_item(stripped):
        return False
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
        '<section style="margin:0 0 22px;padding:0 4px;">'
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


def render_minimal(md):
    lines = strip_frontmatter(md).splitlines()
    out = [
        "<section style=\"max-width:677px;margin:0 auto;padding:4px;box-sizing:border-box;"
        "background:#ffffff;color:#4d4f46;font-family:'IBM Plex Sans',-apple-system,system-ui,"
        "'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;line-height:1.75;\">"
    ]
    i = 0
    chapter = 0
    first_content = True
    while i < len(lines):
        line = lines[i].rstrip()
        if not line:
            i += 1
            continue
        if line.strip() == "---":
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
        if line.startswith("## "):
            chapter += 1
            out.append(section_title(chapter, clean_heading(line[3:])))
            first_content = False
            i += 1
            continue
        if line.startswith("### "):
            out.append(subheading(line[4:]))
            first_content = False
            i += 1
            continue
        if line.startswith("# "):
            i += 1
            continue
        if is_micro_heading(line):
            out.append(micro_heading(line.strip()))
            first_content = False
            i += 1
            continue
        if is_question_item(line):
            items, next_index = collect_consecutive_items(lines, i, is_question_item)
            if len(items) >= 2:
                out.append(question_list_block(items))
                first_content = False
                i = next_index
                continue
        if is_example_item(line):
            items, next_index = collect_consecutive_items(lines, i, is_example_item)
            if len(items) >= 2:
                out.append(example_list_block(items))
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
            out.append(image_block(image.group(1)))
            first_content = False
            i += 1
            continue
        if line.startswith(">"):
            q = [line.lstrip("> ").strip()]
            i += 1
            while i < len(lines) and lines[i].startswith(">"):
                q.append(lines[i].lstrip("> ").strip())
                i += 1
            out.append(quote_block("\n".join(q), opening=first_content))
            first_content = False
            continue
        if is_list_item(line):
            items = []
            while i < len(lines) and is_list_item(lines[i]):
                items.append(list_item_text(lines[i]))
                i += 1
            out.append(list_block(items))
            first_content = False
            continue
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
        out.append(paragraph(" ".join(para)))
        first_content = False
    out.append("</section>")
    return "\n".join(out) + "\n"


def render(md, theme):
    if theme != DEFAULT_THEME:
        raise SystemExit(
            f"deterministic renderer currently supports theme '{DEFAULT_THEME}', got '{theme}'. "
            "Use the theme component library for agent-led assembly or add a renderer adapter."
        )
    return render_minimal(md)


def default_output(input_path, theme):
    stem = Path(input_path).stem
    return Path.cwd() / f"{stem}-公众号排版-{theme}.html"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="Markdown file path")
    ap.add_argument("output", nargs="?", help="Output HTML path")
    ap.add_argument("--theme", default=DEFAULT_THEME, help="Theme id, default: minimal")
    args = ap.parse_args()

    src = Path(args.input)
    if not src.is_file():
        raise SystemExit(f"input not found: {src}")
    dst = Path(args.output) if args.output else default_output(src, args.theme)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(render(src.read_text(encoding="utf-8"), args.theme), encoding="utf-8")
    print(dst)


if __name__ == "__main__":
    main()
