#!/usr/bin/env python3
"""Run a small regression suite for gzh-format."""

import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = Path(tempfile.mkdtemp(prefix="gzh-format-regression-"))
SAMPLE = ROOT / "assets" / "sample-article.md"
STRESS = ROOT / "tests" / "fixtures" / "stress-markdown.md"


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


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    html = OUT_DIR / "sample-minimal.html"
    preview = OUT_DIR / "sample-minimal_预览.html"
    stress_html = OUT_DIR / "stress-minimal.html"
    stress_preview = OUT_DIR / "stress-minimal_预览.html"

    run([sys.executable, ROOT / "scripts" / "component_lint.py", ROOT])
    run([sys.executable, ROOT / "scripts" / "render_markdown.py", SAMPLE, html])
    run([sys.executable, ROOT / "scripts" / "validate_gzh_html.py", html])
    run([sys.executable, ROOT / "scripts" / "wrap_preview.py", html, preview])
    run([sys.executable, ROOT / "scripts" / "render_markdown.py", STRESS, stress_html])
    run([sys.executable, ROOT / "scripts" / "validate_gzh_html.py", stress_html])
    run([sys.executable, ROOT / "scripts" / "wrap_preview.py", stress_html, stress_preview])
    run_expect_failure(
        [sys.executable, ROOT / "scripts" / "render_markdown.py", STRESS, "--target", "pudding"],
        "unrecognized arguments: --target",
    )

    assert_contains(html, "font-size:54px")
    assert_contains(html, "text-align:left")
    assert_contains(html, "<span leaf=\"\">01</span>")
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
        'text-align:justify;color:#4d4f46;padding:0 4px;">'
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
    assert_not_contains(stress_html, "<script")
    assert_not_contains(stress_html, "gzhCopyBtn")
    assert_contains(stress_preview, 'id="gzhCopyBtn"')
    assert_contains(stress_preview, stress_html.read_text(encoding="utf-8"))

    print(f"regression ok: {html}")
    print(f"preview: {preview}")
    print(f"stress regression ok: {stress_html}")
    print(f"stress preview: {stress_preview}")


if __name__ == "__main__":
    main()
