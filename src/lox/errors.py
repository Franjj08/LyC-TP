from dataclasses import dataclass
import sys
from typing import Optional


class LoxError(Exception):
    """Clase base para todos los errores del intérprete Lox."""

    def __init__(self, message: str, line: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.line = line

    def __str__(self) -> str:
        if self.line is not None:
            return f"[línea {self.line}] Error: {self.message}"
        return f"Error: {self.message}"


class LoxLexicalError(LoxError):
    """Error emitido durante el análisis léxico (Scanner)."""
    pass


class LoxSyntaxError(LoxError):
    """Error emitido durante el análisis sintáctico (Parser)."""
    pass


class LoxResolutionError(LoxError):
    """Error emitido durante el análisis semántico (Resolver)."""
    pass


class LoxRuntimeError(LoxError):
    """Error emitido durante la ejecución (Interpreter)."""
    pass


class LoxReturnException(Exception):
    """Excepción de control de flujo utilizada para desenrollar el stack en sentencias return."""

    def __init__(self, value: object):
        super().__init__("Return value unwinding")
        self.value = value


class DiagnosticReporter:
    """Manejador centralizado de diagnóstico y reporte de errores."""

    def __init__(self):
        self.had_error: bool = False
        self.had_runtime_error: bool = False

    def report_error(self, line: int, where: str, message: str) -> None:
        self.had_error = True
        print(f"[línea {line}] Error{where}: {message}", file=sys.stderr)

    def report_runtime_error(self, error: LoxRuntimeError) -> None:
        self.had_runtime_error = True
        print(f"{error}", file=sys.stderr)

    def reset(self) -> None:
        self.had_error = False
        self.had_runtime_error = False
