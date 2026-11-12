"""公众号人工修订的本地事实模型：映射、白名单、快照与冲突保护。

导出包仅携带受控文字 runs；源路径只从本地 manifest 读取，绝不执行包内 HTML。
"""
from __future__ import annotations

import copy
import hashlib
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
from datetime import datetime, timezone
import uuid
from contextlib import contextmanager

import render_markdown as renderer
from validate_gzh_html import validate
from article_title import checked_title, replace_title, title_info

SCHEMA = 'gzh-edit/v1'
MANIFEST_SCHEMA = 'gzh-edit-manifest/v1'
MARKER = '<!-- gzh-manual-revision:v1 -->'
MARKS = {'code', 'underline', 'strike', 'highlight'}
HEADING_NUMBER = re.compile(r'^\s*(?:\d+(?:[.．、)）]|\s)|[一二三四五六七八九十百]+[、.．]|[（(](?:\d+|[一二三四五六七八九十百]+)[）)])\s*')


def read_exact(path):
    """保留原换行字节对应字符，避免未编辑 CRLF 片段被全篇改写。"""
    with Path(path).open('r', encoding='utf-8', newline='') as stream:
        return stream.read()


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def default_manifest(html_path):
    path = Path(html_path)
    return path.with_name(path.stem + '.gzh-edit-manifest.json')


def render_checked(source, mode, mapping=None):
    """把 renderer 的 CLI 拒绝语义转换为导入器可报告的校验失败。"""
    try:
        return renderer.render(source, 'minimal', mode, source_map=mapping)
    except SystemExit as exc:
        raise ValueError(str(exc)) from exc


class Node:
    def __init__(self, tag='', attrs=None, start=0, open_end=0, parent=None):
        self.tag, self.attrs = tag, dict(attrs or [])
        self.start, self.open_end = start, open_end
        self.close_start = self.end = open_end
        self.children, self.parent = [], parent

    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child, Node):
                yield from child.walk()


class Tree(HTMLParser):
    """保留原 HTML 字符区间，避免用序列化器改动未编辑组件。"""
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.text = text
        self.line_starts = [0] + [m.end() for m in re.finditer('\n', text)]
        self.root = Node()
        self.stack = [self.root]
        self.feed(text)

    def absolute_position(self):
        line, column = self.getpos()
        return self.line_starts[line - 1] + column

    def handle_starttag(self, tag, attrs):
        start = self.absolute_position()
        node = Node(tag, attrs, start, start + len(self.get_starttag_text()), self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in {'img', 'br', 'hr', 'wbr', 'input', 'meta', 'link'}:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if self.stack[-1].tag == tag:
            self.stack.pop()

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                node = self.stack[i]
                node.close_start = self.absolute_position()
                node.end = self.text.find('>', node.close_start) + 1
                del self.stack[i:]
                break

    def handle_data(self, text):
        self.stack[-1].children.append(text)


def styles(node, inherited=None):
    state = dict(inherited or {'red': False, 'bold': False, 'href': '', 'marks': []})
    state['marks'] = list(state['marks'])
    css = dict(re.findall(r'([\w-]+)\s*:\s*([^;]+)', node.attrs.get('style', '')))
    if 'color' in css:
        state['red'] = css['color'].strip().lower() in {'#dc2626', '#c7254e', 'red'}
    weight = css.get('font-weight', '')
    if weight:
        state['bold'] = weight in {'bold', 'bolder'} or (weight.isdigit() and int(weight) >= 600)
    elif node.tag in {'strong', 'b'}:
        state['bold'] = True
    if node.tag == 'a':
        state['href'] = node.attrs.get('href', '')
    style = node.attrs.get('style', '').lower()
    for mark, found in [('code', node.tag == 'code' or 'monospace' in style),
                        ('underline', node.tag == 'u' or 'border-bottom' in css or 'underline' in css.get('text-decoration', '')),
                        ('strike', 'line-through' in css.get('text-decoration', '')),
                        ('highlight', node.tag == 'span' and 'background' in css and 'code' not in state['marks'])]:
        if found and mark not in state['marks']:
            state['marks'].append(mark)
    return state


def node_runs(node, inherited=None):
    state = styles(node, inherited)
    out = []
    for child in node.children:
        if isinstance(child, str):
            if child:
                out.append(dict(state, text=child))
        elif child.tag == 'br':
            out.append(dict(state, text='\n'))
        else:
            out.extend(node_runs(child, state))
    return merge_runs(out)


def merge_runs(runs):
    result = []
    for run in runs:
        if not run['text']:
            continue
        run = dict(run, marks=sorted(run.get('marks', [])))
        if result and all(result[-1][key] == run[key] for key in ('red', 'bold', 'href', 'marks')):
            result[-1]['text'] += run['text']
        else:
            result.append(run)
    return result


def image_urls(text):
    return [n.attrs.get('src', '') for n in Tree(text).root.walk() if n.tag == 'img']


def heading_texts(text):
    return [''.join(r['text'] for r in node_runs(n)) for n in Tree(text).root.walk() if n.tag == 'h3']


def build_manifest(source_md, html_file, *, revision=0, imported=None):
    """只绑定能够确定性重现的 minimal 正文，拒绝猜测旧 HTML 源映射。"""
    source_md, html_file = Path(source_md).resolve(), Path(html_file).resolve()
    source, body = read_exact(source_md), read_exact(html_file)
    mode = renderer.resolve_mode(source, source_md)
    mapping = []
    generated = render_checked(source, mode, mapping)
    # Windows 文本写入会把 LF HTML 转为 CRLF；同步映射偏移后仍逐字核对正文。
    # 不改原文件或哈希，也不把文字/结构差异当作换行差异放行。
    if '\r\n' in body and '\n' not in body.replace('\r\n', '') and '\r' not in generated:
        for record in mapping:
            for key in ('html_start', 'html_end'):
                offset = record[key]
                record[key] += generated.count('\n', 0, offset)
        generated = generated.replace('\n', '\r\n')
    if generated.strip() != body.strip():
        raise ValueError('HTML 与源 Markdown 不对应；请从实际渲染工作副本重新生成，禁止猜测回填')
    # renderer 总是末尾换行；允许 CLI 的旧片段没有该换行，不改变节点区间。
    blocks = []
    for record in mapping:
        kind = record['kind']
        fragment = generated[record['html_start']:record['html_end']]
        tree = Tree(fragment)
        targets = [n for n in tree.root.walk() if n.tag == ('h3' if kind == 'h3' else 'h4' if kind == 'micro' else 'p')]
        extra_open_ends = []
        number_text = None
        number_explicit = False
        if kind == 'h2':
            # 章节编号和标题共用一个编辑块，但编号视觉上单独占一行。
            if len(targets) >= 2:
                extra_open_ends = [record['html_start'] + target.open_end for target in targets[:-1]]
                number_text = ''.join(r['text'] for r in node_runs(targets[0]))
            targets = targets[-1:]
        source_piece = source[record['start']:record['end']]
        if kind == 'h2':
            heading_line = source_piece.splitlines()[0] if source_piece.splitlines() else ''
            if heading_line.startswith('## '):
                _, number_explicit, _ = renderer.heading_number_info(heading_line[3:])
        if kind == 'list':
            # 每个列表正文有自己的源行；项目符号和图形不进入编辑区。
            source_lines = list(re.finditer(r'[^\n]+(?:\n|$)', source_piece))
            source_lines = [m for m in source_lines if renderer.is_list_item(m.group().rstrip())]
            if len(source_lines) != len(targets):
                continue
        elif len(targets) != 1:
            continue
        for index, target in enumerate(targets):
            start, end = record['start'], record['end']
            if kind == 'list':
                start += source_lines[index].start()
                end = record['start'] + source_lines[index].end()
            # 无法表示的双链或嵌入保留源块只读，避免编辑其它字时顺手重写语法。
            if '[[' in source[start:end] or '![' in source[start:end]:
                continue
            prefix = ''
            if kind in {'h2', 'h3'}:
                prefix = re.match(r'#+\s+', source[start:end]).group()
            elif kind == 'list':
                prefix = re.match(r'\s*(?:[-*+]\s+|\d+[.)、]\s+)', source[start:end]).group()
            elif kind == 'quote':
                prefix = '> '
            ancestors = []
            parent = target.parent
            while parent and parent.tag:
                ancestors.append(parent)
                parent = parent.parent
            inherited = None
            for ancestor in reversed(ancestors):
                inherited = styles(ancestor, inherited)
            block = {'id': f'b{len(blocks):04d}', 'kind': kind,
                     'start': start, 'end': end, 'prefix': prefix,
                     'open_end': record['html_start'] + target.open_end,
                     'extra_open_ends': extra_open_ends,
                     'runs': node_runs(target, inherited)}
            if kind == 'h2':
                block['number'] = number_text or ''
                block['number_explicit'] = number_explicit
            blocks.append(block)
    if not blocks:
        raise ValueError('没有可可靠回填的文字块')
    identity = sha(str(source_md) + '\0' + str(html_file))[:24]
    return {'schema': MANIFEST_SCHEMA, 'article_id': identity, 'revision': revision,
            'status': 'saved' if revision else 'baseline', 'source_md': str(source_md),
            'html_file': str(html_file), 'source_sha256': sha(source), 'html_sha256': sha(body),
            'preview_file': str(html_file.with_name(html_file.stem + '_预览.html')),
            'mode': mode, **title_info(source, source_md), 'blocks': blocks, 'images': image_urls(body),
            'headings': heading_texts(body), 'imported_packages': list(imported or [])}


def public_package(manifest):
    return {'schema': SCHEMA, **{key: copy.deepcopy(manifest[key]) for key in
            ('article_id', 'revision', 'source_sha256', 'html_sha256', 'images', 'headings')},
            'title': manifest.get('title', title_info(read_exact(manifest['source_md']), manifest['source_md'])['title']),
            'blocks': [{**{key: copy.deepcopy(block[key]) for key in ('id', 'kind', 'runs')},
                       **({'number': copy.deepcopy(block.get('number', '')), 'number_explicit': bool(block.get('number_explicit', False))}
                          if block.get('kind') == 'h2' else {})}
                      for block in manifest['blocks']]}


def editable_body(body, manifest):
    """只给预览加编辑标识，正文产物与复制内容不带这些属性。"""
    for block in sorted(manifest['blocks'], key=lambda b: b['open_end'], reverse=True):
        positions = [(block['open_end'], 'main')]
        positions.extend((position, 'number') for position in block.get('extra_open_ends', []))
        for open_end, part in sorted(positions, reverse=True):
            pos = open_end - 1
            empty = ' data-gzh-edit-empty="1"' if not block['runs'] else ''
            marker = f' data-gzh-edit-id="{block["id"]}"'
            if part != 'main': marker += f' data-gzh-edit-part="{part}"'
            body = body[:pos] + marker + empty + body[pos:]
    return body


def checked_runs(runs, baseline):
    if not isinstance(runs, list) or len(runs) > 10000:
        raise ValueError('invalid runs')
    links = {r['href'] for r in baseline}
    allowed_marks = {m for r in baseline for m in r['marks']}
    result = []
    for run in runs:
        if not isinstance(run, dict) or set(run) - {'text', 'red', 'bold', 'href', 'marks'}:
            raise ValueError('unsupported run fields')
        if not isinstance(run.get('text'), str) or any(ord(c) < 32 and c not in '\n\t' for c in run['text']):
            raise ValueError('invalid text')
        if len(run['text']) > 200000 or type(run.get('red')) is not bool or type(run.get('bold')) is not bool:
            raise ValueError('invalid style')
        href, marks = run.get('href', ''), run.get('marks', [])
        if not isinstance(href, str) or (href and (not re.match(r'^https?://[^\s<>]+$', href) or href not in links)):
            raise ValueError('unsafe or changed link')
        if not isinstance(marks, list) or any(not isinstance(m, str) or m not in MARKS or m not in allowed_marks for m in marks):
            raise ValueError('unsupported marks')
        result.append(dict(run, href=href, marks=marks))
    return merge_runs(result)


def checked_number(value):
    """校验可单独编辑的章节序号；空字符串代表删除序号。"""
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError('invalid heading number')
    if any(ord(c) < 32 and c not in '\t' for c in value) or '<' in value or '>' in value or '--' in value:
        raise ValueError('invalid heading number')
    return value.strip()


def h2_number_source(number):
    """把 H2 的人工序号写成不会混入标题正文的 Markdown 注释。"""
    return f'<!-- gzh-h2-number:{number} --> '


def source_runs(runs):
    parts = []
    for run in runs:
        attrs = f'data-gzh="manual-style" data-red="{int(run["red"])}" data-bold="{int(run["bold"])}"'
        if run['href']:
            attrs += f' data-href="{html.escape(run["href"], quote=True)}"'
        if run['marks']:
            attrs += f' data-marks="{" ".join(run["marks"])}"'
        # 一行源标记内使用实体表示换行；renderer 负责映射成 br。
        parts.append(f'<span {attrs}>{html.escape(run["text"], quote=False).replace(chr(10), "&#10;")}</span>')
    return ''.join(parts)


def load_manifest(path):
    state = json.loads(Path(path).read_text(encoding='utf-8'))
    if state.get('schema') != MANIFEST_SCHEMA:
        raise ValueError('unsupported manifest')
    paths = [Path(state[key]).resolve() for key in ('source_md', 'html_file', 'preview_file')]
    paths.append(Path(path).resolve())
    if len(set(paths)) != len(paths):
        raise ValueError('源文、正文、预览与 manifest 路径必须互异（包括软链别名）')
    for key, path_key in [('source_sha256', 'source_md'), ('html_sha256', 'html_file')]:
        if sha(read_exact(state[path_key])) != state[key]:
            raise ValueError(f'conflict: {path_key} 来源漂移，零写入')
    # 旧 manifest 没有标题字段；按已核验的源文件补入内存，不偷偷写磁盘。
    if 'title' not in state:
        state.update(title_info(read_exact(state['source_md']), state['source_md']))
    return state


def atomic_write(path, text):
    path = Path(path)
    temp = path.with_name('.' + path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temp.open('w', encoding='utf-8', newline='') as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


@contextmanager
def edit_lock(path):
    """同一文章的导入互斥；异常退出留下的锁需人工核实进程后处理。"""
    lock = Path(str(path) + '.lock')
    try:
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise ValueError('conflict: 当前文章正由另一保存进程写入，或存在待核实的中断锁') from exc
    try:
        os.close(fd)
        yield
    finally:
        lock.unlink()


def apply_package(package, manifest_path, *, apply=False):
    if not apply:
        return _apply_package(package, manifest_path, apply=False)
    with edit_lock(Path(manifest_path).resolve()):
        return _apply_package(package, manifest_path, apply=True)


def compose_package(package, state, source, body):
    """纯函数：把受控文字状态组装成源文和正文，不接触磁盘。"""
    allowed = {'schema', 'article_id', 'revision', 'source_sha256', 'html_sha256', 'images', 'headings', 'blocks', 'saved_at', 'title'}
    if not isinstance(package, dict) or set(package) - allowed or package.get('schema') != SCHEMA:
        raise ValueError('invalid edit package schema/fields')
    for key in ('article_id', 'revision', 'source_sha256', 'html_sha256', 'images', 'headings'):
        if package.get(key) != state[key]:
            raise ValueError(f'conflict: {key} 与当前基线不符，零写入')
    candidates = package.get('blocks')
    if not isinstance(candidates, list) or len(candidates) != len(state['blocks']):
        raise ValueError('block set changed')
    source_path, html_path = Path(state['source_md']), Path(state['html_file'])
    replacements, changes = [], []
    for expected, edited in zip(state['blocks'], candidates):
        allowed_fields = {'id', 'kind', 'runs'} | ({'number', 'number_explicit'} if expected['kind'] == 'h2' else set())
        if not isinstance(edited, dict) or set(edited) - allowed_fields or edited.get('id') != expected['id']:
            raise ValueError('block identity/order changed')
        if edited.get('kind', expected['kind']) != expected['kind']:
            raise ValueError('block kind changed')
        runs = checked_runs(edited.get('runs'), expected['runs'])
        number = expected.get('number', '')
        number_changed = False
        if expected['kind'] == 'h2':
            number = checked_number(edited.get('number', number))
            number_changed = number != expected.get('number', '')
        if runs == merge_runs(expected['runs']) and not number_changed:
            continue
        visible = ''.join(r['text'] for r in runs)
        previous = ''.join(r['text'] for r in expected['runs'])
        original = source[expected['start']:expected['end']]
        newline = '\r\n' if original.endswith('\r\n') else '\n' if original.endswith('\n') else ''
        if runs:
            number_prefix = ''
            if expected['kind'] == 'h2':
                if number_changed or expected.get('number_explicit'):
                    number_prefix = h2_number_source(number)
                elif original.startswith(expected['prefix']):
                    source_heading = original[len(expected['prefix']):].splitlines()[0]
                    source_number, source_explicit, _ = renderer.heading_number_info(source_heading)
                    if source_explicit and source_number:
                        number_prefix = h2_number_source(source_number)
            replacement = expected['prefix'] + number_prefix + source_runs(runs) + newline
        else:
            replacement = ''
        replacements.append((expected['start'], expected['end'], replacement))
        change = {'id': expected['id'], 'kind': expected['kind'], 'before_text': previous,
                  'after_text': visible, 'before_runs': expected['runs'], 'after_runs': runs}
        if expected['kind'] == 'h2':
            change.update({'before_number': expected.get('number', ''), 'after_number': number})
        changes.append(change)
    updated = source
    for start, end, replacement in sorted(replacements, reverse=True):
        updated = updated[:start] + replacement + updated[end:]
    current_title = state.get('title', title_info(source, state['source_md'])['title'])
    next_title = checked_title(package['title']) if 'title' in package else current_title
    title_changed = next_title != current_title
    if title_changed:
        updated = replace_title(updated, next_title)
    if replacements and MARKER not in updated:
        # frontmatter 必须保持首部；正文前插入 marker。
        frontmatter = re.match(r'\A---\r?\n.*?\r?\n---(?:\r?\n|$)', updated, flags=re.S)
        fm_end = frontmatter.end() if frontmatter else 0
        eol = '\r\n' if '\r\n' in source else '\n'
        updated = updated[:fm_end] + eol + MARKER + eol + updated[fm_end:]
    rendered = render_checked(updated, state['mode']) if replacements else body
    if image_urls(rendered) != state['images']:
        raise ValueError('图片集合或顺序变化，拒绝导入')
    # 显式“删除整行”允许移除 H3；其余标题仍按原顺序保留编号。
    deleted_heading_ids = {
        expected['id']
        for expected, edited in zip(state['blocks'], candidates)
        if expected['kind'] == 'h3' and not checked_runs(edited.get('runs'), expected['runs'])
    }
    old_heading_texts = list(state['headings'])
    for block in state['blocks']:
        if block['kind'] != 'h3' or block['id'] not in deleted_heading_ids:
            continue
        previous = ''.join(run['text'] for run in block['runs'])
        if previous in old_heading_texts:
            old_heading_texts.remove(previous)
    new_headings = heading_texts(rendered)
    if len(new_headings) != len(old_heading_texts):
        raise ValueError('H3 数量变化，拒绝导入')
    errors, _, _ = validate(rendered)
    if errors:
        raise ValueError('invalid HTML: ' + '; '.join(errors))
    result = {'status': 'dry-run', 'changed_blocks': len(replacements), 'title_changed': title_changed, 'changes': changes, 'revision': state['revision'] + 1,
              'source_md': str(source_path), 'html_file': str(html_path), 'article_id': state['article_id']}
    return updated, rendered, result


def _apply_package(package, manifest_path, *, apply=False):
    """保留修改包兼容入口；直接保存与此入口共用组装和落盘实现。"""
    manifest_path = Path(manifest_path).resolve()
    state = load_manifest(manifest_path)
    if sha(canonical(package)) in state['imported_packages']:
        return {'status': 'already-imported', 'revision': state['revision'], 'html_file': state['html_file']}
    source, body = read_exact(state['source_md']), read_exact(state['html_file'])
    updated, rendered, result = compose_package(package, state, source, body)
    if not apply:
        return result
    return commit_revision(manifest_path, state, package, source, body, updated, rendered, result)


def commit_revision(manifest_path, state, package, source, body, updated, rendered, result):
    """调用者持有文章锁；原稿快照与多文件回填只有这一份实现。"""
    manifest_path = Path(manifest_path).resolve()
    source_path, html_path = Path(state['source_md']), Path(state['html_file'])
    fingerprint = sha(canonical(package))
    # 当前基线再次检查，防止验证期间其它会话已改稿。
    current = load_manifest(manifest_path)
    if any(current.get(key) != state.get(key) for key in ('article_id', 'revision', 'source_sha256', 'html_sha256', 'source_md', 'html_file', 'preview_file')):
        raise ValueError('conflict: 验证期间保存修订发生变化')
    revision = state['revision'] + 1
    revision_dir = html_path.parent / '.gzh-edits' / state['article_id'] / f'r{revision:04d}-{uuid.uuid4().hex[:8]}'
    revision_dir.mkdir(parents=True, exist_ok=False)
    old_manifest = read_exact(manifest_path)
    preview_path = Path(state['preview_file'])
    old_preview = read_exact(preview_path) if preview_path.exists() else None
    try:
        (revision_dir / 'source.md').write_bytes(source.encode('utf-8'))
        (revision_dir / 'body.html').write_bytes(body.encode('utf-8'))
        (revision_dir / 'manifest.json').write_text(canonical(state), encoding='utf-8')
        (revision_dir / 'package.gzh-edit.json').write_text(canonical(package), encoding='utf-8')
        atomic_write(source_path, updated)
        atomic_write(html_path, rendered)
        next_state = build_manifest(source_path, html_path, revision=revision,
                                    imported=state['imported_packages'] + [fingerprint])
        next_state['preview_file'] = str(preview_path)
        next_state['saved_at'] = datetime.now(timezone.utc).isoformat()
        # 保存后修订副本独立于可回填当前源文件。
        (revision_dir / 'saved.md').write_bytes(updated.encode('utf-8'))
        (revision_dir / 'saved.html').write_bytes(rendered.encode('utf-8'))
        from wrap_preview import render_preview
        preview = render_preview(rendered, html_path.stem, next_state)
        atomic_write(preview_path, preview)
        atomic_write(manifest_path, json.dumps(next_state, ensure_ascii=False, indent=2) + '\n')
    except BaseException:
        atomic_write(source_path, source)
        atomic_write(html_path, body)
        atomic_write(manifest_path, old_manifest)
        if old_preview is not None:
            atomic_write(preview_path, old_preview)
        elif preview_path.exists():
            preview_path.unlink()
        # 保留失败尝试的备份和原因；下一次独立目录可安全重试。
        (revision_dir / 'failed.txt').write_text('保存失败，当前文件已尝试恢复；请以 manifest 预检结果为准。\n', encoding='utf-8')
        raise
    result.update(status='saved', backup_dir=str(revision_dir), preview_html=str(preview_path))
    return result


class EditSession:
    """单篇文章保存会话；保留起始块身份，让保存后的 undo 仍能恢复删段。

    当前磁盘 revision 是冲突依据；起始源文只用于重建完整编辑状态。它不能
    覆盖其它会话后来写入的内容，也不会把浏览器连接令牌写进文章或 manifest。
    """
    def __init__(self, manifest_path):
        self.path = Path(manifest_path).resolve()
        with edit_lock(self.path):
            self.current = load_manifest(self.path)
            self.base = copy.deepcopy(self.current)
            self.source = read_exact(self.current['source_md'])
            self.body = read_exact(self.current['html_file'])
            self.blocks = public_package(self.base)['blocks']
        self.last_fingerprint = None

    def check_current(self):
        actual = load_manifest(self.path)
        fields = ('article_id', 'revision', 'source_sha256', 'html_sha256', 'source_md', 'html_file', 'preview_file')
        if any(actual.get(key) != self.current.get(key) for key in fields):
            raise ValueError('conflict: 文章已由其它会话保存，请重新打开保存服务')
        return actual

    def public_package(self):
        self.check_current()
        value = public_package(self.current)
        value['blocks'] = copy.deepcopy(self.blocks)
        return value

    def snapshot(self):
        """用当前内容填起始排版壳，并为稳定空块重算准确的预览 HTML 偏移。"""
        self.check_current()
        nodes = {node.open_end: node for node in Tree(self.body).root.walk() if node.tag}
        pieces, position, length, mapped = [], 0, 0, []

        def replace_number_inner(fragment, number):
            escaped = html.escape(number, quote=False)
            return re.sub(r'(?<=>)[^<>]*(?=<)', escaped, fragment, count=1)

        for original, block in zip(self.base['blocks'], self.blocks):
            node = nodes[original['open_end']]
            prefix = self.body[position:node.open_end]
            if original['kind'] == 'h2' and original.get('extra_open_ends'):
                number_node = nodes[original['extra_open_ends'][0]]
                number_inner = self.body[number_node.open_end:number_node.close_start]
                number_inner = replace_number_inner(number_inner, block.get('number', original.get('number', '')))
                prefix = (
                    self.body[position:number_node.open_end]
                    + number_inner
                    + self.body[number_node.close_start:node.open_end]
                )
            pieces.append(prefix)
            length += len(prefix)
            record = copy.deepcopy(original)
            record.update(id=block['id'], kind=block['kind'], runs=copy.deepcopy(block['runs']), open_end=length)
            if block['kind'] == 'h2':
                record['number'] = block.get('number', original.get('number', ''))
            if merge_runs(block['runs']) == merge_runs(original['runs']):
                inner = self.body[node.open_end:node.close_start]
            else:
                inner = renderer.inline(source_runs(block['runs'])) if block['runs'] else ''
            pieces.append(inner)
            length += len(inner)
            position = node.close_start
            mapped.append(record)
        pieces.append(self.body[position:])
        state = copy.deepcopy(self.current)
        state['blocks'] = mapped
        return ''.join(pieces), state

    def save(self, package):
        with edit_lock(self.path):
            actual = self.check_current()
            # 浏览器重试会重新生成时间戳；相同修订和文字状态应认作同一次保存。
            identity = {key: value for key, value in package.items() if key != 'saved_at'} if isinstance(package, dict) else package
            fingerprint = sha(canonical(identity))
            if fingerprint == self.last_fingerprint:
                return {'status': 'already-imported', 'revision': actual['revision'], 'package': self.public_package()}
            for key in ('article_id', 'revision', 'source_sha256', 'html_sha256', 'images', 'headings'):
                if not isinstance(package, dict) or package.get(key) != actual[key]:
                    raise ValueError(f'conflict: {key} 与已保存草稿不符')
            # 校验沿用起始块范围、链接和编号，身份校验则使用本次实际磁盘 revision。
            normalized = copy.deepcopy(package)
            # 旧客户端没有标题字段时保留当前标题，不能退回会话初始标题。
            normalized.setdefault('title', actual['title'])
            for key in ('article_id', 'revision', 'source_sha256', 'html_sha256', 'images', 'headings'):
                normalized[key] = self.base[key]
            updated, rendered, result = compose_package(normalized, self.base, self.source, self.body)
            source, body = read_exact(actual['source_md']), read_exact(actual['html_file'])
            if updated == source and rendered == body and actual['status'] == 'saved':
                result = {'status': 'saved', 'changed_blocks': 0, 'revision': actual['revision']}
            else:
                result['revision'] = actual['revision'] + 1
                result = commit_revision(self.path, actual, package, source, body, updated, rendered, result)
            self.current = load_manifest(self.path)
            self.blocks = []
            for base, edited in zip(self.base['blocks'], package['blocks']):
                current_block = {'id': base['id'], 'kind': base['kind'], 'runs': checked_runs(edited['runs'], base['runs'])}
                if base['kind'] == 'h2':
                    current_block['number'] = checked_number(edited.get('number', base.get('number', '')))
                    current_block['number_explicit'] = bool(base.get('number_explicit', False) or current_block['number'] != base.get('number', ''))
                self.blocks.append(current_block)
            self.last_fingerprint = fingerprint
            result['package'] = self.public_package()
            return result


def preflight(manifest_path, pending_packages=()):
    """验证磁盘修订；浏览器 DOM 和下载目录不在自动发现范围内。"""
    path = Path(manifest_path).resolve()
    state = load_manifest(path)
    if state['status'] != 'saved':
        raise ValueError('尚未导入保存修改包，不能作为已保存人工修订同步')
    packages = set(path.parent.glob('*.gzh-edit.json')) | {Path(p).resolve() for p in pending_packages}
    for pending in packages:
        value = json.loads(pending.read_text(encoding='utf-8'))
        if value.get('article_id') == state['article_id'] and sha(canonical(value)) not in state['imported_packages']:
            raise ValueError(f'pending: 存在未导入修改包 {pending.name}')
    return {'manifest_file': str(path), **{key: state[key] for key in ('status', 'article_id', 'revision', 'source_md', 'html_file', 'source_sha256', 'html_sha256')}}


def refresh_sync_metadata(manifest_path, backup_source, *, expected_revision=None, expected_source_sha256=None, expected_html_sha256=None, apply=False):
    """同步成功后只接受已知 frontmatter 字段变化，正文漂移仍然阻断。

    backup_source 必须恰好是成功同步写前的源快照，以旧 SHA 核验。
    不改文章或正文 HTML，不提升人工修订号，只更新映射与预览基线。
    """
    path = Path(manifest_path).resolve()
    with edit_lock(path):
        state = json.loads(read_exact(path))
        if state.get('schema') != MANIFEST_SCHEMA or state.get('status') != 'saved':
            raise ValueError('仅已保存修订支持同步元数据回写登记')
        if any(value is None for value in (expected_revision, expected_source_sha256, expected_html_sha256)):
            raise ValueError('conflict: 必须提供发送微信请求时的修订号和源文/HTML 哈希')
        if (state['revision'], state['source_sha256'], state['html_sha256']) != (expected_revision, expected_source_sha256, expected_html_sha256):
            raise ValueError('conflict: 请求期间保存修订发生变化，不能登记为已同步')
        before, after = read_exact(backup_source), read_exact(state['source_md'])
        body = read_exact(state['html_file'])
        if sha(before) != state['source_sha256'] or sha(body) != state['html_sha256']:
            raise ValueError('conflict: 同步写前快照或 HTML 与保存基线不符')
        allowed = re.compile(r'^(?:digest|wechat_draft_(?:media_id|synced_at|status|title)|wechat_thumb_media_id)\s*:')
        def without_sync_metadata(text):
            fm = re.match(r'\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)', text, flags=re.S)
            if not fm:
                raise ValueError('同步元数据登记要求完整 frontmatter')
            # 此轻量登记器不解析完整 YAML。多行引号/flow、tag/anchor 等复杂值
            # 中的“digest:”可能是其它字段内容，必须拒绝，不能误当顶层白名单。
            for line in fm.group(1).splitlines():
                scalar = re.match(r'^\s*(?:[^\s:#][^:#]*:\s*|-\s+)(.*?)\s*$', line)
                if not scalar:
                    continue
                value = scalar.group(1)
                if (value.startswith('"') and not re.fullmatch(r'"(?:[^"\\]|\\.)*"(?:\s+#.*)?', value)
                    or value.startswith("'") and not re.fullmatch(r"'(?:[^']|'')*'(?:\s+#.*)?", value)
                    or value.startswith('[') and not value.endswith(']')
                    or value.startswith('{') and not value.endswith('}')
                    or value.startswith(('!', '&', '*'))):
                    raise ValueError('conflict: 多行引号或复杂 YAML 元数据不支持自动登记，须显式比较')
            kept = ''.join(line for line in fm.group(1).splitlines(keepends=True) if not allowed.match(line))
            return kept.rstrip('\r\n'), text[fm.end():]
        if without_sync_metadata(before) != without_sync_metadata(after):
            raise ValueError('conflict: 除已知同步字段外的元数据或正文发生变化，拒绝登记')
        next_state = build_manifest(state['source_md'], state['html_file'], revision=state['revision'], imported=state['imported_packages'])
        next_state['preview_file'] = state['preview_file']
        next_state['saved_at'] = state.get('saved_at', '')
        next_state['sync_metadata_refreshed_at'] = datetime.now(timezone.utc).isoformat()
        result = {'status': 'dry-run', 'revision': state['revision'], 'metadata_refreshed': False}
        if apply:
            preview_path = Path(state['preview_file'])
            old_preview = read_exact(preview_path) if preview_path.exists() else None
            old_manifest = read_exact(path)
            from wrap_preview import render_preview
            preview = render_preview(body, Path(state['html_file']).stem, next_state)
            try:
                atomic_write(preview_path, preview)
                atomic_write(path, json.dumps(next_state, ensure_ascii=False, indent=2) + '\n')
            except BaseException:
                atomic_write(path, old_manifest)
                if old_preview is not None:
                    atomic_write(preview_path, old_preview)
                elif preview_path.exists():
                    preview_path.unlink()
                raise
            result.update(status='saved', metadata_refreshed=True)
        return result
