from typing import Any, Optional
from lox.syntax.ast import (
    Expr,
    ExprVisitor,
    BinaryExpr,
    UnaryExpr,
    GroupingExpr,
    LiteralExpr,
)
from lox.syntax.token import Token, TokenType
from lox.errors import DiagnosticReporter, LoxRuntimeError


class Interpreter(ExprVisitor):
    """Evaluador de expresiones mediante recorrido del Árbol de Sintaxis Abstracta (AST)."""

    def __init__(self, diagnostics: Optional[DiagnosticReporter] = None):
        self.diagnostics = diagnostics

    def interpret(self, expr: Expr, print_result: bool = True) -> Any:
        """Evalúa una expresión y opcionalmente imprime su representación canónica.

        Captura errores de runtime y los reporta a través del DiagnosticReporter.
        """
        try:
            value = self.evaluate(expr)
            if print_result:
                print(self.stringify(value))
            return value
        except LoxRuntimeError as error:
            if self.diagnostics:
                self.diagnostics.report_runtime_error(error)
            else:
                raise
            return None

    def evaluate(self, expr: Expr) -> Any:
        """Evalúa un nodo de expresión ejecutando su método accept con este visitor."""
        return expr.accept(self)

    # ---------- Nodos de Expresión ---------- #

    def visit_literal_expr(self, expr: LiteralExpr) -> Any:
        """Retorna el valor literal directo."""
        return expr.value

    def visit_grouping_expr(self, expr: GroupingExpr) -> Any:
        """Evalúa la expresión contenida dentro de los paréntesis."""
        return self.evaluate(expr.expression)

    def visit_unary_expr(self, expr: UnaryExpr) -> Any:
        """Evalúa operaciones unarias: negación numérica (-) y negación lógica (!)."""
        right = self.evaluate(expr.right)

        match expr.operator.token_type:
            case TokenType.MINUS:
                self._check_number_operand(expr.operator, right)
                return -float(right)
            case TokenType.BANG:
                return not self._is_truthy(right)
            case _:
                raise LoxRuntimeError(
                    f"Operador unario no soportado: '{expr.operator.lexeme}'.",
                    token=expr.operator,
                )

    def visit_binary_expr(self, expr: BinaryExpr) -> Any:
        """Evalúa operaciones binarias aritméticas, lógicas y de comparación."""
        left = self.evaluate(expr.left)
        right = self.evaluate(expr.right)

        match expr.operator.token_type:
            # Aritmética
            case TokenType.MINUS:
                self._check_number_operands(expr.operator, left, right)
                return float(left) - float(right)
            case TokenType.SLASH:
                self._check_number_operands(expr.operator, left, right)
                if float(right) == 0.0:
                    raise LoxRuntimeError("División por cero.", token=expr.operator)
                return float(left) / float(right)
            case TokenType.STAR:
                self._check_number_operands(expr.operator, left, right)
                return float(left) * float(right)
            case TokenType.PERCENT:
                self._check_number_operands(expr.operator, left, right)
                if float(right) == 0.0:
                    raise LoxRuntimeError("Módulo por cero.", token=expr.operator)
                return float(left) % float(right)
            case TokenType.PLUS:
                # Sobrecarga: (número + número) o (cadena + cadena)
                if self._is_number(left) and self._is_number(right):
                    return float(left) + float(right)
                if isinstance(left, str) and isinstance(right, str):
                    return left + right
                raise LoxRuntimeError(
                    "Los operandos deben ser dos números o dos cadenas de texto.",
                    token=expr.operator,
                )

            # Comparaciones relacionales
            case TokenType.GREATER:
                self._check_number_operands(expr.operator, left, right)
                return float(left) > float(right)
            case TokenType.GREATER_EQUAL:
                self._check_number_operands(expr.operator, left, right)
                return float(left) >= float(right)
            case TokenType.LESS:
                self._check_number_operands(expr.operator, left, right)
                return float(left) < float(right)
            case TokenType.LESS_EQUAL:
                self._check_number_operands(expr.operator, left, right)
                return float(left) <= float(right)

            # Comparaciones de igualdad
            case TokenType.BANG_EQUAL:
                return not self._is_equal(left, right)
            case TokenType.EQUAL_EQUAL:
                return self._is_equal(left, right)

            case _:
                raise LoxRuntimeError(
                    f"Operador binario no soportado: '{expr.operator.lexeme}'.",
                    token=expr.operator,
                )

    # ---------- Semántica de Runtime ---------- #

    def _is_truthy(self, value: Any) -> bool:
        """Determina la veracidad según las reglas de Lox:
        Únicamente 'false' y 'nil' son falsos. Todo lo demás es verdadero.
        """
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        return True

    def _is_equal(self, a: Any, b: Any) -> bool:
        """Compara igualdad estricta en Lox evitando coerción implícita de Python (ej: 0 == False)."""
        if a is None and b is None:
            return True
        if a is None or b is None:
            return False

        # Si alguno es booleano, ambos deben ser booleanos exactamente
        if isinstance(a, bool) or isinstance(b, bool):
            if not (isinstance(a, bool) and isinstance(b, bool)):
                return False
            return a is b

        # Comparación numérica (soporta float e int)
        if self._is_number(a) and self._is_number(b):
            return float(a) == float(b)

        return a == b

    def _is_number(self, value: Any) -> bool:
        """Verifica si un valor es numérico en Lox (excluyendo booleanos de Python)."""
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    def _check_number_operand(self, operator: Token, operand: Any) -> None:
        """Valida que un operando unario sea numérico."""
        if self._is_number(operand):
            return
        raise LoxRuntimeError("El operando debe ser un número.", token=operator)

    def _check_number_operands(self, operator: Token, left: Any, right: Any) -> None:
        """Valida que ambos operandos binarios sean numéricos."""
        if self._is_number(left) and self._is_number(right):
            return
        raise LoxRuntimeError("Los operandos deben ser números.", token=operator)

    def stringify(self, value: Any) -> str:
        """Convierte un valor de runtime de Lox a su representación canónica en texto."""
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
