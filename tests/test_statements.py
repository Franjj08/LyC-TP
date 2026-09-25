import pytest
from lox.syntax.scanner import Scanner
from lox.syntax.parser import Parser
from lox.errors import DiagnosticReporter, LoxRuntimeError
from lox.runtime.environment import Environment
from lox.runtime.interpreter import Interpreter
from lox.semantics.resolver import Resolver
from lox.cli import LoxCLI


def run_source(source: str, interpreter: Interpreter | None = None) -> None:
    """Ejecuta código fuente compuesto por una o varias sentencias."""
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()
    parser = Parser(tokens)
    statements = parser.parse()
    interp = interpreter if interpreter is not None else Interpreter()
    resolver = Resolver(interp)
    resolver.resolve(statements)
    interp.interpret(statements)


def test_environment_direct_operations():
    global_env = Environment()
    global_env.define("x", 10)
    
    scanner = Scanner("x")
    token_x = scanner.scan_tokens()[0]
    assert global_env.get(token_x) == 10

    # Asignación
    global_env.assign(token_x, 20)
    assert global_env.get(token_x) == 20

    # Variable inexistente
    scanner_y = Scanner("y")
    token_y = scanner_y.scan_tokens()[0]
    with pytest.raises(LoxRuntimeError) as exc_info:
        global_env.get(token_y)
    assert "Variable no definida 'y'" in str(exc_info.value)

    with pytest.raises(LoxRuntimeError) as exc_info:
        global_env.assign(token_y, 99)
    assert "Variable no definida 'y'" in str(exc_info.value)


def test_environment_nested_scopes():
    global_env = Environment()
    global_env.define("a", "global")
    global_env.define("b", "global_b")

    local_env = Environment(enclosing=global_env)
    local_env.define("a", "local")

    scanner_a = Scanner("a")
    token_a = scanner_a.scan_tokens()[0]
    scanner_b = Scanner("b")
    token_b = scanner_b.scan_tokens()[0]

    # 'a' debe resolverse localmente, 'b' en el padre
    assert local_env.get(token_a) == "local"
    assert local_env.get(token_b) == "global_b"
    assert global_env.get(token_a) == "global"


def test_print_statement(capsys):
    run_source('print "hola mundo";')
    stdout, _ = capsys.readouterr()
    assert stdout == "hola mundo\n"

    run_source('print 2 + 3 * 4;')
    stdout, _ = capsys.readouterr()
    assert stdout == "14\n"


def test_var_declaration_and_reading(capsys):
    code = """
    var a = 42;
    var b;
    print a;
    print b;
    """
    run_source(code)
    stdout, _ = capsys.readouterr()
    assert stdout == "42\nnil\n"


def test_variable_assignment(capsys):
    code = """
    var x = 10;
    x = 20;
    print x;
    """
    run_source(code)
    stdout, _ = capsys.readouterr()
    assert stdout == "20\n"


def test_chained_assignment(capsys):
    code = """
    var a;
    var b;
    a = b = 5;
    print a;
    print b;
    """
    run_source(code)
    stdout, _ = capsys.readouterr()
    assert stdout == "5\n5\n"


def test_undefined_variable_runtime_error():
    with pytest.raises(LoxRuntimeError) as exc_info:
        run_source("print x;")
    assert "Variable no definida 'x'" in str(exc_info.value)

    with pytest.raises(LoxRuntimeError) as exc_info:
        run_source("x = 10;")
    assert "Variable no definida 'x'" in str(exc_info.value)


def test_invalid_assignment_target_syntax_error():
    diagnostics = DiagnosticReporter()
    scanner = Scanner("1 + 2 = 3;", diagnostics=diagnostics)
    tokens = scanner.scan_tokens()
    parser = Parser(tokens, diagnostics=diagnostics)
    parser.parse()
    assert diagnostics.had_error


def test_block_shadowing(capsys):
    code = """
    var a = "global";
    {
        var a = "local";
        print a;
    }
    print a;
    """
    run_source(code)
    stdout, _ = capsys.readouterr()
    assert stdout == "local\nglobal\n"


def test_block_nested_scopes_full(capsys):
    code = """
    var a = "global a";
    var b = "global b";
    var c = "global c";
    {
        var a = "outer a";
        var b = "outer b";
        {
            var a = "inner a";
            print a;
            print b;
            print c;
        }
        print a;
        print b;
        print c;
    }
    print a;
    print b;
    print c;
    """
    run_source(code)
    stdout, _ = capsys.readouterr()
    expected = "\n".join([
        "inner a",
        "outer b",
        "global c",
        "outer a",
        "outer b",
        "global c",
        "global a",
        "global b",
        "global c",
    ]) + "\n"
    assert stdout == expected


def test_block_scope_isolation():
    code = """
    {
        var interna = 123;
    }
    print interna;
    """
    with pytest.raises(LoxRuntimeError) as exc_info:
        run_source(code)
    assert "Variable no definida 'interna'" in str(exc_info.value)


def test_cli_run_file_with_statements(tmp_path, capsys):
    script_file = tmp_path / "scopes.lox"
    script_file.write_text(
        """
        var x = 10;
        {
            var x = 20;
            print x;
        }
        print x;
        """,
        encoding="utf-8",
    )

    cli = LoxCLI()
    cli.run_file(str(script_file))
    stdout, _ = capsys.readouterr()
    assert stdout == "20\n10\n"
    assert not cli.diagnostics.had_error
    assert not cli.diagnostics.had_runtime_error
