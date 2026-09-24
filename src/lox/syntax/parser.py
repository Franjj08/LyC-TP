from typing import Optional
from lox.syntax.token import Token, TokenType
from lox.syntax.ast import (
    Expr,
    BinaryExpr,
    UnaryExpr,
    GroupingExpr,
    LiteralExpr,
    VariableExpr,
    AssignmentExpr,
    Stmt,
    ExpressionStmt,
    PrintStmt,
    VarDecl,
    BlockStmt,
)
from lox.errors import DiagnosticReporter, LoxSyntaxError


class Parser:
    """Parser por Descenso Recursivo para sentencias y expresiones de Lox."""

    def __init__(self, tokens: list[Token], diagnostics: Optional[DiagnosticReporter] = None):
        self.tokens = tokens
        self.diagnostics = diagnostics
        self.current: int = 0

    def parse(self) -> list[Stmt]:
        """Parsea una secuencia de declaraciones y sentencias del programa."""
        statements: list[Stmt] = []
        while not self._is_at_end():
            decl = self._declaration()
            if decl is not None:
                statements.append(decl)
        return statements

    def parse_expression(self) -> Optional[Expr]:
        """Parsea una única expresión aislada (utilizado en tests y evaluación directa)."""
        try:
            if self._is_at_end():
                return None
            expr = self._expression()
            if self._match(TokenType.SEMICOLON):
                pass
            if not self._is_at_end():
                raise self._error(self._peek(), "Token inesperado después de la expresión.")
            return expr
        except LoxSyntaxError:
            self._synchronize()
            return None

    # ---------- Declaraciones y Sentencias ---------- #

    def _declaration(self) -> Optional[Stmt]:
        """declaration -> varDeclaration | statement"""
        try:
            if self._match(TokenType.VAR):
                return self._var_declaration()
            return self._statement()
        except LoxSyntaxError:
            self._synchronize()
            return None

    def _var_declaration(self) -> Stmt:
        """varDeclaration -> "var" IDENTIFIER ( "=" expression )? ";" """
        name = self._consume(TokenType.IDENTIFIER, "Se esperaba el nombre de la variable.")
        initializer: Optional[Expr] = None

        if self._match(TokenType.EQUAL):
            initializer = self._expression()

        self._consume(TokenType.SEMICOLON, "Se esperaba ';' después de la declaración de variable.")
        return VarDecl(name=name, initializer=initializer)

    def _statement(self) -> Stmt:
        """statement -> printStmt | block | exprStmt"""
        if self._match(TokenType.PRINT):
            return self._print_statement()
        if self._match(TokenType.LEFT_BRACE):
            return BlockStmt(statements=self._block())
        return self._expression_statement()

    def _print_statement(self) -> Stmt:
        """printStmt -> "print" expression ";" """
        value = self._expression()
        self._consume(TokenType.SEMICOLON, "Se esperaba ';' después del valor a imprimir.")
        return PrintStmt(expression=value)

    def _block(self) -> list[Stmt]:
        """block -> "{" declaration* "}" """
        statements: list[Stmt] = []

        while not self._check(TokenType.RIGHT_BRACE) and not self._is_at_end():
            decl = self._declaration()
            if decl is not None:
                statements.append(decl)

        self._consume(TokenType.RIGHT_BRACE, "Se esperaba '}' después del bloque.")
        return statements

    def _expression_statement(self) -> Stmt:
        """exprStmt -> expression ";" """
        expr = self._expression()
        if not self._check(TokenType.SEMICOLON) and self._is_at_end():
            # Permitimos omitir ';' al final del input en modo interactivo/expresión única
            return ExpressionStmt(expression=expr)
        self._consume(TokenType.SEMICOLON, "Se esperaba ';' después de la expresión.")
        return ExpressionStmt(expression=expr)

    # ---------- Reglas de Producción de Expresiones ---------- #

    def _expression(self) -> Expr:
        """expression -> assignment"""
        return self._assignment()

    def _assignment(self) -> Expr:
        """assignment -> IDENTIFIER "=" assignment | equality"""
        expr = self._equality()

        if self._match(TokenType.EQUAL):
            equals = self._previous()
            value = self._assignment()

            if isinstance(expr, VariableExpr):
                name = expr.name
                return AssignmentExpr(name=name, value=value)

            self._error(equals, "Objetivo de asignación inválido.")

        return expr

    def _equality(self) -> Expr:
        """equality -> comparison ( ( "!=" | "==" ) comparison )*"""
        expr = self._comparison()

        while self._match(TokenType.BANG_EQUAL, TokenType.EQUAL_EQUAL):
            operator = self._previous()
            right = self._comparison()
            expr = BinaryExpr(left=expr, operator=operator, right=right)

        return expr

    def _comparison(self) -> Expr:
        """comparison -> term ( ( ">" | ">=" | "<" | "<=" ) term )*"""
        expr = self._term()

        while self._match(
            TokenType.GREATER,
            TokenType.GREATER_EQUAL,
            TokenType.LESS,
            TokenType.LESS_EQUAL,
        ):
            operator = self._previous()
            right = self._term()
            expr = BinaryExpr(left=expr, operator=operator, right=right)

        return expr

    def _term(self) -> Expr:
        """term -> factor ( ( "-" | "+" ) factor )*"""
        expr = self._factor()

        while self._match(TokenType.MINUS, TokenType.PLUS):
            operator = self._previous()
            right = self._factor()
            expr = BinaryExpr(left=expr, operator=operator, right=right)

        return expr

    def _factor(self) -> Expr:
        """factor -> unary ( ( "/" | "*" | "%" ) unary )*"""
        expr = self._unary()

        while self._match(TokenType.SLASH, TokenType.STAR, TokenType.PERCENT):
            operator = self._previous()
            right = self._unary()
            expr = BinaryExpr(left=expr, operator=operator, right=right)

        return expr

    def _unary(self) -> Expr:
        """unary -> ( "!" | "-" ) unary | primary"""
        if self._match(TokenType.BANG, TokenType.MINUS):
            operator = self._previous()
            right = self._unary()
            return UnaryExpr(operator=operator, right=right)

        return self._primary()

    def _primary(self) -> Expr:
        """primary -> NUMBER | STRING | "true" | "false" | "nil" | "(" expression ")" | IDENTIFIER"""
        if self._match(TokenType.FALSE):
            return LiteralExpr(False)
        if self._match(TokenType.TRUE):
            return LiteralExpr(True)
        if self._match(TokenType.NIL):
            return LiteralExpr(None)

        if self._match(TokenType.NUMBER, TokenType.STRING):
            return LiteralExpr(self._previous().literal)

        if self._match(TokenType.IDENTIFIER):
            return VariableExpr(name=self._previous())

        if self._match(TokenType.LEFT_PAREN):
            expr = self._expression()
            self._consume(TokenType.RIGHT_PAREN, "Se esperaba ')' después de la expresión.")
            return GroupingExpr(expression=expr)

        raise self._error(self._peek(), f"Se esperaba una expresión válida, se obtuvo '{self._peek().lexeme}'.")

    # ---------- Navegación y Helpers ---------- #

    def _match(self, *types: TokenType) -> bool:
        """Comprueba si el token actual coincide con alguno de los tipos dados. Si coincide, lo consume."""
        for token_type in types:
            if self._check(token_type):
                self._advance()
                return True
        return False

    def _check(self, token_type: TokenType) -> bool:
        """Comprueba el tipo del token actual sin consumirlo."""
        if self._is_at_end():
            return False
        return self._peek().token_type == token_type

    def _advance(self) -> Token:
        """Consume el token actual y retorna el token consumido."""
        if not self._is_at_end():
            self.current += 1
        return self._previous()

    def _is_at_end(self) -> bool:
        """Retorna True si alcanzamos el final de la lista de tokens (EOF)."""
        return self._peek().token_type == TokenType.EOF

    def _peek(self) -> Token:
        """Retorna el token actual sin consumirlo."""
        return self.tokens[self.current]

    def _previous(self) -> Token:
        """Retorna el token inmediatamente anterior ya consumido."""
        return self.tokens[self.current - 1]

    def _consume(self, token_type: TokenType, message: str) -> Token:
        """Consume el token esperado o lanza un error sintáctico."""
        if self._check(token_type):
            return self._advance()
        raise self._error(self._peek(), message)

    def _error(self, token: Token, message: str) -> LoxSyntaxError:
        """Genera un error sintáctico y lo registra en el DiagnosticReporter."""
        if token.token_type == TokenType.EOF:
            where = " al final del archivo"
        else:
            where = f" en '{token.lexeme}' (columna {token.column})"

        if self.diagnostics:
            self.diagnostics.report_error(token.line, where, message)

        return LoxSyntaxError(message, line=token.line)

    def _synchronize(self) -> None:
        """Recuperación en Modo Pánico (Panic Mode): descarta tokens hasta el fin de sentencia o delimitador."""
        self._advance()

        while not self._is_at_end():
            if self._previous().token_type == TokenType.SEMICOLON:
                return

            if self._peek().token_type in (
                TokenType.CLASS,
                TokenType.FUN,
                TokenType.VAR,
                TokenType.FOR,
                TokenType.IF,
                TokenType.WHILE,
                TokenType.PRINT,
                TokenType.RETURN,
            ):
                return

            self._advance()
