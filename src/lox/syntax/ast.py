from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional, TypeVar
from lox.syntax.token import Token

T = TypeVar("T")


# =====================================================================
# Expresiones (Expr)
# =====================================================================


class Expr(ABC):
    """Clase base abstracta para todos los nodos de expresión del AST."""

    @abstractmethod
    def accept(self, visitor: "ExprVisitor[T]") -> T:
        """Permite recorrer el nodo mediante el patrón Visitor."""
        pass


class ExprVisitor(ABC):
    """Interfaz para visitar los distintos nodos de expresión."""

    @abstractmethod
    def visit_binary_expr(self, expr: "BinaryExpr") -> Any:
        pass

    @abstractmethod
    def visit_grouping_expr(self, expr: "GroupingExpr") -> Any:
        pass

    @abstractmethod
    def visit_literal_expr(self, expr: "LiteralExpr") -> Any:
        pass

    @abstractmethod
    def visit_unary_expr(self, expr: "UnaryExpr") -> Any:
        pass

    @abstractmethod
    def visit_variable_expr(self, expr: "VariableExpr") -> Any:
        pass

    @abstractmethod
    def visit_assignment_expr(self, expr: "AssignmentExpr") -> Any:
        pass

    @abstractmethod
    def visit_logical_expr(self, expr: "LogicalExpr") -> Any:
        pass

    @abstractmethod
    def visit_call_expr(self, expr: "CallExpr") -> Any:
        pass


@dataclass(frozen=True)
class BinaryExpr(Expr):
    """Representa una operación binaria: izquierda operador derecha."""

    left: Expr
    operator: Token
    right: Expr

    def accept(self, visitor: ExprVisitor) -> Any:
        return visitor.visit_binary_expr(self)

    def __repr__(self) -> str:
        return f"({self.operator.lexeme} {self.left} {self.right})"


@dataclass(frozen=True)
class GroupingExpr(Expr):
    """Representa una expresión envuelta entre paréntesis: ( expresión )."""

    expression: Expr

    def accept(self, visitor: ExprVisitor) -> Any:
        return visitor.visit_grouping_expr(self)

    def __repr__(self) -> str:
        return f"(group {self.expression})"


@dataclass(frozen=True)
class LiteralExpr(Expr):
    """Representa un valor literal: número, cadena, booleano o nil."""

    value: Any

    def accept(self, visitor: ExprVisitor) -> Any:
        return visitor.visit_literal_expr(self)

    def __repr__(self) -> str:
        if self.value is None:
            return "nil"
        if isinstance(self.value, bool):
            return "true" if self.value else "false"
        if isinstance(self.value, str):
            return f'"{self.value}"'
        return str(self.value)


@dataclass(frozen=True)
class UnaryExpr(Expr):
    """Representa una operación unaria prefija: operador derecha."""

    operator: Token
    right: Expr

    def accept(self, visitor: ExprVisitor) -> Any:
        return visitor.visit_unary_expr(self)

    def __repr__(self) -> str:
        return f"({self.operator.lexeme} {self.right})"


@dataclass(frozen=True)
class VariableExpr(Expr):
    """Representa el acceso al valor de una variable por su identificador."""

    name: Token

    def accept(self, visitor: ExprVisitor) -> Any:
        return visitor.visit_variable_expr(self)

    def __repr__(self) -> str:
        return self.name.lexeme


@dataclass(frozen=True)
class AssignmentExpr(Expr):
    """Representa la asignación de un valor a una variable: nombre = expresión."""

    name: Token
    value: Expr

    def accept(self, visitor: ExprVisitor) -> Any:
        return visitor.visit_assignment_expr(self)

    def __repr__(self) -> str:
        return f"(= {self.name.lexeme} {self.value})"


@dataclass(frozen=True)
class LogicalExpr(Expr):
    """Representa una operación lógica con cortocircuito: izquierda (and|or) derecha."""

    left: Expr
    operator: Token
    right: Expr

    def accept(self, visitor: ExprVisitor) -> Any:
        return visitor.visit_logical_expr(self)

    def __repr__(self) -> str:
        return f"({self.operator.lexeme} {self.left} {self.right})"


@dataclass(frozen=True)
class CallExpr(Expr):
    """Representa la invocación a una función o método: callee(argumentos)."""

    callee: Expr
    paren: Token
    arguments: list[Expr]

    def accept(self, visitor: ExprVisitor) -> Any:
        return visitor.visit_call_expr(self)

    def __repr__(self) -> str:
        args_str = ", ".join(repr(a) for a in self.arguments)
        return f"{self.callee}({args_str})"


# =====================================================================
# Sentencias (Stmt)
# =====================================================================


class Stmt(ABC):
    """Clase base abstracta para todos los nodos de sentencia del AST."""

    @abstractmethod
    def accept(self, visitor: "StmtVisitor[T]") -> T:
        """Permite recorrer la sentencia mediante el patrón Visitor."""
        pass


class StmtVisitor(ABC):
    """Interfaz para visitar los distintos nodos de sentencia."""

    @abstractmethod
    def visit_expression_stmt(self, stmt: "ExpressionStmt") -> Any:
        pass

    @abstractmethod
    def visit_print_stmt(self, stmt: "PrintStmt") -> Any:
        pass

    @abstractmethod
    def visit_var_decl(self, stmt: "VarDecl") -> Any:
        pass

    @abstractmethod
    def visit_block_stmt(self, stmt: "BlockStmt") -> Any:
        pass

    @abstractmethod
    def visit_if_stmt(self, stmt: "IfStmt") -> Any:
        pass

    @abstractmethod
    def visit_while_stmt(self, stmt: "WhileStmt") -> Any:
        pass

    @abstractmethod
    def visit_fun_decl(self, stmt: "FunDecl") -> Any:
        pass

    @abstractmethod
    def visit_return_stmt(self, stmt: "ReturnStmt") -> Any:
        pass


@dataclass(frozen=True)
class ExpressionStmt(Stmt):
    """Sentencia consistente en una única expresión evaluada por efecto de lado: expr;"""

    expression: Expr

    def accept(self, visitor: StmtVisitor) -> Any:
        return visitor.visit_expression_stmt(self)


@dataclass(frozen=True)
class PrintStmt(Stmt):
    """Sentencia de impresión por consola: print expr;"""

    expression: Expr

    def accept(self, visitor: StmtVisitor) -> Any:
        return visitor.visit_print_stmt(self)


@dataclass(frozen=True)
class VarDecl(Stmt):
    """Declaración de variable: var nombre = expr; o var nombre;"""

    name: Token
    initializer: Optional[Expr] = None

    def accept(self, visitor: StmtVisitor) -> Any:
        return visitor.visit_var_decl(self)


@dataclass(frozen=True)
class BlockStmt(Stmt):
    """Bloque de sentencias delimitado por llaves: { stmt1; stmt2; ... }"""

    statements: list[Stmt]

    def accept(self, visitor: StmtVisitor) -> Any:
        return visitor.visit_block_stmt(self)


@dataclass(frozen=True)
class IfStmt(Stmt):
    """Sentencia condicional: if (condición) sentencia [else sentencia]"""

    condition: Expr
    then_branch: Stmt
    else_branch: Optional[Stmt] = None

    def accept(self, visitor: StmtVisitor) -> Any:
        return visitor.visit_if_stmt(self)


@dataclass(frozen=True)
class WhileStmt(Stmt):
    """Sentencia de bucle mientras: while (condición) cuerpo"""

    condition: Expr
    body: Stmt

    def accept(self, visitor: StmtVisitor) -> Any:
        return visitor.visit_while_stmt(self)


@dataclass(frozen=True)
class FunDecl(Stmt):
    """Declaración de función: fun nombre(param1, param2) { cuerpo }"""

    name: Token
    params: list[Token]
    body: list[Stmt]

    def accept(self, visitor: StmtVisitor) -> Any:
        return visitor.visit_fun_decl(self)


@dataclass(frozen=True)
class ReturnStmt(Stmt):
    """Sentencia de retorno de función: return expr; o return;"""

    keyword: Token
    value: Optional[Expr] = None

    def accept(self, visitor: StmtVisitor) -> Any:
        return visitor.visit_return_stmt(self)


# =====================================================================
# Impresión del AST (AstPrinter)
# =====================================================================


class AstPrinter(ExprVisitor):
    """Imprime el AST de expresiones en formato de S-Expressions tipo Lisp."""

    def print(self, expr: Expr) -> str:
        return expr.accept(self)

    def visit_binary_expr(self, expr: BinaryExpr) -> str:
        return self._parenthesize(expr.operator.lexeme, expr.left, expr.right)

    def visit_grouping_expr(self, expr: GroupingExpr) -> str:
        return self._parenthesize("group", expr.expression)

    def visit_literal_expr(self, expr: LiteralExpr) -> str:
        if expr.value is None:
            return "nil"
        if isinstance(expr.value, bool):
            return "true" if expr.value else "false"
        if isinstance(expr.value, str):
            return f'"{expr.value}"'
        return str(expr.value)

    def visit_unary_expr(self, expr: UnaryExpr) -> str:
        return self._parenthesize(expr.operator.lexeme, expr.right)

    def visit_variable_expr(self, expr: VariableExpr) -> str:
        return expr.name.lexeme

    def visit_assignment_expr(self, expr: AssignmentExpr) -> str:
        return self._parenthesize(f"= {expr.name.lexeme}", expr.value)

    def visit_logical_expr(self, expr: LogicalExpr) -> str:
        return self._parenthesize(expr.operator.lexeme, expr.left, expr.right)

    def visit_call_expr(self, expr: CallExpr) -> str:
        return self._parenthesize(expr.callee.accept(self), *expr.arguments)

    def _parenthesize(self, name: str, *exprs: Expr) -> str:
        parts = [name]
        for expr in exprs:
            parts.append(expr.accept(self))
        return f"({' '.join(parts)})"
