from enum import Enum, auto
from typing import Any, Optional
from lox.syntax.token import Token, TokenType
from lox.syntax.ast import (
    Expr,
    ExprVisitor,
    BinaryExpr,
    UnaryExpr,
    GroupingExpr,
    LiteralExpr,
    VariableExpr,
    AssignmentExpr,
    LogicalExpr,
    CallExpr,
    Stmt,
    StmtVisitor,
    ExpressionStmt,
    PrintStmt,
    VarDecl,
    BlockStmt,
    IfStmt,
    WhileStmt,
    FunDecl,
    ReturnStmt,
)
from lox.errors import DiagnosticReporter


class FunctionType(Enum):
    NONE = auto()
    FUNCTION = auto()


class Resolver(ExprVisitor, StmtVisitor):
    """Analizador semántico que resuelve estáticamente las referencias de variables locales.

    Calcula la distancia léxica (número de ámbitos hacia arriba) para cada acceso o asignación
    a variables locales, y detecta errores semánticos como inicializaciones recursivas o return fuera de funciones.
    """

    def __init__(self, interpreter: Any, diagnostics: Optional[DiagnosticReporter] = None):
        self.interpreter = interpreter
        self.diagnostics = diagnostics
        self.scopes: list[dict[str, bool]] = []
        self.current_function: FunctionType = FunctionType.NONE

    def resolve(self, target: list[Stmt] | Stmt | Expr | None) -> None:
        """Punto de entrada polimórfico para recorrer y resolver sentencias o expresiones."""
        if target is None:
            return

        if isinstance(target, list):
            for statement in target:
                self.resolve(statement)
        else:
            target.accept(self)

    def _resolve_function(self, function: FunDecl, function_type: FunctionType) -> None:
        enclosing_function = self.current_function
        self.current_function = function_type

        self._begin_scope()
        for param in function.params:
            self._declare(param)
            self._define(param)
        self.resolve(function.body)
        self._end_scope()

        self.current_function = enclosing_function

    def _begin_scope(self) -> None:
        self.scopes.append({})

    def _end_scope(self) -> None:
        self.scopes.pop()

    def _declare(self, name: Token) -> None:
        if not self.scopes:
            return

        scope = self.scopes[-1]
        if name.lexeme in scope:
            self._error(name, f"Ya existe una variable con el nombre '{name.lexeme}' en este ámbito.")

        scope[name.lexeme] = False

    def _define(self, name: Token) -> None:
        if not self.scopes:
            return
        self.scopes[-1][name.lexeme] = True

    def _resolve_local(self, expr: Expr, name: Token) -> None:
        for i in range(len(self.scopes) - 1, -1, -1):
            if name.lexeme in self.scopes[i]:
                self.interpreter.resolve(expr, len(self.scopes) - 1 - i)
                return

    def _error(self, token: Token, message: str) -> None:
        if token.token_type == TokenType.EOF:
            where = " al final del archivo"
        else:
            where = f" en '{token.lexeme}' (columna {token.column})"

        if self.diagnostics:
            self.diagnostics.report_error(token.line, where, message)

    # ---------- Nodos de Sentencia (Stmt) ---------- #

    def visit_block_stmt(self, stmt: BlockStmt) -> Any:
        self._begin_scope()
        self.resolve(stmt.statements)
        self._end_scope()
        return None

    def visit_var_decl(self, stmt: VarDecl) -> Any:
        self._declare(stmt.name)
        if stmt.initializer is not None:
            self.resolve(stmt.initializer)
        self._define(stmt.name)
        return None

    def visit_fun_decl(self, stmt: FunDecl) -> Any:
        self._declare(stmt.name)
        self._define(stmt.name)
        self._resolve_function(stmt, FunctionType.FUNCTION)
        return None

    def visit_expression_stmt(self, stmt: ExpressionStmt) -> Any:
        self.resolve(stmt.expression)
        return None

    def visit_if_stmt(self, stmt: IfStmt) -> Any:
        self.resolve(stmt.condition)
        self.resolve(stmt.then_branch)
        if stmt.else_branch is not None:
            self.resolve(stmt.else_branch)
        return None

    def visit_print_stmt(self, stmt: PrintStmt) -> Any:
        self.resolve(stmt.expression)
        return None

    def visit_return_stmt(self, stmt: ReturnStmt) -> Any:
        if self.current_function == FunctionType.NONE:
            self._error(stmt.keyword, "No se puede retornar desde código de nivel superior.")

        if stmt.value is not None:
            self.resolve(stmt.value)
        return None

    def visit_while_stmt(self, stmt: WhileStmt) -> Any:
        self.resolve(stmt.condition)
        self.resolve(stmt.body)
        return None

    # ---------- Nodos de Expresión (Expr) ---------- #

    def visit_variable_expr(self, expr: VariableExpr) -> Any:
        if self.scopes and self.scopes[-1].get(expr.name.lexeme) is False:
            self._error(expr.name, f"No se puede leer la variable local '{expr.name.lexeme}' en su propio inicializador.")

        self._resolve_local(expr, expr.name)
        return None

    def visit_assignment_expr(self, expr: AssignmentExpr) -> Any:
        self.resolve(expr.value)
        self._resolve_local(expr, expr.name)
        return None

    def visit_binary_expr(self, expr: BinaryExpr) -> Any:
        self.resolve(expr.left)
        self.resolve(expr.right)
        return None

    def visit_call_expr(self, expr: CallExpr) -> Any:
        self.resolve(expr.callee)
        for argument in expr.arguments:
            self.resolve(argument)
        return None

    def visit_grouping_expr(self, expr: GroupingExpr) -> Any:
        self.resolve(expr.expression)
        return None

    def visit_literal_expr(self, expr: LiteralExpr) -> Any:
        return None

    def visit_logical_expr(self, expr: LogicalExpr) -> Any:
        self.resolve(expr.left)
        self.resolve(expr.right)
        return None

    def visit_unary_expr(self, expr: UnaryExpr) -> Any:
        self.resolve(expr.right)
        return None
