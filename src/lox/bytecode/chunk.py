from enum import IntEnum, auto
from typing import Any


class OpCode(IntEnum):
    # Instrucciones sin operandos (1 byte)
    OP_NIL = auto()
    OP_TRUE = auto()
    OP_FALSE = auto()
    OP_POP = auto()
    OP_ADD = auto()
    OP_SUBTRACT = auto()
    OP_MULTIPLY = auto()
    OP_DIVIDE = auto()
    OP_MODULO = auto()
    OP_NEGATE = auto()
    OP_NOT = auto()
    OP_EQUAL = auto()
    OP_BANG_EQUAL = auto()
    OP_GREATER = auto()
    OP_GREATER_EQUAL = auto()
    OP_LESS = auto()
    OP_LESS_EQUAL = auto()
    OP_PRINT = auto()
    OP_RETURN = auto()
    OP_CLOSE_UPVALUE = auto()
    OP_INHERIT = auto()

    # Instrucciones con índice de constante (1 byte de operando)
    OP_CONSTANT = auto()
    OP_DEFINE_GLOBAL = auto()
    OP_GET_GLOBAL = auto()
    OP_SET_GLOBAL = auto()
    OP_CLASS = auto()
    OP_METHOD = auto()
    OP_GET_PROPERTY = auto()
    OP_SET_PROPERTY = auto()
    OP_GET_SUPER = auto()

    # Instrucciones con slot / contador de 1 byte
    OP_GET_LOCAL = auto()
    OP_SET_LOCAL = auto()
    OP_GET_UPVALUE = auto()
    OP_SET_UPVALUE = auto()
    OP_CALL = auto()

    # Instrucciones de salto con offset de 16 bits big-endian (2 bytes de operando)
    OP_JUMP = auto()
    OP_JUMP_IF_FALSE = auto()
    OP_LOOP = auto()

    # Instrucción de longitud variable para closures
    OP_CLOSURE = auto()


class Chunk:
    """Secuencia de bytecode compilado junto con su pool de constantes y líneas de origen."""

    def __init__(self) -> None:
        self.code: bytearray = bytearray()
        self.constants: list[Any] = []
        self.lines: list[int] = []

    def write(self, byte: int, line: int = 1) -> None:
        self.code.append(int(byte) & 0xFF)
        self.lines.append(line)

    def add_constant(self, value: Any) -> int:
        self.constants.append(value)
        return len(self.constants) - 1

    def disassemble(self, name: str = "<script>") -> str:
        lines_out: list[str] = [f"== {name} =="]
        offset = 0
        while offset < len(self.code):
            offset, text = self.disassemble_instruction(offset)
            lines_out.append(text)
        return "\n".join(lines_out)

    def disassemble_instruction(self, offset: int) -> tuple[int, str]:
        line_num = self.lines[offset] if offset < len(self.lines) else 0
        line_prefix = (
            "   |"
            if offset > 0 and line_num == self.lines[offset - 1]
            else f"{line_num:4d}"
        )
        prefix = f"{offset:04d} {line_prefix} "
        opcode_byte = self.code[offset]

        try:
            op = OpCode(opcode_byte)
        except ValueError:
            return offset + 1, f"{prefix}UNKNOWN_OP ({opcode_byte})"

        match op:
            case (
                OpCode.OP_CONSTANT
                | OpCode.OP_DEFINE_GLOBAL
                | OpCode.OP_GET_GLOBAL
                | OpCode.OP_SET_GLOBAL
                | OpCode.OP_CLASS
                | OpCode.OP_METHOD
                | OpCode.OP_GET_PROPERTY
                | OpCode.OP_SET_PROPERTY
                | OpCode.OP_GET_SUPER
            ):
                const_idx = self.code[offset + 1]
                const_val = self.constants[const_idx]
                return (
                    offset + 2,
                    f"{prefix}{op.name:<18} {const_idx:4d} ({const_val!r})",
                )

            case (
                OpCode.OP_GET_LOCAL
                | OpCode.OP_SET_LOCAL
                | OpCode.OP_GET_UPVALUE
                | OpCode.OP_SET_UPVALUE
                | OpCode.OP_CALL
            ):
                slot = self.code[offset + 1]
                return offset + 2, f"{prefix}{op.name:<18} {slot:4d}"

            case OpCode.OP_JUMP | OpCode.OP_JUMP_IF_FALSE | OpCode.OP_LOOP:
                high = self.code[offset + 1]
                low = self.code[offset + 2]
                jump = (high << 8) | low
                sign = -1 if op == OpCode.OP_LOOP else 1
                target = offset + 3 + sign * jump
                return (
                    offset + 3,
                    f"{prefix}{op.name:<18} {offset:4d} -> {target:4d}",
                )

            case OpCode.OP_CLOSURE:
                const_idx = self.code[offset + 1]
                fn_obj = self.constants[const_idx]
                parts = [f"{prefix}{op.name:<18} {const_idx:4d} ({fn_obj!r})"]
                cursor = offset + 2
                upvalue_count = getattr(fn_obj, "upvalue_count", 0)
                for _ in range(upvalue_count):
                    is_local = self.code[cursor]
                    index = self.code[cursor + 1]
                    kind = "local" if is_local else "upvalue"
                    parts.append(f"{cursor:04d}    |                     {kind} {index}")
                    cursor += 2
                return cursor, "\n".join(parts)

            case _:
                return offset + 1, f"{prefix}{op.name}"

