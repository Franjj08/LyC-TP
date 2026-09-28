from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional, TypeVar
from lox.syntax.token import Token

T = TypeVar("T")


class Expr(ABC):

    @abstractmethod
    def accept(self, visitor: "ExprVisitor[T]") -> T:
        pass


class ExprVisitor(ABC):

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

    left: Expr
    operator: Token
    right: Expr

    def accept(self, visitor: ExprVisitor) -> Any:
        return visitor.visit_binary_expr(self)

    def __repr__(self) -> str:
        return f"({self.operator.lexeme} {self.left} {self.right})"


@dataclass(frozen=True)
class GroupingExpr(Expr):

    expression: Expr

    def accept(self, visitor: ExprVisitor) -> Any:
        return visitor.visit_grouping_expr(self)

    def __repr__(self) -> str:
        return f"(group {self.expression})"


@dataclass(frozen=True)
class LiteralExpr(Expr):

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

    operator: Token
    right: Expr

    def accept(self, visitor: ExprVisitor) -> Any:
        return visitor.visit_unary_expr(self)

    def __repr__(self) -> str:
        return f"({self.operator.lexeme} {self.right})"


@dataclass(frozen=True)
class VariableExpr(Expr):

    name: Token

    def accept(self, visitor: ExprVisitor) -> Any:
        return visitor.visit_variable_expr(self)

    def __repr__(self) -> str:
        return self.name.lexeme


@dataclass(frozen=True)
class AssignmentExpr(Expr):

    name: Token
    value: Expr

    def accept(self, visitor: ExprVisitor) -> Any:
        return visitor.visit_assignment_expr(self)

    def __repr__(self) -> str:
        return f"(= {self.name.lexeme} {self.value})"


@dataclass(frozen=True)
class LogicalExpr(Expr):

    left: Expr
    operator: Token
    right: Expr

    def accept(self, visitor: ExprVisitor) -> Any:
        return visitor.visit_logical_expr(self)

    def __repr__(self) -> str:
        return f"({self.operator.lexeme} {self.left} {self.right})"


@dataclass(frozen=True)
class CallExpr(Expr):

    callee: Expr
    paren: Token
    arguments: list[Expr]

    def accept(self, visitor: ExprVisitor) -> Any:
        return visitor.visit_call_expr(self)

    def __repr__(self) -> str:
        args_str = ", ".join(repr(a) for a in self.arguments)
        return f"{self.callee}({args_str})"


class Stmt(ABC):

    @abstractmethod
    def accept(self, visitor: "StmtVisitor[T]") -> T:
        pass


class StmtVisitor(ABC):

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

    expression: Expr

    def accept(self, visitor: StmtVisitor) -> Any:
        return visitor.visit_expression_stmt(self)


@dataclass(frozen=True)
class PrintStmt(Stmt):

    expression: Expr

    def accept(self, visitor: StmtVisitor) -> Any:
        return visitor.visit_print_stmt(self)


@dataclass(frozen=True)
class VarDecl(Stmt):

    name: Token
    initializer: Optional[Expr] = None

    def accept(self, visitor: StmtVisitor) -> Any:
        return visitor.visit_var_decl(self)


@dataclass(frozen=True)
class BlockStmt(Stmt):

    statements: list[Stmt]

    def accept(self, visitor: StmtVisitor) -> Any:
        return visitor.visit_block_stmt(self)


@dataclass(frozen=True)
class IfStmt(Stmt):

    condition: Expr
    then_branch: Stmt
    else_branch: Optional[Stmt] = None

    def accept(self, visitor: StmtVisitor) -> Any:
        return visitor.visit_if_stmt(self)


@dataclass(frozen=True)
class WhileStmt(Stmt):

    condition: Expr
    body: Stmt

    def accept(self, visitor: StmtVisitor) -> Any:
        return visitor.visit_while_stmt(self)


@dataclass(frozen=True)
class FunDecl(Stmt):

    name: Token
    params: list[Token]
    body: list[Stmt]

    def accept(self, visitor: StmtVisitor) -> Any:
        return visitor.visit_fun_decl(self)


@dataclass(frozen=True)
class ReturnStmt(Stmt):

    keyword: Token
    value: Optional[Expr] = None

    def accept(self, visitor: StmtVisitor) -> Any:
        return visitor.visit_return_stmt(self)


class AstPrinter(ExprVisitor):

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
