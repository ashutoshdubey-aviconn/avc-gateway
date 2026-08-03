#!/usr/bin/env python3
"""Add module-level docstrings to Python files in the workspace.

This script finds all `.py` files under the repository (skips `venv`, `.git`,
`__pycache__`), and for files that do not already have a module docstring,
it generates a concise docstring describing:
  - module path
  - a short description derived from leading comments or filename
  - top-level functions and classes (names and their short docstrings if any)

The script is careful to preserve encoding and shebang lines.

Usage:
  python scripts/add_module_docstrings.py

Review changes (git diff) before committing.
"""

from __future__ import annotations

import ast
import os
import re
from pathlib import Path
from typing import List

EXCLUDE_DIRS = {"venv", ".venv", ".git", "__pycache__"}


def find_py_files(root: Path) -> List[Path]:
    out = []
    for p in root.rglob("*.py"):
        # skip files under excluded dirs
        if any(seg in EXCLUDE_DIRS for seg in p.parts):
            continue
        out.append(p)
    return out


def read_leading_comments(text: str) -> str:
    """Return leading block comments (lines starting with #) at the top of file."""
    lines = text.splitlines()
    collected = []
    for ln in lines[:40]:
        s = ln.strip()
        if s.startswith("#"):
            collected.append(s.lstrip("# "))
        elif s == "":
            # allow a couple blank lines in the header
            if collected:
                break
            continue
        else:
            break
    return " ".join(collected).strip()


def generate_docstring(path: Path, source: str) -> str:
    module = ".".join(path.with_suffix("").parts)
    header = read_leading_comments(source)

    try:
        tree = ast.parse(source)
    except Exception:
        # fallback: simple doc mentioning file and header
        lines = [f"Module {path}"]
        if header:
            lines.append(header)
        return "\n".join(lines)

    funcs = []
    classes = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            name = node.name
            doc = ast.get_docstring(node) or ""
            funcs.append((name, doc.splitlines()[0] if doc else ""))
        elif isinstance(node, ast.ClassDef):
            name = node.name
            doc = ast.get_docstring(node) or ""
            classes.append((name, doc.splitlines()[0] if doc else ""))

    desc = header or f"Module {module}"
    parts = [desc, "", "Flow:"]
    if funcs:
        parts.append("Top-level functions:")
        for n, d in funcs[:10]:
            parts.append(f"- {n}: {d}" if d else f"- {n}")
    if classes:
        parts.append("Top-level classes:")
        for n, d in classes[:10]:
            parts.append(f"- {n}: {d}" if d else f"- {n}")

    return "\n".join(parts)


def has_module_docstring(source: str) -> bool:
    try:
        tree = ast.parse(source)
        return ast.get_docstring(tree) is not None
    except Exception:
        return False


def insert_docstring(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if has_module_docstring(text):
        return False

    # preserve shebang and encoding declarations
    lines = text.splitlines()
    prefix = []
    i = 0
    if lines and lines[0].startswith("#!"):
        prefix.append(lines[0])
        i = 1
    # keep initial encoding or future imports if present immediately after shebang
    while i < len(lines) and re.match(r"^#.*coding[:=]", lines[i]):
        prefix.append(lines[i])
        i += 1

    rest = "\n".join(lines[i:])
    doc = generate_docstring(path.relative_to(Path.cwd()), rest)
    # format as triple-quoted string
    doc_block = '"""' + "\n" + doc.strip() + "\n" + '"""' + "\n\n"

    new_text = "\n".join(prefix) + ("\n" if prefix else "") + doc_block + rest
    path.write_text(new_text, encoding="utf-8")
    return True


def main():
    root = Path.cwd()
    pyfiles = find_py_files(root)
    changed = []
    for p in pyfiles:
        try:
            if insert_docstring(p):
                changed.append(str(p))
        except Exception as e:
            print(f"Error processing {p}: {e}")

    print(f"Processed {len(pyfiles)} files, updated {len(changed)} files")
    for c in changed:
        print("Updated:", c)


if __name__ == "__main__":
    main()
