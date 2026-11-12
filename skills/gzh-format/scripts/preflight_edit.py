#!/usr/bin/env python3
"""同步前验证已保存修订：不联网、不读取公众号凭证。"""
import argparse
import json
import sys
from edit_model import preflight, refresh_sync_metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, help='当前文章编辑 manifest')
    parser.add_argument('--pending-package', action='append', default=[], help='可重复指定下载目录等处的待导入包')
    parser.add_argument('--refresh-metadata-from', help='同步成功写回后的源文写前备份，仅登记已知微信字段变化')
    parser.add_argument('--apply', action='store_true', help='与 --refresh-metadata-from 一起真正刷新元数据基线；省略仅校验')
    parser.add_argument('--expected-revision', type=int, help='实际发送请求时的人工修订号')
    parser.add_argument('--expected-source-sha256', help='实际发送请求时的源文哈希')
    parser.add_argument('--expected-html-sha256', help='实际发送请求时的正文 HTML 哈希')
    args = parser.parse_args()
    try:
        if args.apply and not args.refresh_metadata_from:
            parser.error('--apply 仅与 --refresh-metadata-from 一起使用')
        result = refresh_sync_metadata(args.manifest, args.refresh_metadata_from, expected_revision=args.expected_revision,
                                       expected_source_sha256=args.expected_source_sha256,
                                       expected_html_sha256=args.expected_html_sha256, apply=args.apply) if args.refresh_metadata_from else preflight(args.manifest, args.pending_package)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'blocked', 'reason': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
