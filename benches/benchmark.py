"""Suite de Benchmarks para la Entrega Final de Lox (LyC - FIUBA).

Compara:
1. TP (Bytecode VM)      — Entrega Final
2. TP (Tree-Walk)        — Entrega Parcial
3. Cátedra (ploxb)       — Compilador Bytecode de la cátedra
4. Cátedra (plox)        — Intérprete Tree-Walk de la cátedra
5. Python 3.12 (nativo)  — Lenguaje de referencia

Genera tablas en Markdown por consola y exporta un gráfico comparativo en
`benches/benchmark_results.svg`.

Ejecutar con:
    uv run python benches/benchmark.py [repeticiones]
"""

from __future__ import annotations

import shutil
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

TP_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_DIR = TP_DIR.parent
PROGRAMS_DIR = TP_DIR / "benches" / "programs"
SVG_OUTPUT = TP_DIR / "benches" / "benchmark_results.svg"


@dataclass
class EngineSpec:
    name: str
    command: list[str]
    color: str
    supports_functions: bool = True
    supports_oop: bool = True


@dataclass
class BenchmarkCase:
    title: str
    lox_file: Path
    python_code: str
    expected_result: float
    requires_functions: bool = False
    requires_oop: bool = False


def discover_engines() -> list[EngineSpec]:
    pylox_bin = TP_DIR / ".venv" / "bin" / "pylox"
    python_bin = Path(sys.executable)

    engines: list[EngineSpec] = [
        EngineSpec(
            name="TP (Bytecode VM)",
            command=[str(pylox_bin), "--vm"],
            color="#2563eb",
            supports_functions=True,
            supports_oop=True,
        ),
        EngineSpec(
            name="TP (Tree-Walk)",
            command=[str(pylox_bin), "--tree-walk"],
            color="#0ea5e9",
            supports_functions=True,
            supports_oop=True,
        ),
    ]

    ploxb_bin = shutil.which("ploxb")
    if ploxb_bin:
        engines.append(
            EngineSpec(
                name="Cátedra (ploxb)",
                command=[ploxb_bin],
                color="#f59e0b",
                supports_functions=False,
                supports_oop=False,
            )
        )

    plox_bin = WORKSPACE_DIR / "Practica" / "plox" / ".venv" / "bin" / "plox"
    if plox_bin.exists():
        engines.append(
            EngineSpec(
                name="Cátedra (plox)",
                command=[str(plox_bin)],
                color="#ef4444",
                supports_functions=True,
                supports_oop=False,
            )
        )

    engines.append(
        EngineSpec(
            name="Python 3.12 (nativo)",
            command=[str(python_bin), "-c"],
            color="#10b981",
            supports_functions=True,
            supports_oop=True,
        )
    )
    return engines


BENCHMARKS: list[BenchmarkCase] = [
    BenchmarkCase(
        title="large_loop.lox (500.000 iteraciones aritméticas)",
        lox_file=PROGRAMS_DIR / "large_loop.lox",
        python_code=(
            "s = 0\n"
            "for i in range(500000):\n"
            "    s = s + (i % 7)\n"
            "print(s)"
        ),
        expected_result=1_499_994.0,
        requires_functions=False,
        requires_oop=False,
    ),
    BenchmarkCase(
        title="fib_recursive.lox (Fibonacci recursivo n=26)",
        lox_file=PROGRAMS_DIR / "fib_recursive.lox",
        python_code=(
            "def fib(n):\n"
            "    if n < 2: return n\n"
            "    return fib(n - 1) + fib(n - 2)\n"
            "print(fib(26))"
        ),
        expected_result=121_393.0,
        requires_functions=True,
        requires_oop=False,
    ),
    BenchmarkCase(
        title="oop_simulation.lox (100.000 llamadas con herencia y super)",
        lox_file=PROGRAMS_DIR / "oop_simulation.lox",
        python_code=(
            "class Entidad:\n"
            "    def __init__(self, base): self.energia = base\n"
            "    def actualizar(self, paso):\n"
            "        self.energia = self.energia + paso\n"
            "        return self.energia\n"
            "class Unidad(Entidad):\n"
            "    def __init__(self, base, factor):\n"
            "        super().__init__(base)\n"
            "        self.factor = factor\n"
            "    def actualizar(self, paso):\n"
            "        return super().actualizar(paso * self.factor)\n"
            "u = Unidad(0, 2)\n"
            "total = 0\n"
            "for i in range(100000):\n"
            "    total = total + u.actualizar(1)\n"
            "print(total)"
        ),
        expected_result=10_000_100_000.0,
        requires_functions=True,
        requires_oop=True,
    ),
]


def run_once(engine: EngineSpec, bench: BenchmarkCase) -> float:
    if engine.name.startswith("Python"):
        cmd = [*engine.command, bench.python_code]
    else:
        cmd = [*engine.command, str(bench.lox_file)]

    start = time.perf_counter()
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    elapsed = time.perf_counter() - start

    if result.returncode != 0:
        raise RuntimeError(
            f"{engine.name} falló ({result.returncode}): {result.stderr}"
        )

    lines = [line.strip() for line in result.stdout.strip().splitlines() if line.strip()]
    numeric_output = float(lines[-1])
    if numeric_output != bench.expected_result:
        raise RuntimeError(
            f"{engine.name} produjo {numeric_output}; se esperaba {bench.expected_result}"
        )
    return elapsed


def generate_svg_chart(
    all_medians: dict[str, dict[str, float]],
    engines: list[EngineSpec],
    output_path: Path,
) -> None:
    width = 860
    panel_height = 210
    header_height = 75
    footer_height = 35
    total_height = header_height + panel_height * len(all_medians) + footer_height

    svg: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {total_height}" width="{width}" height="{total_height}">',
        "<style>",
        '  text { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }',
        "  .title { font-size: 18px; font-weight: 700; fill: #0f172a; }",
        "  .subtitle { font-size: 12px; fill: #475569; }",
        "  .bench-title { font-size: 14px; font-weight: 600; fill: #1e293b; }",
        "  .label { font-size: 12px; fill: #334155; }",
        "  .val { font-size: 12px; font-weight: 600; fill: #0f172a; }",
        "</style>",
        f'<rect width="{width}" height="{total_height}" rx="10" fill="#f8fafc" stroke="#cbd5e1"/>',
        '<text x="30" y="34" class="title">Benchmarks Comparativos — Lox Bytecode VM vs. Tree-Walk vs. Cátedra vs. Python</text>',
        '<text x="30" y="54" class="subtitle">Mediana de tiempos de ejecución end-to-end en segundos (menor es mejor)</text>',
    ]

    color_map = {e.name: e.color for e in engines}
    y_cursor = header_height

    for bench_title, medians in all_medians.items():
        svg.append(
            f'<rect x="24" y="{y_cursor}" width="{width - 48}" height="{panel_height - 14}" rx="8" fill="#ffffff" stroke="#e2e8f0"/>'
        )
        svg.append(
            f'<text x="40" y="{y_cursor + 26}" class="bench-title">{bench_title}</text>'
        )

        max_val = max(medians.values()) if medians else 1.0
        bar_max_width = 500
        row_y = y_cursor + 46
        row_step = 28

        for eng_name, med in medians.items():
            bar_w = max(4.0, (med / max_val) * bar_max_width)
            color = color_map.get(eng_name, "#64748b")
            svg.append(
                f'<text x="40" y="{row_y + 14}" class="label">{eng_name}</text>'
            )
            svg.append(
                f'<rect x="215" y="{row_y}" width="{bar_w:.1f}" height="18" rx="4" fill="{color}"/>'
            )
            svg.append(
                f'<text x="{223 + bar_w:.1f}" y="{row_y + 14}" class="val">{med:.4f} s</text>'
            )
            row_y += row_step

        y_cursor += panel_height

    svg.append("</svg>")
    output_path.write_text("\n".join(svg), encoding="utf-8")


def main(runs: int = 5) -> None:
    engines = discover_engines()
    all_medians: dict[str, dict[str, float]] = {}

    print(f"=== Suite de Benchmarks Lox ({runs} corridas + 1 warmup) ===\n")

    for bench in BENCHMARKS:
        print(f"### {bench.title}")
        print("| Implementación | Mediana (s) | Promedio (s) | Mínimo (s) | Speedup vs. TP VM |")
        print("|---|---:|---:|---:|---:|")

        bench_medians: dict[str, float] = {}
        bench_stats: list[tuple[str, float, float, float]] = []

        for engine in engines:
            if bench.requires_functions and not engine.supports_functions:
                continue
            if bench.requires_oop and not engine.supports_oop:
                continue

            run_once(engine, bench)  # Warmup
            times = [run_once(engine, bench) for _ in range(runs)]
            med = statistics.median(times)
            avg = statistics.mean(times)
            mn = min(times)
            bench_medians[engine.name] = med
            bench_stats.append((engine.name, med, avg, mn))

        vm_med = bench_medians.get("TP (Bytecode VM)", 1.0)
        for name, med, avg, mn in bench_stats:
            ratio = med / vm_med if vm_med > 0 else 1.0
            speedup_str = "1.00x (base)" if name == "TP (Bytecode VM)" else f"{ratio:.2f}x"
            print(f"| {name} | {med:.4f} | {avg:.4f} | {mn:.4f} | {speedup_str} |")
        print()
        all_medians[bench.title] = bench_medians

    generate_svg_chart(all_medians, engines, SVG_OUTPUT)
    print(f"Gráfico SVG generado en: {SVG_OUTPUT}")


if __name__ == "__main__":
    repetitions = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    main(repetitions)

