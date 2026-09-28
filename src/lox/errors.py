from dataclasses import dataclass
import sys
from typing import Any, Optional


class LoxError(Exception):

    def __init__(self, message: str, line: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.line = line

    def __str__(self) -> str:
        if self.line is not None:
            return f"[línea {self.line}] Error: {self.message}"
        return f"Error: {self.message}"


class LoxLexicalError(LoxError):
    pass


class LoxSyntaxError(LoxError):
    pass


class LoxResolutionError(LoxError):
    pass


class LoxRuntimeError(LoxError):

    def __init__(
        self,
        message: str,
        token: Optional[Any] = None,
        line: Optional[int] = None,
    ):
        token_line = getattr(token, "line", None) if token is not None else None
        effective_line = token_line if token_line is not None else line
        super().__init__(message, line=effective_line)
        self.token = token


class LoxReturnException(Exception):

    def __init__(self, value: object):
        super().__init__("Return value unwinding")
        self.value = value


class DiagnosticReporter:

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
