#!/usr/bin/env python3
"""导入修改包：默认 dry-run，--apply 才快照并回填源文。"""
import argparse
import json
from pathlib import Path
import sys
from edit_model import apply_package


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', help='浏览器导出的 .gzh-edit.json 文件')
    parser.add_argument('--manifest', required=True, help='预览生成时的本地 manifest')
    parser.add_argument('--apply', action='store_true', help='验证后备份并真正回填；省略仅预览')
    args = parser.parse_args()
    try:
        package = json.loads(Path(args.package).read_text(encoding='utf-8'))
        print(json.dumps(apply_package(package, args.manifest, apply=args.apply), ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'blocked', 'reason': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
