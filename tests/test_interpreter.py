import sys
from unittest.mock import patch
import pytest
from lox.syntax.scanner import Scanner
from lox.syntax.parser import Parser
from lox.syntax.token import Token, TokenType
from lox.errors import DiagnosticReporter, LoxRuntimeError
from lox.runtime.interpreter import Interpreter
from lox.cli import LoxCLI


def evaluate_source(source: str, interpreter: Interpreter | None = None) -> object:
    """Helper para escanear, parsear y evaluar una expresión en el intérprete."""
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()
    parser = Parser(tokens)
    expr = parser.parse_expression()
    assert expr is not None, f"Fallo al parsear la expresión: {source}"
    interp = interpreter if interpreter is not None else Interpreter()
    return interp.evaluate(expr)


def test_literal_evaluation():
    assert evaluate_source("123") == 123.0
    assert evaluate_source("45.67") == 45.67
    assert evaluate_source('"hola mundo"') == "hola mundo"
    assert evaluate_source("true") is True
    assert evaluate_source("false") is False
    assert evaluate_source("nil") is None


def test_grouping_evaluation():
    assert evaluate_source("(42)") == 42.0
    assert evaluate_source("((1 + 2) * 3)") == 9.0


def test_unary_minus_evaluation():
    assert evaluate_source("-5") == -5.0
    assert evaluate_source("--5") == 5.0
    assert evaluate_source("-0.5") == -0.5

    with pytest.raises(LoxRuntimeError) as exc_info:
        evaluate_source('-"texto"')
    assert "El operando debe ser un número" in str(exc_info.value)

    with pytest.raises(LoxRuntimeError):
        evaluate_source("-true")

    with pytest.raises(LoxRuntimeError):
        evaluate_source("-nil")


def test_unary_bang_truthiness():
    # En Lox: únicamente false y nil son falsos, todo lo demás es verdadero
    assert evaluate_source("!true") is False
    assert evaluate_source("!false") is True
    assert evaluate_source("!nil") is True

    # 0 y cadenas vacías son verdaderas en Lox
    assert evaluate_source("!0") is False
    assert evaluate_source('!""') is False
    assert evaluate_source("!42") is False
    assert evaluate_source('!"hola"') is False

    # Doble negación
    assert evaluate_source("!!true") is True
    assert evaluate_source("!!nil") is False
    assert evaluate_source("!!0") is True


def test_binary_arithmetic():
    assert evaluate_source("2 + 3") == 5.0
    assert evaluate_source("10 - 4") == 6.0
    assert evaluate_source("3 * 7") == 21.0
    assert evaluate_source("8 / 2") == 4.0
    assert evaluate_source("10 % 3") == 1.0
    assert evaluate_source("2 + 3 * 4") == 14.0
    assert evaluate_source("(2 + 3) * 4") == 20.0
    assert evaluate_source("5 - 3 - 1") == 1.0


def test_binary_string_concatenation():
    assert evaluate_source('"hola" + " mundo"') == "hola mundo"
    assert evaluate_source('"" + "test"') == "test"


def test_binary_type_errors():
    with pytest.raises(LoxRuntimeError) as exc_info:
        evaluate_source('"a" + 1')
    assert "dos números o dos cadenas" in str(exc_info.value)

    with pytest.raises(LoxRuntimeError):
        evaluate_source('1 + "a"')

    with pytest.raises(LoxRuntimeError):
        evaluate_source("true + false")

    with pytest.raises(LoxRuntimeError):
        evaluate_source("nil + nil")

    with pytest.raises(LoxRuntimeError):
        evaluate_source('5 - "a"')

    with pytest.raises(LoxRuntimeError):
        evaluate_source('true * 2')


def test_division_by_zero():
    with pytest.raises(LoxRuntimeError) as exc_info:
        evaluate_source("10 / 0")
    assert "División por cero" in str(exc_info.value)

    with pytest.raises(LoxRuntimeError) as exc_info:
        evaluate_source("10 % 0")
    assert "Módulo por cero" in str(exc_info.value)


def test_comparisons():
    assert evaluate_source("5 > 3") is True
    assert evaluate_source("3 > 5") is False
    assert evaluate_source("3 >= 3") is True
    assert evaluate_source("2 >= 3") is False
    assert evaluate_source("2 < 4") is True
    assert evaluate_source("5 < 1") is False
    assert evaluate_source("4 <= 4") is True
    assert evaluate_source("5 <= 4") is False

    with pytest.raises(LoxRuntimeError):
        evaluate_source('5 > "3"')

    with pytest.raises(LoxRuntimeError):
        evaluate_source('"a" < "b"')


def test_equality():
    assert evaluate_source("5 == 5") is True
    assert evaluate_source("5 != 5") is False
    assert evaluate_source("5 != 3") is True
    assert evaluate_source('"hola" == "hola"') is True
    assert evaluate_source('"hola" != "chau"') is True
    assert evaluate_source("nil == nil") is True
    assert evaluate_source("nil != false") is True

    # Comprobación estricta de tipos: evitar coerción de Python
    assert evaluate_source("false == 0") is False
    assert evaluate_source("true == 1") is False
    assert evaluate_source('"" == false') is False
    assert evaluate_source('5 == "5"') is False


def test_stringify_representation():
    interp = Interpreter()
    assert interp.stringify(None) == "nil"
    assert interp.stringify(True) == "true"
    assert interp.stringify(False) == "false"
    assert interp.stringify(42.0) == "42"
    assert interp.stringify(42.5) == "42.5"
    assert interp.stringify(-10.0) == "-10"
    assert interp.stringify(0.0) == "0"
    assert interp.stringify("hola") == "hola"


def test_interpreter_diagnostic_reporting():
    diagnostics = DiagnosticReporter()
    interp = Interpreter(diagnostics=diagnostics)

    scanner = Scanner('1 / 0')
    tokens = scanner.scan_tokens()
    expr = Parser(tokens).parse_expression()
    assert expr is not None

    result = interp.interpret(expr)
    assert result is None
    assert diagnostics.had_runtime_error


def test_cli_execution_evaluation(capsys):
    cli = LoxCLI()
    result = cli.run("2 + 3 * 4")
    assert result == 14.0
    stdout, _ = capsys.readouterr()
    assert "14" in stdout


def test_cli_runtime_error_exit_code(tmp_path):
    error_file = tmp_path / "runtime_error.lox"
    error_file.write_text("1 / 0;", encoding="utf-8")

    cli = LoxCLI()
    with pytest.raises(SystemExit) as exc_info:
        cli.run_file(str(error_file))
    assert exc_info.value.code == 70
