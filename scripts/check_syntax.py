#!/usr/bin/env python3
"""Valida la sintaxis Python del proyecto sin importar ni arrancar la aplicación."""

from __future__ import annotations

import ast
import sys
from pathlib import Path


def main() -> int:
    project_dir = Path(__file__).resolve().parents[1]
    source_dir = project_dir / "src" / "betplaycito"
    failures: list[str] = []
    for path in sorted(source_dir.rglob("*.py")):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError, UnicodeError) as exc:
            failures.append(f"{path.relative_to(project_dir)}: {exc}")
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print("Sintaxis Python válida.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
