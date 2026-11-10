from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

from lox.bytecode.chunk import Chunk, OpCode
from lox.bytecode.objects import ObjFunction
from lox.errors import DiagnosticReporter
from lox.syntax.ast import (
    AssignmentExpr,
    BinaryExpr,
    BlockStmt,
    CallExpr,
    ClassDecl,
    Expr,
    ExprVisitor,
    ExpressionStmt,
    FunDecl,
    GetExpr,
    GroupingExpr,
    IfStmt,
    LiteralExpr,
    LogicalExpr,
    PrintStmt,
    ReturnStmt,
    SetExpr,
    Stmt,
    StmtVisitor,
    SuperExpr,
    ThisExpr,
    UnaryExpr,
    VarDecl,
    VariableExpr,
    WhileStmt,
)
from lox.syntax.token import Token, TokenType


class FunctionKind(Enum):
    SCRIPT = auto()
    FUNCTION = auto()
    METHOD = auto()
    INITIALIZER = auto()


@dataclass
class LocalSlot:
    name: str
    depth: int
    initialized: bool = False
    is_captured: bool = False


@dataclass
class UpvalueSlot:
    index: int
    is_local: bool


@dataclass
class ClassCompilerContext:
    enclosing: Optional["ClassCompilerContext"] = None
    has_superclass: bool = False


class CompilerState:
    """Estado de compilación por unidad funcional (script, función o método)."""

    def __init__(
        self,
        function_type: FunctionKind,
        name: Optional[str] = None,
        enclosing: Optional["CompilerState"] = None,
    ) -> None:
        self.enclosing: Optional["CompilerState"] = enclosing
        self.function_type: FunctionKind = function_type
        self.function: ObjFunction = ObjFunction(name=name)
        self.scope_depth: int = 0
        self.locals: list[LocalSlot] = []
        self.upvalues: list[UpvalueSlot] = []

        # Reservamos el slot 0 del CallFrame:
        # En métodos e inicializadores almacena el receptor `this`;
        # en funciones normales y el script almacena la propia clausura.
        slot_zero_name = (
            "this"
            if function_type in (FunctionKind.METHOD, FunctionKind.INITIALIZER)
            else ""
        )
        self.locals.append(
            LocalSlot(name=slot_zero_name, depth=0, initialized=True)
        )

    def add_upvalue(self, index: int, is_local: bool) -> int:
        for i, upvalue in enumerate(self.upvalues):
            if upvalue.index == index and upvalue.is_local == is_local:
                return i

        self.upvalues.append(UpvalueSlot(index=index, is_local=is_local))
        self.function.upvalue_count = len(self.upvalues)
        return len(self.upvalues) - 1


class BytecodeCompiler(ExprVisitor, StmtVisitor):
    """Compilador que recorre el AST de Lox y emite Bytecode en objetos ObjFunction/Chunk."""

    def __init__(self, diagnostics: Optional[DiagnosticReporter] = None) -> None:
        self.diagnostics: Optional[DiagnosticReporter] = diagnostics
        self.state: CompilerState = CompilerState(FunctionKind.SCRIPT)
        self.current_class: Optional[ClassCompilerContext] = None
        self.current_line: int = 1

    @property
    def chunk(self) -> Chunk:
        return self.state.function.chunk

    def compile(self, statements: list[Stmt]) -> Optional[ObjFunction]:
        self.state = CompilerState(FunctionKind.SCRIPT)
        self.current_class = None

        for stmt in statements:
            self.compile_stmt(stmt)

        self._emit_return(self.current_line)

        if self.diagnostics and self.diagnostics.had_error:
            return None
        return self.state.function

    def compile_expression(self, expr: Expr) -> Optional[ObjFunction]:
        self.state = CompilerState(FunctionKind.SCRIPT)
        self.current_class = None

        self.compile_expr(expr)
        self._emit_byte(OpCode.OP_RETURN, self.current_line)

        if self.diagnostics and self.diagnostics.had_error:
            return None
        return self.state.function

    def compile_stmt(self, stmt: Stmt) -> None:
        stmt.accept(self)

    def compile_expr(self, expr: Expr) -> None:
        expr.accept(self)

    # ---------- Emisión de Bytecode y Saltos ---------- #

    def _emit_byte(self, byte: int, line: Optional[int] = None) -> None:
        target_line = self.current_line if line is None else line
        self.chunk.write(int(byte), target_line)

    def _emit_bytes(
        self, byte1: int, byte2: int, line: Optional[int] = None
    ) -> None:
        self._emit_byte(byte1, line)
        self._emit_byte(byte2, line)

    def _emit_return(self, line: Optional[int] = None) -> None:
        if self.state.function_type == FunctionKind.INITIALIZER:
            self._emit_bytes(OpCode.OP_GET_LOCAL, 0, line)
        else:
            self._emit_byte(OpCode.OP_NIL, line)
        self._emit_byte(OpCode.OP_RETURN, line)

    def _make_constant(self, value: Any) -> int:
        return self.chunk.add_constant(value)

    def _identifier_constant(self, name: str) -> int:
        for idx, existing in enumerate(self.chunk.constants):
            if type(existing) is str and existing == name:
                return idx
        return self._make_constant(name)

    def _emit_constant(self, value: Any, line: Optional[int] = None) -> None:
        const_idx = self._make_constant(value)
        self._emit_bytes(OpCode.OP_CONSTANT, const_idx, line)

    def _emit_jump(self, instruction: OpCode, line: Optional[int] = None) -> int:
        self._emit_byte(instruction, line)
        self._emit_byte(0xFF, line)
        self._emit_byte(0xFF, line)
        return len(self.chunk.code) - 2

    def _patch_jump(self, offset: int) -> None:
        jump = len(self.chunk.code) - offset - 2
        if jump > 0xFFFF:
            self._error_at_line(
                self.current_line, "Demasiado código para saltar."
            )
            return

        self.chunk.code[offset] = (jump >> 8) & 0xFF
        self.chunk.code[offset + 1] = jump & 0xFF

    def _emit_loop(self, loop_start: int, line: Optional[int] = None) -> None:
        self._emit_byte(OpCode.OP_LOOP, line)
        offset = len(self.chunk.code) - loop_start + 2
        if offset > 0xFFFF:
            self._error_at_line(
                self.current_line, "Cuerpo del bucle demasiado grande."
            )
            return

        self._emit_byte((offset >> 8) & 0xFF, line)
        self._emit_byte(offset & 0xFF, line)

    # ---------- Manejo de Scopes, Locales y Upvalues ---------- #

    def _begin_scope(self) -> None:
        self.state.scope_depth += 1

    def _end_scope(self) -> None:
        self.state.scope_depth -= 1
        while (
            self.state.locals
            and self.state.locals[-1].depth > self.state.scope_depth
        ):
            local = self.state.locals.pop()
            if local.is_captured:
                self._emit_byte(OpCode.OP_CLOSE_UPVALUE)
            else:
                self._emit_byte(OpCode.OP_POP)

    def _declare_local(self, name: Token) -> None:
        if self.state.scope_depth == 0:
            return

        for i in range(len(self.state.locals) - 1, -1, -1):
            local = self.state.locals[i]
            if local.depth != -1 and local.depth < self.state.scope_depth:
                break
            if local.name == name.lexeme:
                self._error(
                    name,
                    f"Ya existe una variable con el nombre '{name.lexeme}' en este ámbito.",
                )

        self._add_local(name.lexeme, initialized=False)

    def _add_local(self, name: str, initialized: bool = False) -> None:
        self.state.locals.append(
            LocalSlot(
                name=name,
                depth=self.state.scope_depth,
                initialized=initialized,
            )
        )

    def _mark_initialized(self) -> None:
        if self.state.scope_depth == 0:
            return
        self.state.locals[-1].initialized = True

    def _resolve_local(
        self, state: CompilerState, name: Token
    ) -> Optional[int]:
        for i in range(len(state.locals) - 1, -1, -1):
            local = state.locals[i]
            if local.name == name.lexeme:
                if not local.initialized:
                    self._error(
                        name,
                        f"No se puede leer la variable local '{name.lexeme}' en su propio inicializador.",
                    )
                return i
        return None

    def _resolve_upvalue(
        self, state: CompilerState, name: Token
    ) -> Optional[int]:
        if state.enclosing is None:
            return None

        local_idx = self._resolve_local(state.enclosing, name)
        if local_idx is not None:
            state.enclosing.locals[local_idx].is_captured = True
            return state.add_upvalue(local_idx, is_local=True)

        upvalue_idx = self._resolve_upvalue(state.enclosing, name)
        if upvalue_idx is not None:
            return state.add_upvalue(upvalue_idx, is_local=False)

        return None

    def _named_variable(self, name: Token) -> None:
        self.current_line = name.line
        if (arg := self._resolve_local(self.state, name)) is not None:
            self._emit_bytes(OpCode.OP_GET_LOCAL, arg, name.line)
        elif (arg := self._resolve_upvalue(self.state, name)) is not None:
            self._emit_bytes(OpCode.OP_GET_UPVALUE, arg, name.line)
        else:
            arg = self._identifier_constant(name.lexeme)
            self._emit_bytes(OpCode.OP_GET_GLOBAL, arg, name.line)

    # ---------- Errores ---------- #

    def _error(self, token: Token, message: str) -> None:
        where = (
            " al final del archivo"
            if token.token_type == TokenType.EOF
            else f" en '{token.lexeme}'"
        )
        if self.diagnostics:
            self.diagnostics.report_error(token.line, where, message)

    def _error_at_line(self, line: int, message: str) -> None:
        if self.diagnostics:
            self.diagnostics.report_error(line, "", message)

    # ---------- Visitors de Sentencias (StmtVisitor) ---------- #

    def visit_expression_stmt(self, stmt: ExpressionStmt) -> Any:
        self.compile_expr(stmt.expression)
        self._emit_byte(OpCode.OP_POP)
        return None

    def visit_print_stmt(self, stmt: PrintStmt) -> Any:
        self.compile_expr(stmt.expression)
        self._emit_byte(OpCode.OP_PRINT)
        return None

    def visit_var_decl(self, stmt: VarDecl) -> Any:
        self.current_line = stmt.name.line
        self._declare_local(stmt.name)

        if stmt.initializer is not None:
            self.compile_expr(stmt.initializer)
        else:
            self._emit_byte(OpCode.OP_NIL, stmt.name.line)

        if self.state.scope_depth > 0:
            self._mark_initialized()
        else:
            global_idx = self._identifier_constant(stmt.name.lexeme)
            self._emit_bytes(OpCode.OP_DEFINE_GLOBAL, global_idx, stmt.name.line)
        return None

    def visit_block_stmt(self, stmt: BlockStmt) -> Any:
        self._begin_scope()
        for s in stmt.statements:
            self.compile_stmt(s)
        self._end_scope()
        return None

    def visit_if_stmt(self, stmt: IfStmt) -> Any:
        self.compile_expr(stmt.condition)

        then_jump = self._emit_jump(OpCode.OP_JUMP_IF_FALSE)
        self._emit_byte(OpCode.OP_POP)

        self.compile_stmt(stmt.then_branch)

        else_jump = self._emit_jump(OpCode.OP_JUMP)
        self._patch_jump(then_jump)
        self._emit_byte(OpCode.OP_POP)

        if stmt.else_branch is not None:
            self.compile_stmt(stmt.else_branch)

        self._patch_jump(else_jump)
        return None

    def visit_while_stmt(self, stmt: WhileStmt) -> Any:
        loop_start = len(self.chunk.code)
        self.compile_expr(stmt.condition)

        exit_jump = self._emit_jump(OpCode.OP_JUMP_IF_FALSE)
        self._emit_byte(OpCode.OP_POP)

        self.compile_stmt(stmt.body)
        self._emit_loop(loop_start)

        self._patch_jump(exit_jump)
        self._emit_byte(OpCode.OP_POP)
        return None

    def _compile_function(
        self, stmt: FunDecl, function_type: FunctionKind
    ) -> None:
        self.current_line = stmt.name.line
        sub_state = CompilerState(
            function_type=function_type,
            name=stmt.name.lexeme,
            enclosing=self.state,
        )
        self.state = sub_state
        self._begin_scope()

        self.state.function.arity = len(stmt.params)
        for param in stmt.params:
            self._declare_local(param)
            self._mark_initialized()

        for body_stmt in stmt.body:
            self.compile_stmt(body_stmt)

        self._emit_return(stmt.name.line)

        fn_obj = self.state.function
        upvalues = self.state.upvalues
        assert self.state.enclosing is not None
        self.state = self.state.enclosing

        const_idx = self._make_constant(fn_obj)
        self._emit_bytes(OpCode.OP_CLOSURE, const_idx, stmt.name.line)
        for uv in upvalues:
            self._emit_byte(1 if uv.is_local else 0, stmt.name.line)
            self._emit_byte(uv.index, stmt.name.line)

    def visit_fun_decl(self, stmt: FunDecl) -> Any:
        self.current_line = stmt.name.line
        self._declare_local(stmt.name)
        if self.state.scope_depth > 0:
            self._mark_initialized()

        self._compile_function(stmt, FunctionKind.FUNCTION)

        if self.state.scope_depth == 0:
            global_idx = self._identifier_constant(stmt.name.lexeme)
            self._emit_bytes(OpCode.OP_DEFINE_GLOBAL, global_idx, stmt.name.line)
        return None

    def visit_return_stmt(self, stmt: ReturnStmt) -> Any:
        self.current_line = stmt.keyword.line
        if self.state.function_type == FunctionKind.SCRIPT:
            self._error(
                stmt.keyword,
                "No se puede retornar desde código de nivel superior.",
            )

        if stmt.value is None:
            self._emit_return(stmt.keyword.line)
        else:
            if self.state.function_type == FunctionKind.INITIALIZER:
                self._error(
                    stmt.keyword,
                    "No se puede retornar un valor desde un inicializador.",
                )
            self.compile_expr(stmt.value)
            self._emit_byte(OpCode.OP_RETURN, stmt.keyword.line)
        return None

    def visit_class_decl(self, stmt: ClassDecl) -> Any:
        self.current_line = stmt.name.line
        name_const = self._identifier_constant(stmt.name.lexeme)
        self._declare_local(stmt.name)

        self._emit_bytes(OpCode.OP_CLASS, name_const, stmt.name.line)
        if self.state.scope_depth > 0:
            self._mark_initialized()
        else:
            self._emit_bytes(OpCode.OP_DEFINE_GLOBAL, name_const, stmt.name.line)

        class_ctx = ClassCompilerContext(
            enclosing=self.current_class, has_superclass=False
        )
        self.current_class = class_ctx

        if stmt.superclass is not None:
            if stmt.name.lexeme == stmt.superclass.name.lexeme:
                self._error(
                    stmt.superclass.name,
                    "Una clase no puede heredar de sí misma.",
                )

            self.compile_expr(stmt.superclass)
            self._begin_scope()
            self._add_local("super", initialized=True)

            self._named_variable(stmt.name)
            self._emit_byte(OpCode.OP_INHERIT, stmt.superclass.name.line)
            class_ctx.has_superclass = True

        self._named_variable(stmt.name)
        for method in stmt.methods:
            kind = (
                FunctionKind.INITIALIZER
                if method.name.lexeme == "init"
                else FunctionKind.METHOD
            )
            self._compile_function(method, kind)
            method_const = self._identifier_constant(method.name.lexeme)
            self._emit_bytes(OpCode.OP_METHOD, method_const, method.name.line)

        self._emit_byte(OpCode.OP_POP, stmt.name.line)

        if class_ctx.has_superclass:
            self._end_scope()

        self.current_class = self.current_class.enclosing
        return None

    # ---------- Visitors de Expresiones (ExprVisitor) ---------- #

    def visit_literal_expr(self, expr: LiteralExpr) -> Any:
        if expr.value is None:
            self._emit_byte(OpCode.OP_NIL)
        elif expr.value is True:
            self._emit_byte(OpCode.OP_TRUE)
        elif expr.value is False:
            self._emit_byte(OpCode.OP_FALSE)
        else:
            self._emit_constant(expr.value)
        return None

    def visit_grouping_expr(self, expr: GroupingExpr) -> Any:
        self.compile_expr(expr.expression)
        return None

    def visit_unary_expr(self, expr: UnaryExpr) -> Any:
        self.current_line = expr.operator.line
        self.compile_expr(expr.right)

        match expr.operator.token_type:
            case TokenType.MINUS:
                self._emit_byte(OpCode.OP_NEGATE, expr.operator.line)
            case TokenType.BANG:
                self._emit_byte(OpCode.OP_NOT, expr.operator.line)
            case _:
                self._error(
                    expr.operator,
                    f"Operador unario no soportado: '{expr.operator.lexeme}'.",
                )
        return None

    def visit_binary_expr(self, expr: BinaryExpr) -> Any:
        self.current_line = expr.operator.line
        self.compile_expr(expr.left)
        self.compile_expr(expr.right)

        line = expr.operator.line
        match expr.operator.token_type:
            case TokenType.PLUS:
                self._emit_byte(OpCode.OP_ADD, line)
            case TokenType.MINUS:
                self._emit_byte(OpCode.OP_SUBTRACT, line)
            case TokenType.STAR:
                self._emit_byte(OpCode.OP_MULTIPLY, line)
            case TokenType.SLASH:
                self._emit_byte(OpCode.OP_DIVIDE, line)
            case TokenType.PERCENT:
                self._emit_byte(OpCode.OP_MODULO, line)
            case TokenType.EQUAL_EQUAL:
                self._emit_byte(OpCode.OP_EQUAL, line)
            case TokenType.BANG_EQUAL:
                self._emit_byte(OpCode.OP_BANG_EQUAL, line)
            case TokenType.GREATER:
                self._emit_byte(OpCode.OP_GREATER, line)
            case TokenType.GREATER_EQUAL:
                self._emit_byte(OpCode.OP_GREATER_EQUAL, line)
            case TokenType.LESS:
                self._emit_byte(OpCode.OP_LESS, line)
            case TokenType.LESS_EQUAL:
                self._emit_byte(OpCode.OP_LESS_EQUAL, line)
            case _:
                self._error(
                    expr.operator,
                    f"Operador binario no soportado: '{expr.operator.lexeme}'.",
                )
        return None

    def visit_logical_expr(self, expr: LogicalExpr) -> Any:
        self.current_line = expr.operator.line
        self.compile_expr(expr.left)

        if expr.operator.token_type == TokenType.AND:
            end_jump = self._emit_jump(OpCode.OP_JUMP_IF_FALSE)
            self._emit_byte(OpCode.OP_POP)
            self.compile_expr(expr.right)
            self._patch_jump(end_jump)
        else:
            else_jump = self._emit_jump(OpCode.OP_JUMP_IF_FALSE)
            end_jump = self._emit_jump(OpCode.OP_JUMP)
            self._patch_jump(else_jump)
            self._emit_byte(OpCode.OP_POP)
            self.compile_expr(expr.right)
            self._patch_jump(end_jump)
        return None

    def visit_variable_expr(self, expr: VariableExpr) -> Any:
        self._named_variable(expr.name)
        return None

    def visit_assignment_expr(self, expr: AssignmentExpr) -> Any:
        self.current_line = expr.name.line
        self.compile_expr(expr.value)

        if (arg := self._resolve_local(self.state, expr.name)) is not None:
            self._emit_bytes(OpCode.OP_SET_LOCAL, arg, expr.name.line)
        elif (arg := self._resolve_upvalue(self.state, expr.name)) is not None:
            self._emit_bytes(OpCode.OP_SET_UPVALUE, arg, expr.name.line)
        else:
            arg = self._identifier_constant(expr.name.lexeme)
            self._emit_bytes(OpCode.OP_SET_GLOBAL, arg, expr.name.line)
        return None

    def visit_call_expr(self, expr: CallExpr) -> Any:
        self.current_line = expr.paren.line
        self.compile_expr(expr.callee)
        for arg in expr.arguments:
            self.compile_expr(arg)
        self._emit_bytes(OpCode.OP_CALL, len(expr.arguments), expr.paren.line)
        return None

    def visit_get_expr(self, expr: GetExpr) -> Any:
        self.current_line = expr.name.line
        self.compile_expr(expr.object)
        name_const = self._identifier_constant(expr.name.lexeme)
        self._emit_bytes(OpCode.OP_GET_PROPERTY, name_const, expr.name.line)
        return None

    def visit_set_expr(self, expr: SetExpr) -> Any:
        self.current_line = expr.name.line
        self.compile_expr(expr.object)
        self.compile_expr(expr.value)
        name_const = self._identifier_constant(expr.name.lexeme)
        self._emit_bytes(OpCode.OP_SET_PROPERTY, name_const, expr.name.line)
        return None

    def visit_this_expr(self, expr: ThisExpr) -> Any:
        self.current_line = expr.keyword.line
        if self.current_class is None:
            self._error(
                expr.keyword, "No se puede usar 'this' fuera de una clase."
            )
            return None
        self._named_variable(expr.keyword)
        return None

    def visit_super_expr(self, expr: SuperExpr) -> Any:
        self.current_line = expr.keyword.line
        if self.current_class is None:
            self._error(
                expr.keyword, "No se puede usar 'super' fuera de una clase."
            )
        elif not self.current_class.has_superclass:
            self._error(
                expr.keyword,
                "No se puede usar 'super' en una clase sin superclase.",
            )

        this_token = Token(
            token_type=TokenType.THIS,
            lexeme="this",
            literal=None,
            line=expr.keyword.line,
        )
        super_token = Token(
            token_type=TokenType.SUPER,
            lexeme="super",
            literal=None,
            line=expr.keyword.line,
        )
        self._named_variable(this_token)
        self._named_variable(super_token)
        method_const = self._identifier_constant(expr.method.lexeme)
        self._emit_bytes(OpCode.OP_GET_SUPER, method_const, expr.keyword.line)
        return None
