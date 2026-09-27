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

IMPLEMENTATIONS = {
    "TP": TP_DIR / ".venv" / "bin" / "pylox",
    "Cátedra": WORKSPACE_DIR / "Practica" / "plox" / ".venv" / "bin" / "plox",
}

EXPECTED_RESULT = 1_499_994.0


def run_once(executable: Path) -> float:
    start = time.perf_counter()
    result = subprocess.run(
        [str(executable), str(PROGRAM)],
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed = time.perf_counter() - start

    if result.returncode != 0:
        raise RuntimeError(
            f"{executable} terminó con código {result.returncode}:\n{result.stderr}"
        )

    output = result.stdout.strip()
    try:
        numeric_output = float(output)
    except ValueError as error:
        raise RuntimeError(f"{executable} produjo una salida no numérica: {output!r}.") from error

    if numeric_output != EXPECTED_RESULT:
        raise RuntimeError(
            f"{executable} produjo {output!r}; se esperaba {EXPECTED_RESULT:g}."
        )

    return elapsed


def main(runs: int = 7) -> None:
    if runs < 1:
        raise ValueError("La cantidad de repeticiones debe ser positiva.")

    for name, executable in IMPLEMENTATIONS.items():
        if not executable.exists():
            raise FileNotFoundError(f"No se encontró el ejecutable de {name}: {executable}")

    print(f"Programa: {PROGRAM.name} (500.000 iteraciones)")
    print(f"Repeticiones medidas: {runs} + 1 calentamiento por implementación\n")

    results: dict[str, list[float]] = {}
    for name, executable in IMPLEMENTATIONS.items():
        run_once(executable)  # Calentamiento fuera de la medición.
        times = [run_once(executable) for _ in range(runs)]
        results[name] = times

        print(
            f"{name:<8} "
            f"mediana={statistics.median(times):.4f}s  "
            f"promedio={statistics.mean(times):.4f}s  "
            f"mínimo={min(times):.4f}s  "
            f"máximo={max(times):.4f}s"
        )

    tp_median = statistics.median(results["TP"])
    reference_median = statistics.median(results["Cátedra"])
    ratio = tp_median / reference_median

    print()
    if ratio < 1:
        print(f"El TP fue {1 / ratio:.2f}x más rápido según la mediana.")
    else:
        print(f"La cátedra fue {ratio:.2f}x más rápida según la mediana.")


if __name__ == "__main__":
    repetitions = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    main(repetitions)
