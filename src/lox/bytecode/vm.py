import time
from typing import Any, Optional

from lox.bytecode.chunk import OpCode
from lox.bytecode.compiler import BytecodeCompiler
from lox.bytecode.objects import (
    CallFrame,
    ObjBoundMethod,
    ObjClass,
    ObjClosure,
    ObjFunction,
    ObjInstance,
    ObjNative,
    ObjUpvalue,
)
from lox.errors import DiagnosticReporter, LoxRuntimeError
from lox.syntax.ast import Expr, ExpressionStmt, Stmt


class VirtualMachine:
    """Máquina Virtual basada en pila (Stack-based VM) para ejecutar Bytecode de Lox."""

    MAX_FRAMES = 256

    def __init__(self, diagnostics: Optional[DiagnosticReporter] = None) -> None:
        self.diagnostics: Optional[DiagnosticReporter] = diagnostics
        self.frames: list[CallFrame] = []
        self.stack: list[Any] = []
        self.globals: dict[str, Any] = {}
        self.open_upvalues: list[ObjUpvalue] = []

        self._define_native("clock", 0, lambda _args: float(time.time()))

    def _define_native(self, name: str, arity: int, fn: Any) -> None:
        self.globals[name] = ObjNative(name=name, arity=arity, fn=fn)

    def push(self, value: Any) -> None:
        self.stack.append(value)

    def pop(self) -> Any:
        if not self.stack:
            raise RuntimeError("Stack underflow en la Máquina Virtual.")
        return self.stack.pop()

    def peek(self, distance: int = 0) -> Any:
        return self.stack[-1 - distance]

    def interpret(
        self,
        target: list[Stmt] | Stmt | Expr,
        disassemble: bool = False,
    ) -> Any:
        compiler = BytecodeCompiler(diagnostics=self.diagnostics)

        if isinstance(target, list):
            statements = target
        elif isinstance(target, Stmt):
            statements = [target]
        else:
            statements = [ExpressionStmt(expression=target)]

        function = compiler.compile(statements)
        if function is None:
            return None

        if disassemble:
            self._print_disassembly(function)

        return self.run(function)

    def _print_disassembly(self, function: ObjFunction) -> None:
        name = "<script>" if function.name is None else function.name
        print(function.chunk.disassemble(name))
        for const in function.chunk.constants:
            if isinstance(const, ObjFunction):
                print()
                self._print_disassembly(const)

    def run(self, function: ObjFunction) -> Any:
        self.stack.clear()
        self.frames.clear()
        self.open_upvalues.clear()

        script_closure = ObjClosure(function)
        self.push(script_closure)
        self.frames.append(CallFrame(closure=script_closure, ip=0, base_slot=0))

        try:
            return self._execute()
        except LoxRuntimeError as error:
            self.stack.clear()
            self.frames.clear()
            self.open_upvalues.clear()
            if self.diagnostics:
                self.diagnostics.report_runtime_error(error)
                return None
            raise

    def _execute(self) -> Any:
        while self.frames:
            frame = self.frames[-1]
            chunk = frame.closure.function.chunk
            code = chunk.code
            constants = chunk.constants

            op_offset = frame.ip
            byte = code[frame.ip]
            frame.ip += 1

            match byte:
                case OpCode.OP_CONSTANT:
                    const_idx = code[frame.ip]
                    frame.ip += 1
                    self.push(constants[const_idx])

                case OpCode.OP_NIL:
                    self.push(None)

                case OpCode.OP_TRUE:
                    self.push(True)

                case OpCode.OP_FALSE:
                    self.push(False)

                case OpCode.OP_POP:
                    self.pop()

                case OpCode.OP_GET_LOCAL:
                    slot = code[frame.ip]
                    frame.ip += 1
                    self.push(self.stack[frame.base_slot + slot])

                case OpCode.OP_SET_LOCAL:
                    slot = code[frame.ip]
                    frame.ip += 1
                    self.stack[frame.base_slot + slot] = self.peek(0)

                case OpCode.OP_GET_GLOBAL:
                    name = constants[code[frame.ip]]
                    frame.ip += 1
                    if name not in self.globals:
                        self._error(f"Variable no definida '{name}'.", frame, op_offset)
                    self.push(self.globals[name])

                case OpCode.OP_DEFINE_GLOBAL:
                    name = constants[code[frame.ip]]
                    frame.ip += 1
                    self.globals[name] = self.pop()

                case OpCode.OP_SET_GLOBAL:
                    name = constants[code[frame.ip]]
                    frame.ip += 1
                    if name not in self.globals:
                        self._error(f"Variable no definida '{name}'.", frame, op_offset)
                    self.globals[name] = self.peek(0)

                case OpCode.OP_GET_UPVALUE:
                    slot = code[frame.ip]
                    frame.ip += 1
                    upvalue = frame.closure.upvalues[slot]
                    if upvalue.location is not None:
                        self.push(self.stack[upvalue.location])
                    else:
                        self.push(upvalue.closed)

                case OpCode.OP_SET_UPVALUE:
                    slot = code[frame.ip]
                    frame.ip += 1
                    upvalue = frame.closure.upvalues[slot]
                    if upvalue.location is not None:
                        self.stack[upvalue.location] = self.peek(0)
                    else:
                        upvalue.closed = self.peek(0)

                case OpCode.OP_CLOSE_UPVALUE:
                    self._close_upvalues(len(self.stack) - 1)
                    self.pop()

                case OpCode.OP_EQUAL:
                    b = self.pop()
                    a = self.pop()
                    self.push(self._is_equal(a, b))

                case OpCode.OP_BANG_EQUAL:
                    b = self.pop()
                    a = self.pop()
                    self.push(not self._is_equal(a, b))

                case OpCode.OP_GREATER:
                    b = self.pop()
                    a = self.pop()
                    self._check_numbers(a, b, frame, op_offset)
                    self.push(float(a) > float(b))

                case OpCode.OP_GREATER_EQUAL:
                    b = self.pop()
                    a = self.pop()
                    self._check_numbers(a, b, frame, op_offset)
                    self.push(float(a) >= float(b))

                case OpCode.OP_LESS:
                    b = self.pop()
                    a = self.pop()
                    self._check_numbers(a, b, frame, op_offset)
                    self.push(float(a) < float(b))

                case OpCode.OP_LESS_EQUAL:
                    b = self.pop()
                    a = self.pop()
                    self._check_numbers(a, b, frame, op_offset)
                    self.push(float(a) <= float(b))

                case OpCode.OP_ADD:
                    b = self.pop()
                    a = self.pop()
                    if self._is_number(a) and self._is_number(b):
                        self.push(float(a) + float(b))
                    elif isinstance(a, str) and isinstance(b, str):
                        self.push(a + b)
                    else:
                        self._error(
                            "Los operandos deben ser dos números o dos cadenas de texto.",
                            frame,
                            op_offset,
                        )

                case OpCode.OP_SUBTRACT:
                    b = self.pop()
                    a = self.pop()
                    self._check_numbers(a, b, frame, op_offset)
                    self.push(float(a) - float(b))

                case OpCode.OP_MULTIPLY:
                    b = self.pop()
                    a = self.pop()
                    self._check_numbers(a, b, frame, op_offset)
                    self.push(float(a) * float(b))

                case OpCode.OP_DIVIDE:
                    b = self.pop()
                    a = self.pop()
                    self._check_numbers(a, b, frame, op_offset)
                    if float(b) == 0.0:
                        self._error("División por cero.", frame, op_offset)
                    self.push(float(a) / float(b))

                case OpCode.OP_MODULO:
                    b = self.pop()
                    a = self.pop()
                    self._check_numbers(a, b, frame, op_offset)
                    if float(b) == 0.0:
                        self._error("Módulo por cero.", frame, op_offset)
                    self.push(float(a) % float(b))

                case OpCode.OP_NOT:
                    self.push(not self._is_truthy(self.pop()))

                case OpCode.OP_NEGATE:
                    val = self.pop()
                    if not self._is_number(val):
                        self._error(
                            "El operando debe ser un número.", frame, op_offset
                        )
                    self.push(-float(val))

                case OpCode.OP_PRINT:
                    print(self.stringify(self.pop()))

                case OpCode.OP_JUMP:
                    offset = (code[frame.ip] << 8) | code[frame.ip + 1]
                    frame.ip += 2 + offset

                case OpCode.OP_JUMP_IF_FALSE:
                    offset = (code[frame.ip] << 8) | code[frame.ip + 1]
                    frame.ip += 2
                    if not self._is_truthy(self.peek(0)):
                        frame.ip += offset

                case OpCode.OP_LOOP:
                    offset = (code[frame.ip] << 8) | code[frame.ip + 1]
                    frame.ip += 2 - offset

                case OpCode.OP_CALL:
                    arg_count = code[frame.ip]
                    frame.ip += 1
                    callee = self.peek(arg_count)
                    self._call_value(callee, arg_count, frame, op_offset)

                case OpCode.OP_CLOSURE:
                    const_idx = code[frame.ip]
                    frame.ip += 1
                    fn_obj: ObjFunction = constants[const_idx]
                    closure = ObjClosure(fn_obj)
                    self.push(closure)
                    for _ in range(fn_obj.upvalue_count):
                        is_local = code[frame.ip]
                        index = code[frame.ip + 1]
                        frame.ip += 2
                        if is_local:
                            closure.upvalues.append(
                                self._capture_upvalue(frame.base_slot + index)
                            )
                        else:
                            closure.upvalues.append(
                                frame.closure.upvalues[index]
                            )

                case OpCode.OP_CLASS:
                    name = constants[code[frame.ip]]
                    frame.ip += 1
                    self.push(ObjClass(name))

                case OpCode.OP_INHERIT:
                    subclass = self.pop()
                    superclass = self.peek(0)
                    if not isinstance(superclass, ObjClass):
                        self._error(
                            "La superclase debe ser una clase.", frame, op_offset
                        )
                    assert isinstance(subclass, ObjClass)
                    subclass.methods.update(superclass.methods)

                case OpCode.OP_METHOD:
                    name = constants[code[frame.ip]]
                    frame.ip += 1
                    method = self.pop()
                    klass = self.peek(0)
                    assert isinstance(klass, ObjClass) and isinstance(
                        method, ObjClosure
                    )
                    klass.methods[name] = method

                case OpCode.OP_GET_PROPERTY:
                    name = constants[code[frame.ip]]
                    frame.ip += 1
                    instance = self.peek(0)
                    if not isinstance(instance, ObjInstance):
                        self._error(
                            "Solo las instancias tienen propiedades.",
                            frame,
                            op_offset,
                        )
                    if name in instance.fields:
                        value = instance.fields[name]
                        self.pop()
                        self.push(value)
                    elif name in instance.klass.methods:
                        bound = ObjBoundMethod(
                            receiver=instance,
                            method=instance.klass.methods[name],
                        )
                        self.pop()
                        self.push(bound)
                    else:
                        self._error(
                            f"Propiedad no definida '{name}'.", frame, op_offset
                        )

                case OpCode.OP_SET_PROPERTY:
                    name = constants[code[frame.ip]]
                    frame.ip += 1
                    instance = self.peek(1)
                    if not isinstance(instance, ObjInstance):
                        self._error(
                            "Solo las instancias tienen campos.",
                            frame,
                            op_offset,
                        )
                    value = self.pop()
                    self.pop()
                    instance.fields[name] = value
                    self.push(value)

                case OpCode.OP_GET_SUPER:
                    name = constants[code[frame.ip]]
                    frame.ip += 1
                    superclass = self.pop()
                    receiver = self.pop()
                    assert isinstance(superclass, ObjClass) and isinstance(
                        receiver, ObjInstance
                    )
                    method = superclass.methods.get(name)
                    if method is None:
                        self._error(
                            f"Propiedad no definida '{name}'.", frame, op_offset
                        )
                    self.push(ObjBoundMethod(receiver=receiver, method=method))

                case OpCode.OP_RETURN:
                    result = self.pop()
                    finished_frame = self.frames.pop()
                    self._close_upvalues(finished_frame.base_slot)

                    if not self.frames:
                        self.stack.clear()
                        return result

                    del self.stack[finished_frame.base_slot :]
                    self.push(result)

                case _:
                    self._error(
                        f"Instrucción de bytecode desconocida: {byte}",
                        frame,
                        op_offset,
                    )

        return None

    # ---------- Invocación y Upvalues ---------- #

    def _call_value(
        self,
        callee: Any,
        arg_count: int,
        frame: CallFrame,
        op_offset: int,
    ) -> None:
        if isinstance(callee, ObjBoundMethod):
            self.stack[-1 - arg_count] = callee.receiver
            self._call_closure(callee.method, arg_count, frame, op_offset)
        elif isinstance(callee, ObjClass):
            instance = ObjInstance(callee)
            self.stack[-1 - arg_count] = instance
            initializer = callee.methods.get("init")
            if initializer is not None:
                self._call_closure(initializer, arg_count, frame, op_offset)
            elif arg_count != 0:
                self._error(
                    f"Se esperaban 0 argumentos pero se obtuvieron {arg_count}.",
                    frame,
                    op_offset,
                )
        elif isinstance(callee, ObjClosure):
            self._call_closure(callee, arg_count, frame, op_offset)
        elif isinstance(callee, ObjNative):
            if arg_count != callee.arity:
                self._error(
                    f"Se esperaban {callee.arity} argumentos pero se obtuvieron {arg_count}.",
                    frame,
                    op_offset,
                )
            args = (
                self.stack[len(self.stack) - arg_count :]
                if arg_count > 0
                else []
            )
            del self.stack[len(self.stack) - arg_count - 1 :]
            result = callee.fn(args)
            self.push(result)
        else:
            self._error(
                "Solo se pueden invocar funciones y clases.", frame, op_offset
            )

    def _call_closure(
        self,
        closure: ObjClosure,
        arg_count: int,
        frame: CallFrame,
        op_offset: int,
    ) -> None:
        arity = closure.function.arity
        if arg_count != arity:
            self._error(
                f"Se esperaban {arity} argumentos pero se obtuvieron {arg_count}.",
                frame,
                op_offset,
            )
        if len(self.frames) >= self.MAX_FRAMES:
            self._error("Stack overflow.", frame, op_offset)

        base_slot = len(self.stack) - arg_count - 1
        self.frames.append(
            CallFrame(closure=closure, ip=0, base_slot=base_slot)
        )

    def _capture_upvalue(self, stack_location: int) -> ObjUpvalue:
        for uv in self.open_upvalues:
            if uv.location == stack_location:
                return uv

        created = ObjUpvalue(location=stack_location)
        insert_idx = len(self.open_upvalues)
        for i, uv in enumerate(self.open_upvalues):
            if uv.location is not None and uv.location < stack_location:
                insert_idx = i
                break
        self.open_upvalues.insert(insert_idx, created)
        return created

    def _close_upvalues(self, last_slot: int) -> None:
        while self.open_upvalues:
            uv = self.open_upvalues[0]
            if uv.location is not None and uv.location >= last_slot:
                uv.closed = self.stack[uv.location]
                uv.location = None
                self.open_upvalues.pop(0)
            else:
                break

    # ---------- Helpers de Tipos y Errores ---------- #

    def _error(
        self, message: str, frame: CallFrame, op_offset: int
    ) -> None:
        lines = frame.closure.function.chunk.lines
        line = lines[op_offset] if 0 <= op_offset < len(lines) else None
        raise LoxRuntimeError(message, line=line)

    @staticmethod
    def _is_number(value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    def _check_numbers(
        self, a: Any, b: Any, frame: CallFrame, op_offset: int
    ) -> None:
        if self._is_number(a) and self._is_number(b):
            return
        self._error("Los operandos deben ser números.", frame, op_offset)

    @staticmethod
    def _is_truthy(value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        return True

    def _is_equal(self, a: Any, b: Any) -> bool:
        if a is None and b is None:
            return True
        if a is None or b is None:
            return False
        if isinstance(a, bool) or isinstance(b, bool):
            if not (isinstance(a, bool) and isinstance(b, bool)):
                return False
            return a is b
        if self._is_number(a) and self._is_number(b):
            return float(a) == float(b)
        return a == b

    def stringify(self, value: Any) -> str:
        if value is None:
            return "nil"
        if isinstance(value, bool):
            return "true" if value else "false"
        if self._is_number(value):
            text = str(float(value))
            if text.endswith(".0"):
                return text[:-2]
            return text
        return str(value)

