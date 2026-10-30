#!/usr/bin/env python3
"""Validate the public SCS-FKB tree before release."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "README.md",
    "README.zh-CN.md",
    "PROJECT.md",
    "LICENSE",
    "LICENSE-docs",
    "NOTICE",
    "CITATION.cff",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    ".gitignore",
    ".gitattributes",
    ".editorconfig",
    ".pre-commit-config.yaml",
    ".env.example",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "Makefile",
    ".github/workflows/ci.yml",
    ".github/dependabot.yml",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
    ".github/ISSUE_TEMPLATE/data_source.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    "configs/corpus.yaml",
    "configs/schema.yaml",
    "data/README.md",
    "docs/index.md",
    "docs/corpus.md",
    "docs/questions.md",
    "docs/method.md",
    "docs/data-policy.md",
    "docs/roadmap.md",
    "scripts/check_public_tree.py",
    "tests/test_configs.py",
    "tests/test_public_tree.py",
]

TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".cff",
    ".py",
    ".sh",
    ".cfg",
    ".ini",
}
TEXT_NAMES = {
    "LICENSE",
    "LICENSE-docs",
    "NOTICE",
    "Makefile",
    ".gitignore",
    ".gitattributes",
    ".editorconfig",
    ".env.example",
}
SKIP_PARTS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "data",
    "runs",
}
ABSOLUTE_PATTERNS = [
    "/" + "Users" + "/",
    "/" + "home" + "/",
]
SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9]{20,}",
    r"ghp_[A-Za-z0-9]{20,}",
    r"github_pat_[A-Za-z0-9_]{20,}",
    r"BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY",
]
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
FENCE_RE = re.compile(r"```.*?```", re.DOTALL)


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z"],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return [
            path.relative_to(ROOT)
            for path in ROOT.rglob("*")
            if path.is_file() and not any(part in SKIP_PARTS for part in path.parts)
        ]
    return [Path(item.decode("utf-8")) for item in result.stdout.split(b"\0") if item]


def is_text(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES or path.name in TEXT_NAMES


def check_required(errors: list[str]) -> None:
    for name in REQUIRED:
        if not (ROOT / name).is_file():
            errors.append(f"missing required file: {name}")


def check_tracked(files: list[Path], errors: list[str]) -> None:
    for path in files:
        name = path.as_posix()
        if name.startswith("runs/"):
            errors.append(f"tracked run artifact: {name}")
        if name == ".env" or name.endswith((".db", ".db-wal", ".db-shm", ".sqlite", ".sqlite3")):
            errors.append(f"tracked secret or database: {name}")
        if name.startswith("data/") and name != "data/README.md":
            errors.append(f"tracked data payload: {name}")


def check_content(files: list[Path], errors: list[str]) -> None:
    for path in files:
        if not is_text(path) or any(part in SKIP_PARTS for part in path.parts):
            continue
        try:
            text = (ROOT / path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for pattern in ABSOLUTE_PATTERNS:
            if pattern in text:
                errors.append(f"absolute path pattern {pattern!r} in {path}")
        for pattern in SECRET_PATTERNS:
            if re.search(pattern, text):
                errors.append(f"secret pattern in {path}")


def check_yaml(errors: list[str]) -> None:
    candidates = [
        ROOT / "configs/corpus.yaml",
        ROOT / "configs/schema.yaml",
        ROOT / "CITATION.cff",
        ROOT / ".pre-commit-config.yaml",
        ROOT / ".github/workflows/ci.yml",
        ROOT / ".github/dependabot.yml",
        *sorted((ROOT / ".github/ISSUE_TEMPLATE").glob("*.yml")),
    ]
    for path in candidates:
        if not path.is_file():
            continue
        try:
            yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            errors.append(f"invalid YAML in {path.relative_to(ROOT)}: {exc}")


def check_links(files: list[Path], errors: list[str]) -> None:
    for path in files:
        if path.suffix.lower() != ".md" or any(part in SKIP_PARTS for part in path.parts):
            continue
        text = (ROOT / path).read_text(encoding="utf-8")
        text = FENCE_RE.sub("", text)
        for target in LINK_RE.findall(text):
            target = target.strip().split("#", 1)[0].split("?", 1)[0]
            if not target or target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            if target.startswith("/"):
                errors.append(f"absolute link {target!r} in {path}")
                continue
            resolved = (ROOT / path.parent / target).resolve()
            if not resolved.is_file():
                errors.append(f"broken link {target!r} in {path}")


def main() -> int:
    errors: list[str] = []
    files = tracked_files()
    check_required(errors)
    check_tracked(files, errors)
    check_content(files, errors)
    check_yaml(errors)
    check_links(files, errors)
    if errors:
        print("PUBLIC TREE CHECK FAILED")
        for error in sorted(set(errors)):
            print("-", error)
        return 1
    print(f"PUBLIC TREE CHECK OK ({len(files)} tracked files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
