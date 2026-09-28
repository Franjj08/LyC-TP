from typing import Optional, Any
from lox.syntax.token import Token, TokenType, KEYWORDS
from lox.errors import DiagnosticReporter, LoxLexicalError


class Scanner:

    def __init__(self, source: str, diagnostics: Optional[DiagnosticReporter] = None):
        self.source = source
        self.diagnostics = diagnostics
        self.tokens: list[Token] = []

        self.start: int = 0
        self.current: int = 0
        self.line: int = 1

    def scan_tokens(self) -> list[Token]:
        while not self._is_at_end():
            self.start = self.current
            self.scan_token()

        self.tokens.append(
            Token(
                token_type=TokenType.EOF,
                lexeme="",
                literal=None,
                line=self.line,
            )
        )
        return self.tokens

    def scan_token(self) -> None:
        c = self._advance()

        match c:
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

            case "/":
                if self._match("/"):
                    while self._peek() != "\n" and not self._is_at_end():
                        self._advance()
                else:
                    self._add_token(TokenType.SLASH)

            case " " | "\r" | "\t":
                pass
            case "\n":
                self.line += 1

            case '"' | "'":
                self._string(c)

            case _ if c.isdigit():
                self._number()

            case _ if c.isalpha() or c == "_":
                self._identifier()

            case _:
                self._error(f"Carácter inesperado '{c}'")

    def _string(self, quote_char: str) -> None:
        value_chars: list[str] = []

        while not self._is_at_end() and self._peek() != quote_char:
            ch = self._peek()

            if ch == "\n":
                self.line += 1

            if ch == "\\":
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

        self._advance()

        literal_value = "".join(value_chars)
        self._add_token(TokenType.STRING, literal=literal_value)

    def _number(self) -> None:
        while self._peek().isdigit():
            self._advance()

        if self._peek() == "." and self._peek_next().isdigit():
            self._advance()
            while self._peek().isdigit():
                self._advance()

        lexeme = self.source[self.start : self.current]
        try:
            num_val = float(lexeme) if "." in lexeme else float(int(lexeme))
            self._add_token(TokenType.NUMBER, literal=num_val)
        except ValueError:
            self._error(f"Formato numérico inválido: '{lexeme}'")

    def _identifier(self) -> None:
        while self._peek().isalnum() or self._peek() == "_":
            self._advance()

        lexeme = self.source[self.start : self.current]
        token_type = KEYWORDS.get(lexeme, TokenType.IDENTIFIER)
        self._add_token(token_type)

    def _is_at_end(self) -> bool:
        return self.current >= len(self.source)

    def _advance(self) -> str:
        char = self.source[self.current]
        self.current += 1
        return char

    def _match(self, expected: str) -> bool:
        if self._is_at_end():
            return False
        if self.source[self.current] != expected:
            return False
        self.current += 1
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
            )
        )

    def _error(self, message: str) -> None:
        if self.diagnostics:
            self.diagnostics.report_error(self.line, "", message)
