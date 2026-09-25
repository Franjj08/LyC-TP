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


def test_if_then_branch(capsys):
    code = """
    if (true) print "entró";
    if (false) print "no entra";
    """
    run_source(code)
    stdout, _ = capsys.readouterr()
    assert stdout == "entró\n"


def test_if_else_branches(capsys):
    code = """
    if (1 > 2) {
        print "imposible";
    } else {
        print "correcto";
    }
    """
    run_source(code)
    stdout, _ = capsys.readouterr()
    assert stdout == "correcto\n"


def test_if_truthiness(capsys):
    code = """
    if (0) print "cero es verdadero en Lox";
    if ("") print "cadena vacía es verdadera en Lox";
    if (nil) print "nil"; else print "nil es falso";
    """
    run_source(code)
    stdout, _ = capsys.readouterr()
    assert stdout == "cero es verdadero en Lox\ncadena vacía es verdadera en Lox\nnil es falso\n"


def test_dangling_else(capsys):
    # En if (a) if (b) s1 else s2, el else pertenece al if interno
    code = """
    if (true)
        if (false)
            print "b es true";
        else
            print "else interno";
    """
    run_source(code)
    stdout, _ = capsys.readouterr()
    assert stdout == "else interno\n"


def test_while_loop(capsys):
    code = """
    var i = 0;
    while (i < 3) {
        print i;
        i = i + 1;
    }
    """
    run_source(code)
    stdout, _ = capsys.readouterr()
    assert stdout == "0\n1\n2\n"


def test_while_loop_never_enters(capsys):
    code = """
    var x = 10;
    while (x < 5) {
        x = x + 1;
    }
    print x;
    """
    run_source(code)
    stdout, _ = capsys.readouterr()
    assert stdout == "10\n"


def test_for_loop_basic(capsys):
    code = """
    var sum = 0;
    for (var i = 1; i <= 4; i = i + 1) {
        sum = sum + i;
    }
    print sum;
    """
    run_source(code)
    stdout, _ = capsys.readouterr()
    assert stdout == "10\n"


def test_for_loop_scope_isolation():
    code = """
    for (var i = 0; i < 3; i = i + 1) {
        var x = i;
    }
    print i;
    """
    with pytest.raises(LoxRuntimeError) as exc_info:
        run_source(code)
    assert "Variable no definida 'i'" in str(exc_info.value)


def test_for_loop_omitted_clauses(capsys):
    # Sin inicializador
    code1 = """
    var i = 0;
    for (; i < 2; i = i + 1) {
        print i;
    }
    """
    run_source(code1)
    stdout1, _ = capsys.readouterr()
    assert stdout1 == "0\n1\n"

    # Sin incremento
    code2 = """
    for (var j = 0; j < 2;) {
        print j;
        j = j + 1;
    }
    """
    run_source(code2)
    stdout2, _ = capsys.readouterr()
    assert stdout2 == "0\n1\n"


def test_nested_loops(capsys):
    code = """
    var total = 0;
    for (var i = 0; i < 3; i = i + 1) {
        var j = 0;
        while (j < 2) {
            total = total + 1;
            j = j + 1;
        }
    }
    print total;
    """
    run_source(code)
    stdout, _ = capsys.readouterr()
    assert stdout == "6\n"


def test_logical_or_short_circuit(capsys):
    # Si la izquierda es verdadera, la derecha con error no debe evaluarse
    code = """
    print true or variable_inexistente;
    print "hola" or false;
    print nil or "rescate";
    """
    run_source(code)
    stdout, _ = capsys.readouterr()
    assert stdout == "true\nhola\nrescate\n"


def test_logical_and_short_circuit(capsys):
    # Si la izquierda es falsa, la derecha con error no debe evaluarse
    code = """
    print false and variable_inexistente;
    print nil and 123;
    print true and "segundo";
    """
    run_source(code)
    stdout, _ = capsys.readouterr()
    assert stdout == "false\nnil\nsegundo\n"


def test_logical_precedence():
    interp = Interpreter()

    def eval_expr(source: str):
        scanner = Scanner(source)
        tokens = scanner.scan_tokens()
        parser = Parser(tokens)
        expr = parser.parse_expression()
        assert expr is not None
        return interp.evaluate(expr)

    # 'and' tiene mayor precedencia que 'or': false and false or true -> (false and false) or true -> true
    assert eval_expr("false and false or true") is True
    # true or false and false -> true or (false and false) -> true
    assert eval_expr("true or false and false") is True


def test_real_test_1_flow(capsys):
    flow_file = Path(__file__).resolve().parent.parent.parent / "Practica/plox/real-tests/1-flow.lox"
    assert flow_file.exists()

    cli = LoxCLI()
    cli.run_file(str(flow_file))
    stdout, _ = capsys.readouterr()
    assert "ERROR" not in stdout
    assert "--- IFs ---" in stdout
    assert "--- WHILEs ---" in stdout
    assert "--- FOR ---" in stdout
