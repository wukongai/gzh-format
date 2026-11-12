"""公众号标题的受控纯文字映射；不依赖完整 YAML 解析器、不改正文排版。"""
import json
from pathlib import Path
import re


FRONTMATTER = re.compile(r'\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)', re.S)


def checked_title(value):
    """输入框不能把换行或元数据注入标题，标题长度仅作资源上界。"""
    if (not isinstance(value, str) or not value.strip() or len(value) > 2000
            or any(ord(c) < 32 or 127 <= ord(c) <= 159 or c in '\u2028\u2029' or 0xD800 <= ord(c) <= 0xDFFF for c in value)):
        raise ValueError('标题必须为非空单行纯文字，不能含控制字符')
    return value


def _scalar(value):
    value = value.strip()
    if not value or value.startswith('#'):
        return ''
    if value.startswith('"'):
        match = re.fullmatch(r'("(?:[^"\\]|\\.)*")(?:\s+#.*)?', value)
        if not match:
            raise ValueError('复杂或多行 YAML 标题须在源 Markdown 中修改')
        try:
            result = json.loads(match.group(1))
        except ValueError as exc:
            raise ValueError('复杂 YAML 标题转义不支持，请在源 Markdown 中修改') from exc
        return checked_title(result) if result else ''
    if value.startswith("'"):
        match = re.fullmatch(r"'((?:[^']|'')*)'(?:\s+#.*)?", value)
        if not match:
            raise ValueError('复杂或多行 YAML 标题须在源 Markdown 中修改')
        return match.group(1).replace("''", "'")
    value = re.split(r'\s+#', value, maxsplit=1)[0].rstrip()
    if value.startswith(('|', '>', '!', '&', '*', '[', '{', '`')) or ': ' in value:
        raise ValueError('复杂 YAML 标题须在源 Markdown 中修改')
    return value


def _metadata(source):
    """只接受能明确定位的顶层 title；多行引号不能伪装成顶层字段。"""
    fm = FRONTMATTER.match(source)
    if not fm:
        if re.match(r'\A---(?:\r?\n|$)', source):
            raise ValueError('YAML frontmatter 未闭合，不能自动写入标题')
        return None, None, ''
    matches = []
    lines = list(re.finditer(r'[^\r\n]+(?:\r?\n|$)', source[fm.start(1):fm.end(1)]))
    for index, line in enumerate(lines):
        text = line.group().rstrip('\r\n')
        if re.match(r'^["\']', text):
            raise ValueError('复杂 YAML 带引号字段名不支持自动修改标题')
        scalar = re.match(r'^([^\s:#][^:#]*):\s*(.*?)\s*$', text)
        if not scalar:
            continue
        key, value = scalar.groups()
        key = key.rstrip()
        # 前置字段有跨行引号或 flow 时无法可靠判断下一行 title 的归属。
        if key != 'title' and ((value.startswith('"') and not re.fullmatch(r'"(?:[^"\\]|\\.)*"(?:\s+#.*)?', value))
                or (value.startswith("'") and not re.fullmatch(r"'(?:[^']|'')*'(?:\s+#.*)?", value))
                or (value.startswith('[') and not value.endswith(']'))
                or (value.startswith('{') and not value.endswith('}'))):
            raise ValueError('复杂或多行 YAML 元数据不支持自动修改标题')
        if key == 'title':
            for following in lines[index + 1:]:
                continuation = following.group().rstrip('\r\n')
                if not continuation.strip() or continuation.lstrip().startswith('#'):
                    continue
                if not continuation[0].isspace():
                    break
                raise ValueError('复杂或多行 YAML 标题须在源 Markdown 中修改')
            start = fm.start(1) + line.start()
            end = fm.start(1) + line.end()
            matches.append((start, end, _scalar(value)))
    if len(matches) > 1:
        raise ValueError('重复 YAML title 字段，请先在源 Markdown 中消歧')
    return fm, matches[0] if matches else None, matches[0][2] if matches else ''


def _h1(source):
    """只映射正文中的 ATX H1，代码块中的示例标题不参与回填。"""
    fm = FRONTMATTER.match(source)
    start = fm.end() if fm else 0
    fence = None
    in_comment = False
    headings = []
    for line in re.finditer(r'[^\n]+(?:\n|$)|\n', source[start:]):
        text = line.group().rstrip('\r\n')
        if fence is not None:
            # 关闭围栏只能有同类标记及尾部空白；带 info 的伪结束仍是代码。
            if re.fullmatch(r' {0,3}' + re.escape(fence[0]) + '{' + str(len(fence)) + r',}[ \t]*', text):
                fence = None
            continue
        if not in_comment and re.match(r'^#\s+', text) and '<!--' in text:
            raise ValueError('正文 H1 含内联注释，请先在源 Markdown 中确认文章标题')
        if in_comment or '<!--' in text:
            # 注释可能跨行且含有示例 H1，整行不参与文章标题映射。
            cursor = 0
            while cursor < len(text):
                token = text.find('-->' if in_comment else '<!--', cursor)
                if token < 0:
                    break
                cursor = token + (3 if in_comment else 4)
                in_comment = not in_comment
            continue
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})', text)
        if marker:
            fence = marker.group(1)
            continue
        heading = re.match(r'^#\s+(.+?)\s*$', text)
        if heading:
            headings.append((start + line.start(), start + line.end(), heading.group(1)))
    return headings


def title_info(source, source_path):
    """复杂 YAML 保持正文可编辑，标题只读并显示原因，绝不猜测写回。"""
    warning = ''
    value = ''
    try:
        _, _, value = _metadata(source)
        if value:
            checked_title(value)
    except ValueError as exc:
        warning = str(exc)
        value = ''
    try:
        headings = _h1(source)
    except ValueError as exc:
        headings = []
        warning = warning or str(exc)
    fallback = headings[0][2] if headings else Path(source_path).stem
    if len(headings) > 1:
        warning = warning or '存在多个正文 H1，请先在源 Markdown 中确认唯一文章标题'
    return {'title': value or fallback,
            'title_editable': not bool(warning), 'title_warning': warning}


def replace_title(source, value):
    """只替换 title 和已有唯一 H1，保留其余字节、换行和文件身份。"""
    value = checked_title(value)
    fm, title, _ = _metadata(source)
    headings = _h1(source)
    if len(headings) > 1:
        raise ValueError('存在多个正文 H1，不能自动同步文章标题')
    eol = '\r\n' if '\r\n' in source else '\n'
    replacements = []
    if headings:
        begin, end, _ = headings[0]
        trailing = eol if source[begin:end].endswith('\n') else ''
        replacements.append((begin, end, '# ' + value + trailing))
    encoded = json.dumps(value, ensure_ascii=False)
    if title:
        begin, end, _ = title
        trailing = eol if source[begin:end].endswith('\n') else ''
        replacements.append((begin, end, 'title: ' + encoded + trailing))
    elif fm:
        at = source.find('\n') + 1
        replacements.append((at, at, 'title: ' + encoded + eol))
    else:
        replacements.append((0, 0, '---' + eol + 'title: ' + encoded + eol + '---' + eol + eol))
    for begin, end, replacement in sorted(replacements, reverse=True):
        source = source[:begin] + replacement + source[end:]
    return source
