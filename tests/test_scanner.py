import pytest
from lox.syntax.token import Token, TokenType, KEYWORDS
from lox.syntax.scanner import Scanner
from lox.errors import DiagnosticReporter
from lox.cli import LoxCLI


def test_single_character_tokens():
    source = "(){},.-+;*%"
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()

    expected_types = [
        TokenType.LEFT_PAREN,
        TokenType.RIGHT_PAREN,
        TokenType.LEFT_BRACE,
        TokenType.RIGHT_BRACE,
        TokenType.COMMA,
        TokenType.DOT,
        TokenType.MINUS,
        TokenType.PLUS,
        TokenType.SEMICOLON,
        TokenType.STAR,
        TokenType.PERCENT,
        TokenType.EOF,
    ]

    assert [t.token_type for t in tokens] == expected_types
    assert [t.lexeme for t in tokens[:-1]] == ["(", ")", "{", "}", ",", ".", "-", "+", ";", "*", "%"]


def test_two_character_operators():
    source = "! != = == < <= > >="
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()

    expected_types = [
        TokenType.BANG,
        TokenType.BANG_EQUAL,
        TokenType.EQUAL,
        TokenType.EQUAL_EQUAL,
        TokenType.LESS,
        TokenType.LESS_EQUAL,
        TokenType.GREATER,
        TokenType.GREATER_EQUAL,
        TokenType.EOF,
    ]

    assert [t.token_type for t in tokens] == expected_types


def test_slash_and_comments():
    source = """
    // Este es un comentario
    / // otro comentario
    /
    """
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()

    expected_types = [
        TokenType.SLASH,
        TokenType.SLASH,
        TokenType.EOF,
    ]
    assert [t.token_type for t in tokens] == expected_types


def test_string_literals():
    source = '"hola mundo" \'comillas simples\' "con \\n escape \\t y \\"comillas\\""'
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()

    assert len(tokens) == 4
    assert tokens[0].token_type == TokenType.STRING
    assert tokens[0].literal == "hola mundo"

    assert tokens[1].token_type == TokenType.STRING
    assert tokens[1].literal == "comillas simples"

    assert tokens[2].token_type == TokenType.STRING
    assert tokens[2].literal == 'con \n escape \t y "comillas"'

    assert tokens[3].token_type == TokenType.EOF


def test_multiline_string():
    source = '''"linea 1
linea 2
linea 3"'''
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()

    assert tokens[0].token_type == TokenType.STRING
    assert tokens[0].literal == "linea 1\nlinea 2\nlinea 3"
    assert tokens[0].line == 3


def test_number_literals():
    source = "123 45.67 0.001 9999"
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()

    expected_literals = [123.0, 45.67, 0.001, 9999.0]
    for i, lit in enumerate(expected_literals):
        assert tokens[i].token_type == TokenType.NUMBER
        assert tokens[i].literal == lit


def test_identifiers_and_keywords():
    source = "var language = \"Lox\"; fun add(a, b) { return a + b; } if (true or false) { print nil; }"
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()

    types = [t.token_type for t in tokens]
    assert types[0] == TokenType.VAR
    assert types[1] == TokenType.IDENTIFIER
    assert tokens[1].lexeme == "language"
    assert types[2] == TokenType.EQUAL
    assert types[3] == TokenType.STRING
    assert types[4] == TokenType.SEMICOLON
    assert types[5] == TokenType.FUN
    assert types[6] == TokenType.IDENTIFIER
    assert tokens[6].lexeme == "add"


def test_maximal_munch():
    source = "var truemanshow = true; if_condition = if;"
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()

    # "truemanshow" no debe ser cortado en "true"
    assert tokens[0].token_type == TokenType.VAR
    assert tokens[1].token_type == TokenType.IDENTIFIER
    assert tokens[1].lexeme == "truemanshow"
    assert tokens[2].token_type == TokenType.EQUAL
    assert tokens[3].token_type == TokenType.TRUE

    # "if_condition" no debe ser cortado en "if"
    assert tokens[5].token_type == TokenType.IDENTIFIER
    assert tokens[5].lexeme == "if_condition"
    assert tokens[6].token_type == TokenType.EQUAL
    assert tokens[7].token_type == TokenType.IF


def test_all_keywords():
    for keyword, token_type in KEYWORDS.items():
        scanner = Scanner(keyword)
        tokens = scanner.scan_tokens()
        assert len(tokens) == 2
        assert tokens[0].token_type == token_type
        assert tokens[0].lexeme == keyword


def test_line_and_column_tracking():
    source = "var a = 1;\nvar b = 2;"
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()

    # Line 1
    assert tokens[0].lexeme == "var" and tokens[0].line == 1 and tokens[0].column == 1
    assert tokens[1].lexeme == "a" and tokens[1].line == 1 and tokens[1].column == 5
    assert tokens[2].lexeme == "=" and tokens[2].line == 1 and tokens[2].column == 7
    assert tokens[3].lexeme == "1" and tokens[3].line == 1 and tokens[3].column == 9
    assert tokens[4].lexeme == ";" and tokens[4].line == 1 and tokens[4].column == 10

    # Line 2
    assert tokens[5].lexeme == "var" and tokens[5].line == 2 and tokens[5].column == 1
    assert tokens[6].lexeme == "b" and tokens[6].line == 2 and tokens[6].column == 5


def test_lexical_errors_unexpected_character():
    reporter = DiagnosticReporter()
    scanner = Scanner("var @ = 1;", diagnostics=reporter)
    tokens = scanner.scan_tokens()

    assert reporter.had_error
    # El scanner sigue procesando los tokens válidos restantes
    assert tokens[0].token_type == TokenType.VAR
    assert tokens[1].token_type == TokenType.EQUAL
    assert tokens[2].token_type == TokenType.NUMBER


def test_lexical_errors_unterminated_string():
    reporter = DiagnosticReporter()
    scanner = Scanner('"cadena sin cerrar', diagnostics=reporter)
    scanner.scan_tokens()

    assert reporter.had_error


def test_cli_lexical_error_exit_code(tmp_path):
    error_file = tmp_path / "error.lox"
    error_file.write_text('var @ = "invalido";', encoding="utf-8")

    cli = LoxCLI()
    with pytest.raises(SystemExit) as exc_info:
        cli.run_file(str(error_file))
    assert exc_info.value.code == 65
