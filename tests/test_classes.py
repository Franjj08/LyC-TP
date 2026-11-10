import pytest
from lox.syntax.scanner import Scanner
from lox.syntax.parser import Parser
from lox.errors import DiagnosticReporter, LoxRuntimeError
from lox.runtime.interpreter import Interpreter
from lox.semantics.resolver import Resolver


def run_source(source: str) -> DiagnosticReporter:
    diagnostics = DiagnosticReporter()
    scanner = Scanner(source, diagnostics=diagnostics)
    tokens = scanner.scan_tokens()
    parser = Parser(tokens, diagnostics=diagnostics)
    statements = parser.parse()
    assert not diagnostics.had_error

    interpreter = Interpreter(diagnostics=diagnostics)
    resolver = Resolver(interpreter, diagnostics=diagnostics)
    resolver.resolve(statements)
    assert not diagnostics.had_error

    interpreter.interpret(statements)
    return diagnostics


def test_class_and_instance_printing(capsys):
    code = """
    class Bagel {}
    print Bagel;
    var bagel = Bagel();
    print bagel;
    """
    diag = run_source(code)
    assert not diag.had_runtime_error
    stdout, _ = capsys.readouterr()
    assert stdout == "Bagel\nBagel instance\n"


def test_instance_properties_get_and_set(capsys):
    code = """
    class Punto {}
    var p = Punto();
    p.x = 10;
    p.y = 25;
    print p.x + p.y;
    """
    diag = run_source(code)
    assert not diag.had_runtime_error
    stdout, _ = capsys.readouterr()
    assert stdout == "35\n"


def test_methods_this_and_bound_methods(capsys):
    code = """
    class Persona {
        presentarse() {
            print "Hola, soy " + this.nombre;
        }
    }
    var ana = Persona();
    ana.nombre = "Ana";
    var fn_presentar = ana.presentarse;
    fn_presentar();
    """
    diag = run_source(code)
    assert not diag.had_runtime_error
    stdout, _ = capsys.readouterr()
    assert stdout == "Hola, soy Ana\n"


def test_initializer_and_early_return(capsys):
    code = """
    class Contador {
        init(inicio) {
            if (inicio < 0) {
                this.valor = 0;
                return;
            }
            this.valor = inicio;
        }
    }
    var c1 = Contador(-5);
    var c2 = Contador(10);
    print c1.valor;
    print c2.valor;
    print c2.init(99);
    print c2.valor;
    """
    diag = run_source(code)
    assert not diag.had_runtime_error
    stdout, _ = capsys.readouterr()
    assert stdout == "0\n10\nContador instance\n99\n"


def test_inheritance_and_super(capsys):
    code = """
    class Doughnut {
        cook() {
            print "Freir hasta dorar.";
        }
    }

    class BostonCream < Doughnut {
        cook() {
            super.cook();
            print "Rellenar con crema pastelera y cubrir con chocolate.";
        }
    }

    BostonCream().cook();
    """
    diag = run_source(code)
    assert not diag.had_runtime_error
    stdout, _ = capsys.readouterr()
    assert stdout == (
        "Freir hasta dorar.\n"
        "Rellenar con crema pastelera y cubrir con chocolate.\n"
    )


def test_super_method_resolution_hierarchy(capsys):
    code = """
    class A {
        method() {
            print "A method";
        }
    }

    class B < A {
        method() {
            print "B method";
        }
        test() {
            super.method();
        }
    }

    class C < B {}

    C().test();
    """
    diag = run_source(code)
    assert not diag.had_runtime_error
    stdout, _ = capsys.readouterr()
    assert stdout == "A method\n"


@pytest.mark.parametrize(
    "code",
    [
        "var x = 123; print x.prop;",
        "var x = 123; x.prop = 456;",
        "class A {} var a = A(); print a.inexistente;",
        "var NoEsClase = 42; class Sub < NoEsClase {}",
    ],
)
def test_oop_runtime_errors(code: str):
    diag = run_source(code)
    assert diag.had_runtime_error

