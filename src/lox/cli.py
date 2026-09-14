import sys
from pathlib import Path
from lox.errors import DiagnosticReporter, LoxError, LoxRuntimeError


class LoxCLI:
    def __init__(self):
        self.diagnostics = DiagnosticReporter()

    def run_file(self, path: str) -> None:
        file_path = Path(path)
        if not file_path.exists():
            print(f"Error: No se pudo abrir el archivo '{path}'", file=sys.stderr)
            sys.exit(66)

        source = file_path.read_text(encoding="utf-8")
        self.run(source)

        if self.diagnostics.had_error:
            sys.exit(65)
        if self.diagnostics.had_runtime_error:
            sys.exit(70)

    def run_prompt(self) -> None:
        print("Lox Tree-Walk Interpreter (REPL)")
        print("Escribe 'exit' o presiona Ctrl+D para salir.\n")

        while True:
            try:
                line = input("lox> ")
                if line.strip() == "exit":
                    break
                if not line.strip():
                    continue
                self.run(line)
                # En modo interactivo reseteamos el estado de error por línea
                self.diagnostics.had_error = False
            except (EOFError, KeyboardInterrupt):
                print("\nHasta luego!")
                break

    def run(self, source: str) -> None:
        # En las próximas fases conectaremos Scanner -> Parser -> Resolver -> Interpreter
        # Por ahora verificamos que el flujo y CLI respondan adecuadamente
        pass


def main() -> None:
    cli = LoxCLI()
    args = sys.argv[1:]

    if len(args) > 1:
        print("Uso: pylox [script.lox]", file=sys.stderr)
        sys.exit(64)
    elif len(args) == 1:
        cli.run_file(args[0])
    else:
        cli.run_prompt()


if __name__ == "__main__":
    main()
