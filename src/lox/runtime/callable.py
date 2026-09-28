from abc import ABC, abstractmethod
import time
from typing import Any
from lox.syntax.ast import FunDecl
from lox.runtime.environment import Environment
from lox.errors import LoxReturnException


class LoxCallable(ABC):

    @abstractmethod
    def arity(self) -> int:
        pass

    @abstractmethod
    def call(self, interpreter: Any, arguments: list[Any]) -> Any:
        pass


class LoxFunction(LoxCallable):

    def __init__(self, declaration: FunDecl, closure: Environment):
        self.declaration = declaration
        self.closure = closure

    def arity(self) -> int:
        return len(self.declaration.params)

    def call(self, interpreter: Any, arguments: list[Any]) -> Any:
        environment = Environment(enclosing=self.closure)
        for param, argument in zip(self.declaration.params, arguments):
            environment.define(param.lexeme, argument)

        try:
            interpreter.execute_block(self.declaration.body, environment)
        except LoxReturnException as return_value:
            return return_value.value

        return None

    def __str__(self) -> str:
        return f"<fn {self.declaration.name.lexeme}>"


class ClockFunction(LoxCallable):

    def arity(self) -> int:
        return 0

    def call(self, interpreter: Any, arguments: list[Any]) -> Any:
        return float(time.time())

    def __str__(self) -> str:
        return "<native fn clock>"
