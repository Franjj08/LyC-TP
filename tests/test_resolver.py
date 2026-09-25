from pathlib import Path
import pytest
from lox.syntax.scanner import Scanner
from lox.syntax.parser import Parser
from lox.errors import DiagnosticReporter
from lox.runtime.interpreter import Interpreter
from lox.semantics.resolver import Resolver
from lox.cli import LoxCLI


def run_source(source: str, interpreter: Interpreter | None = None) -> None:
    """Helper para escanear, parsear, resolver y ejecutar sentencias."""
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()
    parser = Parser(tokens)
    statements = parser.parse()
    interp = interpreter if interpreter is not None else Interpreter()
    resolver = Resolver(interp)
    resolver.resolve(statements)
    interp.interpret(statements)


def test_closure_bug_fixed(capsys):
    code = """
    var a = "global";
    {
        fun ret_a() {
            return a;
        }

        print ret_a();
        var a = "block";
        print ret_a();
    }
    """
    run_source(code)
    stdout, _ = capsys.readouterr()
    assert stdout == "global\nglobal\n"


def test_error_variable_self_initialization():
    code = """
    {
        var a = a;
    }
    """
    diagnostics = DiagnosticReporter()
    scanner = Scanner(code, diagnostics=diagnostics)
    tokens = scanner.scan_tokens()
    parser = Parser(tokens, diagnostics=diagnostics)
    statements = parser.parse()

    interp = Interpreter(diagnostics=diagnostics)
    resolver = Resolver(interp, diagnostics=diagnostics)
    resolver.resolve(statements)

    assert diagnostics.had_error


def test_error_duplicate_variable_in_local_scope():
    code = """
    {
        var x = 1;
        var x = 2;
    }
    """
    diagnostics = DiagnosticReporter()
    scanner = Scanner(code, diagnostics=diagnostics)
    tokens = scanner.scan_tokens()
    parser = Parser(tokens, diagnostics=diagnostics)
    statements = parser.parse()

    interp = Interpreter(diagnostics=diagnostics)
    resolver = Resolver(interp, diagnostics=diagnostics)
    resolver.resolve(statements)

    assert diagnostics.had_error


def test_error_return_from_top_level():
    code = "return 42;"
    diagnostics = DiagnosticReporter()
    scanner = Scanner(code, diagnostics=diagnostics)
    tokens = scanner.scan_tokens()
    parser = Parser(tokens, diagnostics=diagnostics)
    statements = parser.parse()

    interp = Interpreter(diagnostics=diagnostics)
    resolver = Resolver(interp, diagnostics=diagnostics)
    resolver.resolve(statements)

    assert diagnostics.had_error


def test_real_test_2_functions(capsys):
    test_file = Path(__file__).resolve().parent.parent.parent / "Practica/plox/real-tests/2-functions.lox"
    assert test_file.exists()

    cli = LoxCLI()
    cli.run_file(str(test_file))
    stdout, _ = capsys.readouterr()
    assert "ERROR" not in stdout
    assert "--- CLOSURE BUG ---" in stdout


def test_real_test_3_minsky(capsys):
    test_file = Path(__file__).resolve().parent.parent.parent / "Practica/plox/real-tests/3-minsky.lox"
    assert test_file.exists()

    cli = LoxCLI()
    cli.run_file(str(test_file))
    stdout, _ = capsys.readouterr()
    assert "ERROR" not in stdout
    assert "--- MINSKY MACHINE ---" in stdout


def test_real_test_4_fizzbuzz(capsys):
    test_file = Path(__file__).resolve().parent.parent.parent / "Practica/plox/real-tests/4-fizzbuzz.lox"
    assert test_file.exists()

    cli = LoxCLI()
    cli.run_file(str(test_file))
    stdout, _ = capsys.readouterr()
    assert "ERROR" not in stdout
    assert "--- FIZZ BUZZ ---" in stdout
