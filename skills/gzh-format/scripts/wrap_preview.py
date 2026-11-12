#!/usr/bin/env python3
"""把已校验的公众号正文片段（纯 <section>）包成带「复制」按钮的浏览器预览页。

用户打开预览页 → 点右上角「复制到公众号」→ 按钮选中并复制里面渲染后的富文本
（等价手动 Ctrl+A/Ctrl+C，样式全保留）→ 到公众号编辑器 Ctrl+V 粘贴即可。

按钮和 JS 只存在于预览外壳里，**不在被复制的 section 内**，所以粘进公众号的
仍是干净合规的正文，不含 <script>/<button>。校验请对原始 section 文件跑
validate_gzh_html.py（本预览页含 script/style，不参与校验）。

用法:
    wrap_preview.py <section.html> [output.html]
    默认输出 <section去扩展名>_预览.html
"""

import argparse
import html
import json
import re
from pathlib import Path

from _stdio import configure_utf8_stdio

configure_utf8_stdio()


def render_preview(content, title, manifest=None, save_bridge=None):
    """脚本和编辑标识仅进入预览外壳，JSON 用转义避免闭合 script。"""
    assets = Path(__file__).resolve().parents[1] / 'assets'
    tpl = (assets / 'preview-template.html').read_text(encoding='utf-8')
    css, script = '', ''
    readonly = ' readonly'
    title_warning = ''
    if manifest is not None:
        from edit_model import editable_body, public_package
        content = editable_body(content, manifest)
        metadata = public_package(manifest)
        title = metadata['title']
        readonly = '' if manifest.get('title_editable', True) else ' readonly'
        title_warning = manifest.get('title_warning', '')
        if save_bridge is not None:
            metadata['save_bridge'] = save_bridge
        data = json.dumps(metadata, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
        css = '<style>' + (assets / 'editor.css').read_text(encoding='utf-8') + '</style>'
        script = '<script id="gzh-edit-data" type="application/json">' + data + '</script>\n<script>' + (assets / 'editor.js').read_text(encoding='utf-8') + '</script>'
    replacements = {'{{TITLE}}': html.escape(title, quote=True),
                    '{{TITLE_READONLY}}': readonly, '{{TITLE_WARNING}}': html.escape(title_warning),
                    '<!--GZH_CONTENT-->': content, '<!--GZH_EDIT_CSS-->': css, '<!--GZH_EDIT_SCRIPT-->': script}
    # 单次替换模板标记，作者标题里的教学占位符不再被解释为模板指令。
    pattern = '|'.join(re.escape(token) for token in replacements)
    return re.sub(pattern, lambda match: replacements[match.group()], tpl)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', help='已经校验的公众号正文 HTML')
    parser.add_argument('output', nargs='?', help='预览路径，默认 <stem>_预览.html')
    parser.add_argument('--editable', action='store_true', help='生成可编辑预览与基线 manifest')
    parser.add_argument('--source-md', help='产生正文 HTML 的实际 Markdown 工作副本')
    parser.add_argument('--manifest', help='本地来源 manifest，默认正文同目录同名前缀')
    args = parser.parse_args()
    src = Path(args.source).resolve()
    out = Path(args.output).resolve() if args.output else src.with_name(src.stem + '_预览.html')
    if args.editable and not args.source_md:
        parser.error('--editable 必须指定 --source-md，不能猜测源文')
    # 编辑映射基于磁盘原文偏移，读取正文时不能自动把 CRLF 变成 LF。
    with src.open('r', encoding='utf-8', newline='') as stream:
        content = stream.read()
    manifest = None
    if args.editable:
        from edit_model import build_manifest, default_manifest, load_manifest, atomic_write
        path = Path(args.manifest).resolve() if args.manifest else default_manifest(src)
        protected = {src, Path(args.source_md).resolve(), path}
        if len(protected) != 3 or out in protected:
            parser.error('源 Markdown、正文 HTML、manifest、预览输出路径必须互异，禁止软链别名覆盖')
        if path.exists():
            manifest = load_manifest(path)
            if Path(manifest['source_md']) != Path(args.source_md).resolve() or Path(manifest['html_file']) != src:
                parser.error('manifest 已绑定其它源文件，拒绝覆盖')
        else:
            manifest = build_manifest(args.source_md, src)
        if not args.output and path.exists():
            out = Path(manifest['preview_file'])
        if path.exists() and Path(manifest['preview_file']) != out:
            parser.error('manifest 已绑定另一预览输出路径；请复用已绑定路径')
        manifest['preview_file'] = str(out)
        preview = render_preview(content, src.stem, manifest)
        atomic_write(path, json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
        print(f'编辑基线：{path}')
    else:
        title = src.stem
        if args.source_md:
            from article_title import title_info
            from edit_model import read_exact
            title = title_info(read_exact(args.source_md), args.source_md)['title']
        preview = render_preview(content, title)
    if out == src:
        parser.error('预览输出不能覆盖正文 HTML')
    with out.open('w', encoding='utf-8', newline='') as stream:
        stream.write(preview)
    print(f'✓ 已生成预览页：{out}')
    if args.editable:
        print('要直接保存草稿，请用 serve_preview.py --manifest <上述基线> 打开本地保存页面。')


if __name__ == "__main__":
    main()
