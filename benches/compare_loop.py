"""Compara el TP con plox usando el mismo programa Lox.

La medición es end-to-end: incluye inicio de Python, scanner, parser,
resolver y ejecución. Ejecutar desde cualquier directorio con:

    .venv/bin/python benches/compare_loop.py 7
"""

from __future__ import annotations

import statistics
import subprocess
import sys
import time
from pathlib import Path


TP_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_DIR = TP_DIR.parent
PROGRAM = TP_DIR / "benches" / "programs" / "large_loop.lox"

IMPLEMENTATIONS: dict[str, list[str]] = {
    "TP (Bytecode VM)": [str(TP_DIR / ".venv" / "bin" / "pylox"), "--vm"],
    "TP (Tree-Walk)": [str(TP_DIR / ".venv" / "bin" / "pylox"), "--tree-walk"],
    "Cátedra (ploxb)": [str(Path.home() / ".local" / "bin" / "ploxb")],
    "Cátedra (plox)": [str(WORKSPACE_DIR / "Practica" / "plox" / ".venv" / "bin" / "plox")],
}

EXPECTED_RESULT = 1_499_994.0


def run_once(cmd_prefix: list[str]) -> float:
    start = time.perf_counter()
    result = subprocess.run(
        [*cmd_prefix, str(PROGRAM)],
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed = time.perf_counter() - start

    if result.returncode != 0:
        raise RuntimeError(
            f"{cmd_prefix[0]} terminó con código {result.returncode}:\n{result.stderr}"
        )

    output = result.stdout.strip()
    try:
        numeric_output = float(output)
    except ValueError as error:
        raise RuntimeError(f"{cmd_prefix[0]} produjo una salida no numérica: {output!r}.") from error

    if numeric_output != EXPECTED_RESULT:
        raise RuntimeError(
            f"{cmd_prefix[0]} produjo {output!r}; se esperaba {EXPECTED_RESULT:g}."
        )

    return elapsed


def main(runs: int = 7) -> None:
    if runs < 1:
        raise ValueError("La cantidad de repeticiones debe ser positiva.")

    active_impls: dict[str, list[str]] = {}
    for name, cmd_prefix in IMPLEMENTATIONS.items():
        if Path(cmd_prefix[0]).exists():
            active_impls[name] = cmd_prefix

    print(f"Programa: {PROGRAM.name} (500.000 iteraciones)")
    print(f"Repeticiones medidas: {runs} + 1 calentamiento por implementación\n")

    results: dict[str, list[float]] = {}
    for name, cmd_prefix in active_impls.items():
        run_once(cmd_prefix)  # Calentamiento fuera de la medición.
        times = [run_once(cmd_prefix) for _ in range(runs)]
        results[name] = times

        print(
            f"{name:<18} "
            f"mediana={statistics.median(times):.4f}s  "
            f"promedio={statistics.mean(times):.4f}s  "
            f"mínimo={min(times):.4f}s  "
            f"máximo={max(times):.4f}s"
        )

    vm_median = statistics.median(results["TP (Bytecode VM)"])
    print()
    for name, times in results.items():
        if name == "TP (Bytecode VM)":
            continue
        med = statistics.median(times)
        ratio = med / vm_median
        print(f"TP (Bytecode VM) fue {ratio:.2f}x más rápido que {name} según la mediana.")


if __name__ == "__main__":
    repetitions = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    main(repetitions)
