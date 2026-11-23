#!/usr/bin/env python3
"""Roda ruff e pytest sobre uma branch SEM mexer no checkout atual (uso do revisor-codigo).

Cria um git worktree temporário e destacado (--detach) da branch, roda as ferramentas da squad
com a .venv do projeto e remove o worktree no final. É o caminho sancionado para o subagente
revisor-codigo, que roda em permissionMode dontAsk e não pode usar "git worktree" direto.

Uso: python3 scripts/checar_branch.py <branch>
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

PROJETO = Path(__file__).resolve().parents[1]
REPO = Path(subprocess.check_output(
    ["git", "-C", str(PROJETO), "rev-parse", "--show-toplevel"], text=True).strip())
VENV = PROJETO / ".venv/bin"
NOME_VALIDO = re.compile(r"^[A-Za-z0-9._/-]+$")


def rodar(cmd: list[str], cwd: Path) -> None:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    exibido = " ".join(Path(c).name if i == 0 else c for i, c in enumerate(cmd))
    print(f"$ {exibido}  (exit {proc.returncode})")
    print((proc.stdout + proc.stderr).strip()[-4000:] or "(sem saída)")
    print()


def main() -> None:
    if len(sys.argv) != 2 or not NOME_VALIDO.match(sys.argv[1]) or sys.argv[1].startswith("-"):
        raise SystemExit("uso: checar_branch.py <branch>")
    branch = sys.argv[1]
    with tempfile.TemporaryDirectory(prefix="checar-branch-") as tmp:
        destino = Path(tmp) / "wt"
        subprocess.run(["git", "-C", str(REPO), "worktree", "add", "--detach", "-q",
                        str(destino), branch], check=True)
        try:
            alvo = destino / PROJETO.relative_to(REPO)
            sha = subprocess.check_output(["git", "-C", str(destino), "rev-parse", "--short",
                                           "HEAD"], text=True).strip()
            print(f"Branch {branch} @ {sha} (worktree temporário)\n")
            rodar([str(VENV / "ruff"), "check", "agendamento", "tests"], alvo)
            rodar([str(VENV / "pytest"), "-q", "-p", "no:cacheprovider"], alvo)
        finally:
            subprocess.run(["git", "-C", str(REPO), "worktree", "remove", "--force",
                            str(destino)], check=False)


if __name__ == "__main__":
    main()
