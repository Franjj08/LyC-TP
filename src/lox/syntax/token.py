from enum import Enum, auto
from dataclasses import dataclass
from typing import Any, Optional


class TokenType(Enum):
    # Tokens de un solo carácter
    LEFT_PAREN = auto()
    RIGHT_PAREN = auto()
    LEFT_BRACE = auto()
    RIGHT_BRACE = auto()
    COMMA = auto()
    DOT = auto()
    MINUS = auto()
    PLUS = auto()
    SEMICOLON = auto()
    SLASH = auto()
    STAR = auto()
    PERCENT = auto()

    # Operadores de uno o dos caracteres
    BANG = auto()
    BANG_EQUAL = auto()
    EQUAL = auto()
    EQUAL_EQUAL = auto()
    GREATER = auto()
    GREATER_EQUAL = auto()
    LESS = auto()
    LESS_EQUAL = auto()

    # Literales
    IDENTIFIER = auto()
    STRING = auto()
    NUMBER = auto()

    # Palabras clave reservadas
    AND = auto()
    CLASS = auto()
    ELSE = auto()
    FALSE = auto()
    FUN = auto()
    FOR = auto()
    IF = auto()
    NIL = auto()
    OR = auto()
    PRINT = auto()
    RETURN = auto()
    SUPER = auto()
    THIS = auto()
    TRUE = auto()
    VAR = auto()
    WHILE = auto()

    # Fin de archivo
    EOF = auto()


KEYWORDS: dict[str, TokenType] = {
    "and": TokenType.AND,
    "class": TokenType.CLASS,
    "else": TokenType.ELSE,
    "false": TokenType.FALSE,
    "for": TokenType.FOR,
    "fun": TokenType.FUN,
    "if": TokenType.IF,
    "nil": TokenType.NIL,
    "or": TokenType.OR,
    "print": TokenType.PRINT,
    "return": TokenType.RETURN,
    "super": TokenType.SUPER,
    "this": TokenType.THIS,
    "true": TokenType.TRUE,
    "var": TokenType.VAR,
    "while": TokenType.WHILE,
}


@dataclass(frozen=True)
class Token:
    """Representa una unidad léxica atómica (Token) con información de tipo y posición."""

    token_type: TokenType
    lexeme: str
    literal: Any = None
    line: int = 1
    column: int = 1

    def __repr__(self) -> str:
        if self.token_type == TokenType.IDENTIFIER:
            return f"{self.token_type.name}<{self.lexeme}>"
        if self.literal is not None:
            return f"{self.token_type.name}<{self.literal}>"
        return self.token_type.name

    def __str__(self) -> str:
        return f"Token({self.token_type.name}, lexeme={self.lexeme!r}, literal={self.literal!r}, line={self.line}, col={self.column})"
