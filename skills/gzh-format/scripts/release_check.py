#!/usr/bin/env python3
"""Run offline release checks for the standalone gzh-format skill."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
IS_STANDALONE_REPOSITORY = (REPO_ROOT / "THIRD_PARTY_NOTICES.md").is_file()
SCAN_ROOT = REPO_ROOT if IS_STANDALONE_REPOSITORY else ROOT
REQUIRED = (
    "SKILL.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "skill.contract.yaml",
    "agents/openai.yaml",
    "assets/preview-template.html",
    "assets/sample-article.md",
    "references/theme-index.md",
    "themes/_shared/common-components.md",
    "themes/minimal/components.md",
    "themes/red/components.md",
    "themes/green/components.md",
    "scripts/component_lint.py",
    "scripts/render_markdown.py",
    "scripts/validate_gzh_html.py",
    "scripts/wrap_preview.py",
    "scripts/regression.py",
    "scripts/release_check.py",
    "tests/fixtures/stress-markdown.md",
    "tests/evaluation/held-out-mixed.md",
    "tests/evaluation/2026-07-11-install-and-render-results.md",
)
REPOSITORY_REQUIRED = (
    "README.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "CHANGELOG.md",
    ".github/workflows/release-check.yml",
)
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
SKIP_LINK_PREFIXES = ("http://", "https://", "mailto:", "#", "data:")
SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "secret assignment": re.compile(
        r"(?i)\b(?:app_secret|api_key|access_token|password)\s*[:=]\s*"
        r"[\"']?(?!<|\{|\$)[A-Za-z0-9_./+\-=]{16,}"
    ),
}


def text_files() -> list[Path]:
    result: list[Path] = []
    for path in SCAN_ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
            continue
        try:
            path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        result.append(path)
    return result


def check_required(problems: list[str]) -> None:
    for relative in REQUIRED:
        if not (ROOT / relative).is_file():
            problems.append(f"missing required file: {relative}")
    # The canonical Content-factory source also lives at skills/gzh-format.
    # Only apply standalone repository checks when the public distribution
    # marker exists at the repository root.
    if IS_STANDALONE_REPOSITORY:
        for relative in REPOSITORY_REQUIRED:
            if not (REPO_ROOT / relative).is_file():
                problems.append(f"missing repository file: {relative}")
        if (REPO_ROOT / "SKILL.md").exists():
            problems.append(
                "repository root must not contain SKILL.md; use skills/gzh-format/SKILL.md"
            )


def check_frontmatter(problems: list[str]) -> None:
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, flags=re.S)
    if not match:
        problems.append("SKILL.md frontmatter is missing or malformed")
        return
    frontmatter = match.group(1)
    for key in ("name", "description", "license"):
        if not re.search(rf"(?m)^{re.escape(key)}:\s*\S", frontmatter):
            problems.append(f"SKILL.md frontmatter missing {key}")
    if not re.search(r"(?m)^\s+compatibility:\s*\S", frontmatter):
        problems.append("SKILL.md metadata missing compatibility")


def check_links(files: list[Path], problems: list[str]) -> None:
    for markdown in (path for path in files if path.suffix.lower() == ".md"):
        text = markdown.read_text(encoding="utf-8")
        text = re.sub(r"```.*?```", "", text, flags=re.S)
        text = re.sub(r"`[^`]*`", "", text)
        for raw_target in LINK_RE.findall(text):
            target = raw_target.strip().split()[0].strip("<>")
            if target.startswith(SKIP_LINK_PREFIXES):
                continue
            target = target.split("#", 1)[0]
            if target and not (markdown.parent / target).resolve().exists():
                problems.append(
                    f"broken link: {markdown.relative_to(SCAN_ROOT)} -> {raw_target}"
                )


def check_security(files: list[Path], problems: list[str]) -> None:
    for path in files:
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(SCAN_ROOT)
        mac_user_root = "/" + "Users" + "/"
        windows_user_root = "C:\\" + "Users" + "\\"
        if mac_user_root in text or windows_user_root in text:
            problems.append(f"absolute user path: {relative}")
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                problems.append(f"secret-like {label}: {relative}")
    for path in ROOT.rglob("*"):
        if path.is_symlink():
            problems.append(f"symlink is not allowed in release bundle: {path.relative_to(ROOT)}")


def check_python_syntax(problems: list[str]) -> None:
    for path in sorted((ROOT / "scripts").glob("*.py")):
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except SyntaxError as exc:
            problems.append(f"python syntax error: {path.relative_to(ROOT)}:{exc.lineno}: {exc.msg}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--static-only",
        action="store_true",
        help="skip the functional regression subprocess",
    )
    args = parser.parse_args()

    problems: list[str] = []
    files = text_files()
    check_required(problems)
    check_frontmatter(problems)
    check_links(files, problems)
    check_security(files, problems)
    check_python_syntax(problems)

    if problems:
        print(f"release check failed: {len(problems)} problem(s)")
        for problem in problems:
            print(f"- {problem}")
        return 1

    print(f"static release check ok: {len(files)} UTF-8 text files")
    if not args.static_only:
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "regression.py")],
            cwd=ROOT,
            check=True,
        )
        print("functional release check ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
