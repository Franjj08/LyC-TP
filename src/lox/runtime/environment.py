from typing import Any, Optional
from lox.syntax.token import Token
from lox.errors import LoxRuntimeError


class Environment:
    """Tabla de símbolos que asocia nombres de variables con sus valores en tiempo de ejecución.

    Soporta entornos anidados mediante un enlace léxico a su entorno envolvente (enclosing).
    """

    def __init__(self, enclosing: Optional["Environment"] = None):
        self.values: dict[str, Any] = {}
        self.enclosing: Optional["Environment"] = enclosing

    def define(self, name: str, value: Any) -> None:
        """Define o redefine una variable en el ámbito actual."""
        self.values[name] = value

    def get(self, name: Token) -> Any:
        """Obtiene el valor de una variable en este ámbito o en sus envolventes."""
        if name.lexeme in self.values:
            return self.values[name.lexeme]

        if self.enclosing is not None:
            return self.enclosing.get(name)

        raise LoxRuntimeError(f"Variable no definida '{name.lexeme}'.", token=name)

    def assign(self, name: Token, value: Any) -> None:
        """Asigna un nuevo valor a una variable existente en este ámbito o en sus envolventes."""
        if name.lexeme in self.values:
            self.values[name.lexeme] = value
            return

        if self.enclosing is not None:
            self.enclosing.assign(name, value)
            return

        raise LoxRuntimeError(f"Variable no definida '{name.lexeme}'.", token=name)
