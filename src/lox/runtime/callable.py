from abc import ABC, abstractmethod
from typing import Any, Optional
from lox.syntax.ast import FunDecl
from lox.syntax.token import Token
from lox.runtime.environment import Environment
from lox.errors import LoxReturnException, LoxRuntimeError


class LoxCallable(ABC):

    @abstractmethod
    def arity(self) -> int:
        pass

    @abstractmethod
    def call(self, interpreter: Any, arguments: list[Any]) -> Any:
        pass


class LoxFunction(LoxCallable):

    def __init__(
        self,
        declaration: FunDecl,
        closure: Environment,
        is_initializer: bool = False,
    ):
        self.declaration = declaration
        self.closure = closure
        self.is_initializer = is_initializer

    def bind(self, instance: "LoxInstance") -> "LoxFunction":
        environment = Environment(enclosing=self.closure)
        environment.define("this", instance)
        return LoxFunction(
            declaration=self.declaration,
            closure=environment,
            is_initializer=self.is_initializer,
        )

    def arity(self) -> int:
        return len(self.declaration.params)

    def call(self, interpreter: Any, arguments: list[Any]) -> Any:
        environment = Environment(enclosing=self.closure)
        for param, argument in zip(self.declaration.params, arguments):
            environment.define(param.lexeme, argument)

        try:
            interpreter.execute_block(self.declaration.body, environment)
        except LoxReturnException as return_value:
            if self.is_initializer:
                return self.closure.get_at(0, "this")
            return return_value.value

        if self.is_initializer:
            return self.closure.get_at(0, "this")
        return None

    def __str__(self) -> str:
        return f"<fn {self.declaration.name.lexeme}>"


class LoxClass(LoxCallable):

    def __init__(
        self,
        name: str,
        superclass: Optional["LoxClass"],
        methods: dict[str, LoxFunction],
    ):
        self.name = name
        self.superclass = superclass
        self.methods = methods

    def find_method(self, name: str) -> Optional[LoxFunction]:
        if name in self.methods:
            return self.methods[name]
        if self.superclass is not None:
            return self.superclass.find_method(name)
        return None

    def arity(self) -> int:
        initializer = self.find_method("init")
        if initializer is None:
            return 0
        return initializer.arity()

    def call(self, interpreter: Any, arguments: list[Any]) -> Any:
        instance = LoxInstance(self)
        initializer = self.find_method("init")
        if initializer is not None:
            initializer.bind(instance).call(interpreter, arguments)
        return instance

    def __str__(self) -> str:
        return self.name


class LoxInstance:

    def __init__(self, klass: LoxClass):
        self.klass = klass
        self.fields: dict[str, Any] = {}

    def get(self, name: Token) -> Any:
        if name.lexeme in self.fields:
            return self.fields[name.lexeme]

        method = self.klass.find_method(name.lexeme)
        if method is not None:
            return method.bind(self)

        raise LoxRuntimeError(f"Propiedad no definida '{name.lexeme}'.", token=name)

    def set(self, name: Token, value: Any) -> None:
        self.fields[name.lexeme] = value

    def __str__(self) -> str:
        return f"{self.klass.name} instance"
