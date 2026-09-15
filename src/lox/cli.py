import sys
from pathlib import Path
from lox.errors import DiagnosticReporter, LoxError, LoxRuntimeError
from lox.syntax import Scanner


class LoxCLI:
    def __init__(self, scanner_mode: bool = False):
        self.diagnostics = DiagnosticReporter()
        self.scanner_mode = scanner_mode

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
        if self.scanner_mode:
            print("Lox Scanner (Modo Tokens)")
            print("Escribe código para ver sus tokens. Escribe 'exit' o presiona Ctrl+D para salir.\n")
            prompt_str = "lox (scanner)> "
        else:
            print("Lox Tree-Walk Interpreter (REPL)")
            print("Escribe 'exit' o presiona Ctrl+D para salir.\n")
            prompt_str = "lox> "

        while True:
            try:
                line = input(prompt_str)
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

    def run(self, source: str) -> list:
        scanner = Scanner(source, diagnostics=self.diagnostics)
        tokens = scanner.scan_tokens()

        if self.scanner_mode:
            for token in tokens:
                print(token)

        # En la Fase 2 pasaremos tokens al Parser si no estamos en scanner_mode
        return tokens


def main() -> None:
    args = sys.argv[1:]
    scanner_mode = False

    # Verificamos si se solicitó el modo scanner
    if "scanner" in args:
        scanner_mode = True
        args.remove("scanner")
    elif "--scanner" in args:
        scanner_mode = True
        args.remove("--scanner")

    cli = LoxCLI(scanner_mode=scanner_mode)

    if len(args) > 1:
        print("Uso: pylox [scanner] [script.lox]", file=sys.stderr)
        sys.exit(64)
    elif len(args) == 1:
        cli.run_file(args[0])
    else:
        cli.run_prompt()


if __name__ == "__main__":
    main()
