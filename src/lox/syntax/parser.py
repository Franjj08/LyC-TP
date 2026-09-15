from typing import Optional
from lox.syntax.token import Token, TokenType
from lox.syntax.ast import (
    Expr,
    BinaryExpr,
    UnaryExpr,
    GroupingExpr,
    LiteralExpr,
)
from lox.errors import DiagnosticReporter, LoxSyntaxError


class Parser:
    """Parser por Descenso Recursivo para expresiones del lenguaje Lox."""

    def __init__(self, tokens: list[Token], diagnostics: Optional[DiagnosticReporter] = None):
        self.tokens = tokens
        self.diagnostics = diagnostics
        self.current: int = 0

    def parse(self) -> Optional[Expr]:
        """Parsea una expresión completa. Retorna None si ocurrió un error sintáctico."""
        try:
            if self._is_at_end():
                return None

            # Permitimos opcionalmente 'print <expr>' para compatibilidad antes de la Fase 4
            if self._match(TokenType.PRINT):
                expr = self._expression()
            else:
                expr = self._expression()

            # Permitimos punto y coma opcional al final de la expresión
            if self._match(TokenType.SEMICOLON):
                pass

            if not self._is_at_end():
                raise self._error(self._peek(), "Token inesperado después de la expresión.")

            return expr
        except LoxSyntaxError:
            self._synchronize()
            return None

    # ---------- Reglas de Producción de Expresiones ---------- #

    def _expression(self) -> Expr:
        """expression -> equality"""
        return self._equality()

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
        """primary -> NUMBER | STRING | "true" | "false" | "nil" | "(" expression ")" """
        if self._match(TokenType.FALSE):
            return LiteralExpr(False)
        if self._match(TokenType.TRUE):
            return LiteralExpr(True)
        if self._match(TokenType.NIL):
            return LiteralExpr(None)

        if self._match(TokenType.NUMBER, TokenType.STRING):
            return LiteralExpr(self._previous().literal)

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
