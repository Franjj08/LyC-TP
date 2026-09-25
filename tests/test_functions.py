from pathlib import Path
import pytest
from lox.syntax.scanner import Scanner
from lox.syntax.parser import Parser
from lox.errors import LoxRuntimeError
from lox.runtime.interpreter import Interpreter
from lox.semantics.resolver import Resolver
from lox.cli import LoxCLI


def run_source(source: str, interpreter: Interpreter | None = None) -> None:
    """Helper para parsear y ejecutar sentencias."""
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()
    parser = Parser(tokens)
    statements = parser.parse()
    interp = interpreter if interpreter is not None else Interpreter()
    resolver = Resolver(interp)
    resolver.resolve(statements)
    interp.interpret(statements)


def test_simple_function_declaration_and_call(capsys):
    code = """
    fun saludar(nombre) {
        print "Hola " + nombre;
    }
    saludar("Lox");
    """
    run_source(code)
    stdout, _ = capsys.readouterr()
    assert stdout == "Hola Lox\n"


def test_function_return_values(capsys):
    code = """
    fun sumar(a, b) {
        return a + b;
    }
    print sumar(10, 20);

    fun vacio() {
        return;
    }
    print vacio();

    fun sin_retorno() {
        var x = 1;
    }
    print sin_retorno();
    """
    run_source(code)
    stdout, _ = capsys.readouterr()
    assert stdout == "30\nnil\nnil\n"


def test_recursive_fibonacci(capsys):
    code = """
    fun fib(n) {
        if (n <= 1) return n;
        return fib(n - 2) + fib(n - 1);
    }
    print fib(10);
    """
    run_source(code)
    stdout, _ = capsys.readouterr()
    assert stdout == "55\n"


def test_closures_and_counters(capsys):
    code = """
    fun crear_contador() {
        var c = 0;
        fun incrementar() {
            c = c + 1;
            return c;
        }
        return incrementar;
    }

    var c1 = crear_contador();
    var c2 = crear_contador();

    print c1();
    print c1();
    print c2();
    print c1();
    """
    run_source(code)
    stdout, _ = capsys.readouterr()
    assert stdout == "1\n2\n1\n3\n"


def test_call_non_callable_error():
    code = """
    var no_funcion = "hola";
    no_funcion();
    """
    with pytest.raises(LoxRuntimeError) as exc_info:
        run_source(code)
    assert "Solo se pueden invocar funciones y clases" in str(exc_info.value)


def test_arity_mismatch_error():
    code = """
    fun f(a, b) {
        return a + b;
    }
    f(1);
    """
    with pytest.raises(LoxRuntimeError) as exc_info:
        run_source(code)
    assert "Se esperaban 2 argumentos pero se obtuvieron 1" in str(exc_info.value)


def test_return_at_top_level_error():
    code = "return 10;"
    with pytest.raises(LoxRuntimeError) as exc_info:
        run_source(code)
    assert "No se puede retornar desde código de nivel superior" in str(exc_info.value)


def test_native_clock_function(capsys):
    code = """
    var t = clock();
    print t > 0;
    """
    run_source(code)
    stdout, _ = capsys.readouterr()
    assert stdout == "true\n"


def test_real_test_0_simple(capsys):
    simple_file = Path(__file__).resolve().parent.parent.parent / "Practica/plox/real-tests/0-simple.lox"
    assert simple_file.exists()

    cli = LoxCLI()
    cli.run_file(str(simple_file))
    stdout, _ = capsys.readouterr()
    assert "ERROR" not in stdout
    assert "--- SIMPLE CALC ---" in stdout
    assert "--- STRINGS ---" in stdout
    assert "--- BOOLEAN LOGIC ---" in stdout
