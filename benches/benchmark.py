import statistics
import subprocess
import sys
import time
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parent
PROGRAMS_DIR = BENCH_DIR / "programs"

BENCHMARKS = [
    ("fibonacci.lox", "Cálculo recursivo fib(25)"),
    ("loop.lox", "Bucle de 50.000 iteraciones con mutación de estado"),
    ("minsky.lox", "Simulación Minsky Machine con 1.500 evaluaciones"),
]


def run_single_benchmark(path: Path) -> float:
    start = time.perf_counter()
    result = subprocess.run(
        [sys.executable, "-m", "lox.cli", str(path)],
        cwd=BENCH_DIR.parent,
        capture_output=True,
        text=True,
    )
    elapsed = time.perf_counter() - start

    if result.returncode != 0:
        print(f"Error ejecutando {path.name}:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)

    return elapsed


def main(iterations: int = 5) -> None:
    print(f"============================================================")
    print(f" Lox Tree-Walk Interpreter Benchmarks ({iterations} iteraciones por test)")
    print(f"============================================================\n")

    results_table = []

    for filename, description in BENCHMARKS:
        path = PROGRAMS_DIR / filename
        times = []
        print(f"Ejecutando {filename} ({description})...", end="", flush=True)

        for _ in range(iterations):
            t = run_single_benchmark(path)
            times.append(t)
            print(".", end="", flush=True)

        avg = statistics.mean(times)
        std = statistics.stdev(times) if len(times) > 1 else 0.0
        fastest = min(times)
        slowest = max(times)
        print(f" Promedio: {avg:.4f}s (±{std:.4f}s)")

        results_table.append({
            "name": filename,
            "desc": description,
            "avg": avg,
            "std": std,
            "min": fastest,
            "max": slowest,
        })

    print("\nResumen de Métricas:")
    print("-" * 75)
    print(f"{'Benchmark':<18} | {'Promedio (s)':<14} | {'Mínimo (s)':<12} | {'Máximo (s)':<12}")
    print("-" * 75)
    for r in results_table:
        print(f"{r['name']:<18} | {r['avg']:<14.4f} | {r['min']:<12.4f} | {r['max']:<12.4f}")
    print("-" * 75)


if __name__ == "__main__":
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    main(runs)
