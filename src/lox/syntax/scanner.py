from typing import Optional, Any
from lox.syntax.token import Token, TokenType, KEYWORDS
from lox.errors import DiagnosticReporter, LoxLexicalError


class Scanner:
    """Analizador léxico (Scanner) para el lenguaje Lox.
    
    Convierte el código fuente en una secuencia ordenada de Tokens,
    rastreando información de línea y columna y recolectando diagnósticos de error.
    """

    def __init__(self, source: str, diagnostics: Optional[DiagnosticReporter] = None):
        self.source = source
        self.diagnostics = diagnostics
        self.tokens: list[Token] = []

        self.start: int = 0
        self.current: int = 0
        self.line: int = 1
        self.column: int = 1
        self.start_column: int = 1

    def scan_tokens(self) -> list[Token]:
        """Escanea todo el código fuente y retorna la lista de tokens finalizada con EOF."""
        while not self._is_at_end():
            self.start = self.current
            self.start_column = self.column
            self.scan_token()

        # Añadimos el token EOF al final
        self.tokens.append(
            Token(
                token_type=TokenType.EOF,
                lexeme="",
                literal=None,
                line=self.line,
                column=self.column,
            )
        )
        return self.tokens

    def scan_token(self) -> None:
        """Escanea un único token o secuencia de caracteres."""
        c = self._advance()

        match c:
            # Tokens de un solo carácter
            case "(":
                self._add_token(TokenType.LEFT_PAREN)
            case ")":
                self._add_token(TokenType.RIGHT_PAREN)
            case "{":
                self._add_token(TokenType.LEFT_BRACE)
            case "}":
                self._add_token(TokenType.RIGHT_BRACE)
            case ",":
                self._add_token(TokenType.COMMA)
            case ".":
                self._add_token(TokenType.DOT)
            case "-":
                self._add_token(TokenType.MINUS)
            case "+":
                self._add_token(TokenType.PLUS)
            case ";":
                self._add_token(TokenType.SEMICOLON)
            case "*":
                self._add_token(TokenType.STAR)
            case "%":
                self._add_token(TokenType.PERCENT)

            # Operadores de uno o dos caracteres
            case "!":
                token_type = TokenType.BANG_EQUAL if self._match("=") else TokenType.BANG
                self._add_token(token_type)
            case "=":
                token_type = TokenType.EQUAL_EQUAL if self._match("=") else TokenType.EQUAL
                self._add_token(token_type)
            case "<":
                token_type = TokenType.LESS_EQUAL if self._match("=") else TokenType.LESS
                self._add_token(token_type)
            case ">":
                token_type = TokenType.GREATER_EQUAL if self._match("=") else TokenType.GREATER
                self._add_token(token_type)

            # Barra diagonal o comentario de línea
            case "/":
                if self._match("/"):
                    # Comentario de una línea: ignorar hasta el fin de línea o EOF
                    while self._peek() != "\n" and not self._is_at_end():
                        self._advance()
                else:
                    self._add_token(TokenType.SLASH)

            # Espacios en blanco
            case " " | "\r" | "\t":
                pass
            case "\n":
                self.line += 1
                self.column = 1

            # Literales de texto (comillas dobles o simples)
            case '"' | "'":
                self._string(c)

            # Literales numéricos
            case _ if c.isdigit():
                self._number()

            # Identificadores y palabras reservadas
            case _ if c.isalpha() or c == "_":
                self._identifier()

            # Carácter no reconocido
            case _:
                self._error(f"Carácter inesperado '{c}'")

    # ---------- Manejo de Literales ---------- #

    def _string(self, quote_char: str) -> None:
        """Escanea un literal de texto, procesando secuencias de escape y multilíneas."""
        value_chars: list[str] = []

        while not self._is_at_end() and self._peek() != quote_char:
            ch = self._peek()

            if ch == "\n":
                self.line += 1
                self.column = 0  # _advance incrementará a 1

            if ch == "\\":
                # Carácter de escape
                self._advance()
                if self._is_at_end():
                    break
                escaped = self._advance()
                match escaped:
                    case "n":
                        value_chars.append("\n")
                    case "t":
                        value_chars.append("\t")
                    case "r":
                        value_chars.append("\r")
                    case "\\":
                        value_chars.append("\\")
                    case '"':
                        value_chars.append('"')
                    case "'":
                        value_chars.append("'")
                    case _:
                        value_chars.append(escaped)
                continue

            value_chars.append(self._advance())

        if self._is_at_end():
            self._error(f"Cadena de texto sin terminar: '{self.source[self.start:self.current]}'")
            return

        # Consumir la comilla de cierre
        self._advance()

        literal_value = "".join(value_chars)
        self._add_token(TokenType.STRING, literal=literal_value)

    def _number(self) -> None:
        """Escanea un número entero o de punto flotante."""
        while self._peek().isdigit():
            self._advance()

        # Parte decimal opcional: requiere un punto seguido de al menos un dígito
        if self._peek() == "." and self._peek_next().isdigit():
            self._advance()  # Consumir el '.'
            while self._peek().isdigit():
                self._advance()

        lexeme = self.source[self.start : self.current]
        try:
            num_val = float(lexeme) if "." in lexeme else float(int(lexeme))
            self._add_token(TokenType.NUMBER, literal=num_val)
        except ValueError:
            self._error(f"Formato numérico inválido: '{lexeme}'")

    def _identifier(self) -> None:
        """Escanea un identificador de usuario o palabra clave reservada."""
        while self._peek().isalnum() or self._peek() == "_":
            self._advance()

        lexeme = self.source[self.start : self.current]
        token_type = KEYWORDS.get(lexeme, TokenType.IDENTIFIER)
        self._add_token(token_type)

    # ---------- Funciones Auxiliares ---------- #

    def _is_at_end(self) -> bool:
        return self.current >= len(self.source)

    def _advance(self) -> str:
        char = self.source[self.current]
        self.current += 1
        self.column += 1
        return char

    def _match(self, expected: str) -> bool:
        if self._is_at_end():
            return False
        if self.source[self.current] != expected:
            return False
        self.current += 1
        self.column += 1
        return True

    def _peek(self) -> str:
        if self._is_at_end():
            return "\0"
        return self.source[self.current]

    def _peek_next(self) -> str:
        if self.current + 1 >= len(self.source):
            return "\0"
        return self.source[self.current + 1]

    def _add_token(self, token_type: TokenType, literal: Any = None) -> None:
        lexeme = self.source[self.start : self.current]
        self.tokens.append(
            Token(
                token_type=token_type,
                lexeme=lexeme,
                literal=literal,
                line=self.line,
                column=self.start_column,
            )
        )

    def _error(self, message: str) -> None:
        if self.diagnostics:
            self.diagnostics.report_error(self.line, f" en columna {self.start_column}", message)
