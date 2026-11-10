from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from lox.bytecode.chunk import Chunk


class ObjFunction:
    """Representación en tiempo de compilación y ejecución de una función Lox."""

    def __init__(self, name: Optional[str] = None, arity: int = 0) -> None:
        self.name: Optional[str] = name
        self.arity: int = arity
        self.upvalue_count: int = 0
        self.chunk: Chunk = Chunk()

    def __repr__(self) -> str:
        if self.name is None:
            return "<script>"
        return f"<fn {self.name}>"

    def __str__(self) -> str:
        return repr(self)


class ObjUpvalue:
    """Referencia a una variable local capturada por un closure (abierta en stack o cerrada en heap)."""

    def __init__(self, location: Optional[int]) -> None:
        self.location: Optional[int] = location
        self.closed: Any = None

    def __repr__(self) -> str:
        if self.location is not None:
            return f"<upvalue @{self.location}>"
        return f"<upvalue closed={self.closed!r}>"


class ObjClosure:
    """Función empaquetada junto con sus upvalues capturados en tiempo de ejecución."""

    def __init__(self, function: ObjFunction) -> None:
        self.function: ObjFunction = function
        self.upvalues: list[ObjUpvalue] = []

    def __repr__(self) -> str:
        return repr(self.function)

    def __str__(self) -> str:
        return str(self.function)


class ObjNative:
    """Función nativa de la máquina virtual (ej. clock)."""

    def __init__(self, name: str, arity: int, fn: Callable[[list[Any]], Any]) -> None:
        self.name: str = name
        self.arity: int = arity
        self.fn: Callable[[list[Any]], Any] = fn

    def __repr__(self) -> str:
        return "<native fn>"

    def __str__(self) -> str:
        return "<native fn>"


class ObjClass:
    """Representación de una clase Lox en la VM."""

    def __init__(self, name: str) -> None:
        self.name: str = name
        self.methods: dict[str, ObjClosure] = {}

    def __repr__(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.name


class ObjInstance:
    """Instancia de una clase Lox en la VM."""

    def __init__(self, klass: ObjClass) -> None:
        self.klass: ObjClass = klass
        self.fields: dict[str, Any] = {}

    def __repr__(self) -> str:
        return f"{self.klass.name} instance"

    def __str__(self) -> str:
        return f"{self.klass.name} instance"


class ObjBoundMethod:
    """Método enlazado a una instancia particular (`this`)."""

    def __init__(self, receiver: ObjInstance, method: ObjClosure) -> None:
        self.receiver: ObjInstance = receiver
        self.method: ObjClosure = method

    def __repr__(self) -> str:
        return repr(self.method.function)

    def __str__(self) -> str:
        return str(self.method.function)


@dataclass
class CallFrame:
    """Marco de activación de una invocación de función en la pila de la VM."""

    closure: ObjClosure
    ip: int = 0
    base_slot: int = 0

