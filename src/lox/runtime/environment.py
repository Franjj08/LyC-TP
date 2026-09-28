from typing import Any, Optional
from lox.syntax.token import Token
from lox.errors import LoxRuntimeError


class Environment:

    def __init__(self, enclosing: Optional["Environment"] = None):
        self.values: dict[str, Any] = {}
        self.enclosing: Optional["Environment"] = enclosing

    def define(self, name: str, value: Any) -> None:
        self.values[name] = value

    def get(self, name: Token) -> Any:
        if name.lexeme in self.values:
            return self.values[name.lexeme]

        if self.enclosing is not None:
            return self.enclosing.get(name)

        raise LoxRuntimeError(f"Variable no definida '{name.lexeme}'.", token=name)

    def assign(self, name: Token, value: Any) -> None:
        if name.lexeme in self.values:
            self.values[name.lexeme] = value
            return

        if self.enclosing is not None:
            self.enclosing.assign(name, value)
            return

        raise LoxRuntimeError(f"Variable no definida '{name.lexeme}'.", token=name)

    def ancestor(self, distance: int) -> "Environment":
        environment = self
        for _ in range(distance):
            assert environment.enclosing is not None, "El entorno envolvente no puede ser nulo en la distancia resuelta."
            environment = environment.enclosing
        return environment

    def get_at(self, distance: int, name: str) -> Any:
        return self.ancestor(distance).values.get(name)

    def assign_at(self, distance: int, name: Token, value: Any) -> None:
        self.ancestor(distance).values[name.lexeme] = value
