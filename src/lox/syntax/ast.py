from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, TypeVar
from lox.syntax.token import Token

T = TypeVar("T")


class Expr(ABC):
    """Clase base abstracta para todos los nodos del Árbol de Sintaxis Abstracta (AST)."""

    @abstractmethod
    def accept(self, visitor: "ExprVisitor[T]") -> T:
        """Permite recorrer el nodo mediante el patrón Visitor."""
        pass


class ExprVisitor(ABC, list[T] if False else object):
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

    def _parenthesize(self, name: str, *exprs: Expr) -> str:
        parts = [name]
        for expr in exprs:
            parts.append(expr.accept(self))
        return f"({' '.join(parts)})"
