from typing import Any, Optional
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
from lox.syntax.token import Token, TokenType
from lox.errors import DiagnosticReporter, LoxRuntimeError, LoxReturnException
from lox.runtime.environment import Environment
from lox.runtime.callable import LoxCallable, LoxFunction, ClockFunction


class Interpreter(ExprVisitor, StmtVisitor):
    """Evaluador de sentencias y expresiones mediante recorrido del AST (Tree-Walk)."""

    def __init__(self, diagnostics: Optional[DiagnosticReporter] = None):
        self.diagnostics = diagnostics
        self.globals: Environment = Environment()
        self.environment: Environment = self.globals
        # Mapeo de identidad de nodo AST (id(expr)) a su profundidad estática
        self.locals: dict[int, int] = {}

        # Definir funciones nativas estándar
        self.globals.define("clock", ClockFunction())

    def resolve(self, expr: Expr, depth: int) -> None:
        """Almacena la distancia léxica resuelta por el Resolver para la expresión dada."""
        self.locals[id(expr)] = depth

    def interpret(self, target: list[Stmt] | Stmt | Expr, print_result: Optional[bool] = None) -> Any:
        """Punto de entrada para ejecutar sentencias o evaluar expresiones.

        Captura errores de runtime y los reporta a través del DiagnosticReporter.
        """
        try:
            if isinstance(target, list):
                last_value = None
                for statement in target:
                    last_value = self.execute(statement)
                return last_value
            elif isinstance(target, Stmt):
                return self.execute(target)
            else:
                value = self.evaluate(target)
                if print_result:
                    print(self.stringify(value))
                return value
        except LoxReturnException:
            error = LoxRuntimeError("No se puede retornar desde código de nivel superior.")
            if self.diagnostics:
                self.diagnostics.report_runtime_error(error)
            else:
                raise error
            return None
        except LoxRuntimeError as error:
            if self.diagnostics:
                self.diagnostics.report_runtime_error(error)
            else:
                raise
            return None

    def evaluate(self, expr: Expr) -> Any:
        """Evalúa un nodo de expresión ejecutando su método accept con este visitor."""
        return expr.accept(self)

    def execute(self, stmt: Stmt) -> Any:
        """Ejecuta un nodo de sentencia ejecutando su método accept con este visitor."""
        return stmt.accept(self)

    def execute_block(self, statements: list[Stmt], environment: Environment) -> None:
        """Ejecuta una lista de sentencias dentro del contexto de un nuevo entorno de variables."""
        previous = self.environment
        try:
            self.environment = environment
            for statement in statements:
                self.execute(statement)
        finally:
            self.environment = previous

    # ---------- Nodos de Sentencia (Stmt) ---------- #

    def visit_expression_stmt(self, stmt: ExpressionStmt) -> Any:
        """Evalúa la expresión de la sentencia y retorna su valor."""
        return self.evaluate(stmt.expression)

    def visit_print_stmt(self, stmt: PrintStmt) -> Any:
        """Evalúa la expresión e imprime su representación en consola."""
        value = self.evaluate(stmt.expression)
        print(self.stringify(value))
        return None

    def visit_var_decl(self, stmt: VarDecl) -> Any:
        """Declara una variable en el entorno actual, inicializándola si corresponde."""
        value = None
        if stmt.initializer is not None:
            value = self.evaluate(stmt.initializer)

        self.environment.define(stmt.name.lexeme, value)
        return None

    def visit_block_stmt(self, stmt: BlockStmt) -> Any:
        """Ejecuta un bloque delimitado por llaves en un nuevo ámbito léxico."""
        self.execute_block(stmt.statements, Environment(enclosing=self.environment))
        return None

    def visit_if_stmt(self, stmt: IfStmt) -> Any:
        """Ejecuta condicionalmente la rama then o else según la veracidad de la condición."""
        if self._is_truthy(self.evaluate(stmt.condition)):
            return self.execute(stmt.then_branch)
        elif stmt.else_branch is not None:
            return self.execute(stmt.else_branch)
        return None

    def visit_while_stmt(self, stmt: WhileStmt) -> Any:
        """Ejecuta repetidamente el cuerpo del bucle mientras la condición sea verdadera."""
        while self._is_truthy(self.evaluate(stmt.condition)):
            self.execute(stmt.body)
        return None

    def visit_fun_decl(self, stmt: FunDecl) -> Any:
        """Declara una función vinculando su cuerpo con el entorno léxico actual (closure)."""
        function = LoxFunction(declaration=stmt, closure=self.environment)
        self.environment.define(stmt.name.lexeme, function)
        return None

    def visit_return_stmt(self, stmt: ReturnStmt) -> Any:
        """Desenrolla el stack mediante LoxReturnException con el valor devuelto."""
        value = None
        if stmt.value is not None:
            value = self.evaluate(stmt.value)

        raise LoxReturnException(value)

    # ---------- Nodos de Expresión (Expr) ---------- #

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

    def visit_logical_expr(self, expr: LogicalExpr) -> Any:
        """Evalúa expresiones lógicas con cortocircuito ('and' y 'or'). Retorna el operando real."""
        left = self.evaluate(expr.left)

        if expr.operator.token_type == TokenType.OR:
            if self._is_truthy(left):
                return left
        else:  # TokenType.AND
            if not self._is_truthy(left):
                return left

        return self.evaluate(expr.right)

    def visit_call_expr(self, expr: CallExpr) -> Any:
        """Evalúa una llamada a función verificando aridad y condición de invocabilidad."""
        callee = self.evaluate(expr.callee)

        arguments: list[Any] = []
        for argument in expr.arguments:
            arguments.append(self.evaluate(argument))

        if not isinstance(callee, LoxCallable):
            raise LoxRuntimeError(
                "Solo se pueden invocar funciones y clases.",
                token=expr.paren,
            )

        function: LoxCallable = callee
        if len(arguments) != function.arity():
            raise LoxRuntimeError(
                f"Se esperaban {function.arity()} argumentos pero se obtuvieron {len(arguments)}.",
                token=expr.paren,
            )

        return function.call(self, arguments)

    def visit_variable_expr(self, expr: VariableExpr) -> Any:
        """Obtiene el valor de una variable utilizando la distancia léxica si fue resuelta localmente."""
        return self._look_up_variable(expr.name, expr)

    def _look_up_variable(self, name: Token, expr: Expr) -> Any:
        distance = self.locals.get(id(expr))
        if distance is not None:
            return self.environment.get_at(distance, name.lexeme)
        return self.globals.get(name)

    def visit_assignment_expr(self, expr: AssignmentExpr) -> Any:
        """Evalúa el valor a asignar y actualiza la variable en la distancia léxica correspondiente."""
        value = self.evaluate(expr.value)
        distance = self.locals.get(id(expr))
        if distance is not None:
            self.environment.assign_at(distance, expr.name, value)
        else:
            self.globals.assign(expr.name, value)
        return value

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
