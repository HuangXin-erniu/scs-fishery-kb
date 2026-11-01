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
    "PROJECT.zh-CN.md",
    "GOVERNANCE.md",
    "LICENSE",
    "LICENSE-docs",
    "NOTICE",
    "CITATION.cff",
    ".github/CONTRIBUTING.md",
    ".github/CODE_OF_CONDUCT.md",
    ".github/SECURITY.md",
    ".github/SUPPORT.md",
    ".github/CODEOWNERS",
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
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    "configs/corpus.yaml",
    "configs/schema.yaml",
    "configs/statistics.yaml",
    "configs/sc-standards.yaml",
    "configs/pipeline.yaml",
    "configs/eval.yaml",
    "configs/cwp-handbook.yaml",
    "configs/glossary-bridge.yaml",
    "docs/index.md",
    "docs/architecture.md",
    "docs/plan.md",
    "docs/evaluation.md",
    "docs/project-log.md",
    "docs/corpus.md",
    "docs/questions.md",
    "docs/data-policy.md",
    "docs/glossary.md",
    "docs/style-guide.md",
    "docs/adr/README.md",
    "docs/adr/0001-no-versioned-releases.md",
    "docs/adr/0002-bilingual-documentation.md",
    "docs/adr/0003-data-outside-repository.md",
    "docs/adr/0004-public-private-boundary.md",
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
    "C:" + "\\" + "Users" + "\\",
    "/" + "Volumes" + "/",
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


CACHE_PARTS = {".pytest_cache", ".ruff_cache", "__pycache__", ".venv", "venv"}
BINARY_SUFFIXES = {
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".zip",
    ".7z",
    ".tar",
    ".gz",
    ".bz2",
    ".xz",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
}
MAX_TRACKED_BYTES = 256 * 1024


def check_tracked(files: list[Path], errors: list[str]) -> None:
    for path in files:
        name = path.as_posix()
        if name.startswith(("data/", "runs/")):
            errors.append(f"tracked data or run artifact: {name}")
        if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
            errors.append(f"tracked secret file: {name}")
        if name.endswith((".db", ".db-wal", ".db-shm", ".sqlite", ".sqlite3")):
            errors.append(f"tracked database: {name}")
        if any(part in CACHE_PARTS for part in path.parts):
            errors.append(f"tracked cache or environment: {name}")
        if path.suffix.lower() in BINARY_SUFFIXES:
            errors.append(f"tracked binary file: {name}")
        try:
            size = (ROOT / path).stat().st_size
        except OSError:
            continue
        if size > MAX_TRACKED_BYTES:
            errors.append(f"tracked file exceeds 256 KiB: {name}")


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
        ROOT / "configs/statistics.yaml",
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


def check_no_tags(errors: list[str]) -> None:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "tag", "--list"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return
    tags = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if tags:
        errors.append("repository has tags but versioning is disabled: " + ", ".join(tags))


def main() -> int:
    errors: list[str] = []
    files = tracked_files()
    check_required(errors)
    check_tracked(files, errors)
    check_content(files, errors)
    check_yaml(errors)
    check_no_tags(errors)
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
