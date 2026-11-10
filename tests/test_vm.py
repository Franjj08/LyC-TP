from pathlib import Path
import pytest

from lox.bytecode import BytecodeCompiler, VirtualMachine
from lox.cli import LoxCLI
from lox.errors import DiagnosticReporter
from lox.syntax.parser import Parser
from lox.syntax.scanner import Scanner


def run_vm_source(source: str) -> DiagnosticReporter:
    diagnostics = DiagnosticReporter()
    scanner = Scanner(source, diagnostics=diagnostics)
    tokens = scanner.scan_tokens()
    parser = Parser(tokens, diagnostics=diagnostics)
    statements = parser.parse()
    if diagnostics.had_error:
        return diagnostics

    vm = VirtualMachine(diagnostics=diagnostics)
    vm.interpret(statements)
    return diagnostics


def test_vm_arithmetic_and_comparisons(capsys):
    code = """
    print 2 + 3 * 4;
    print (10 - 2) / 4;
    print 10 % 3;
    print -5 + 8;
    print !false and (3 < 5 or 1 == 2);
    print "hola " + "vm";
    """
    diag = run_vm_source(code)
    assert not diag.had_error
    assert not diag.had_runtime_error
    stdout, _ = capsys.readouterr()
    assert stdout == "14\n2\n1\n3\ntrue\nhola vm\n"


def test_vm_globals_locals_and_control_flow(capsys):
    code = """
    var acc = 0;
    for (var i = 1; i <= 5; i = i + 1) {
        var step = i * 2;
        if (step > 4) {
            acc = acc + step;
        } else {
            acc = acc + 1;
        }
    }
    print acc;
    """
    diag = run_vm_source(code)
    assert not diag.had_error
    assert not diag.had_runtime_error
    stdout, _ = capsys.readouterr()
    # i=1: step=2 -> +1 (1)
    # i=2: step=4 -> +1 (2)
    # i=3: step=6 -> +6 (8)
    # i=4: step=8 -> +8 (16)
    # i=5: step=10 -> +10 (26)
    assert stdout == "26\n"


def test_vm_functions_recursion_and_closures(capsys):
    code = """
    fun fib(n) {
        if (n < 2) return n;
        return fib(n - 1) + fib(n - 2);
    }
    print fib(8);

    fun make_counter(base) {
        var count = base;
        fun inc(delta) {
            count = count + delta;
            return count;
        }
        return inc;
    }

    var c = make_counter(10);
    print c(5);
    print c(3);
    """
    diag = run_vm_source(code)
    assert not diag.had_error
    assert not diag.had_runtime_error
    stdout, _ = capsys.readouterr()
    assert stdout == "21\n15\n18\n"


def test_vm_oop_classes_inheritance_and_super(capsys):
    code = """
    class Figura {
        init(nombre) {
            this.nombre = nombre;
        }
        describir() {
            return "Figura: " + this.nombre;
        }
    }

    class Rectangulo < Figura {
        init(ancho, alto) {
            super.init("Rectangulo");
            this.ancho = ancho;
            this.alto = alto;
        }
        area() {
            return this.ancho * this.alto;
        }
        describir() {
            return super.describir() + " (" + "area=" + ")";
        }
    }

    var r = Rectangulo(4, 6);
    print r.nombre;
    print r.area();
    print r.describir();
    var bound_area = r.area;
    print bound_area();
    """
    diag = run_vm_source(code)
    assert not diag.had_error
    assert not diag.had_runtime_error
    stdout, _ = capsys.readouterr()
    assert stdout == "Rectangulo\n24\nFigura: Rectangulo (area=)\n24\n"


def test_vm_disassembler():
    scanner = Scanner("var x = 1 + 2; print x;")
    parser = Parser(scanner.scan_tokens())
    compiler = BytecodeCompiler()
    fn = compiler.compile(parser.parse())
    assert fn is not None
    dis_text = fn.chunk.disassemble()
    assert "OP_CONSTANT" in dis_text
    assert "OP_ADD" in dis_text
    assert "OP_DEFINE_GLOBAL" in dis_text
    assert "OP_PRINT" in dis_text


@pytest.mark.parametrize(
    "code",
    [
        "{ var a = a; }",
        "{ var x = 1; var x = 2; }",
        "return 10;",
        "print this;",
        "class A < A {}",
        "class A { init() { return 1; } }",
        "class A { m() { super.m(); } }",
    ],
)
def test_vm_compile_errors(code: str):
    diag = run_vm_source(code)
    assert diag.had_error


@pytest.mark.parametrize(
    "code",
    [
        "print 1 / 0;",
        "print 1 + true;",
        "print indefinida;",
        "var x = 5; x();",
        "var x = 5; print x.prop;",
        "class A {} var a = A(); print a.no_existe;",
        "var NoClase = 10; class B < NoClase {}",
    ],
)
def test_vm_runtime_errors(code: str):
    diag = run_vm_source(code)
    assert diag.had_runtime_error


@pytest.mark.parametrize(
    "filename",
    [
        "0-simple.lox",
        "1-flow.lox",
        "2-functions.lox",
        "3-minsky.lox",
        "4-fizzbuzz.lox",
    ],
)
def test_vm_parity_with_tree_walk_on_real_tests(filename: str, capsys):
    test_file = Path(__file__).resolve().parent / "real_tests" / filename
    source = test_file.read_text(encoding="utf-8")

    cli_tw = LoxCLI(use_vm=False)
    cli_tw.run(source, is_repl=False)
    out_tw, _ = capsys.readouterr()

    cli_vm = LoxCLI(use_vm=True)
    cli_vm.run(source, is_repl=False)
    out_vm, _ = capsys.readouterr()

    assert not cli_tw.diagnostics.had_error
    assert not cli_vm.diagnostics.had_error
    assert out_vm == out_tw


def test_showcase_example_clash_royale_parity(capsys):
    example_file = (
        Path(__file__).resolve().parent.parent / "examples" / "clash_royale.lox"
    )
    source = example_file.read_text(encoding="utf-8")

    cli_tw = LoxCLI(use_vm=False)
    cli_tw.run(source, is_repl=False)
    out_tw, _ = capsys.readouterr()

    cli_vm = LoxCLI(use_vm=True)
    cli_vm.run(source, is_repl=False)
    out_vm, _ = capsys.readouterr()

    assert not cli_tw.diagnostics.had_error
    assert not cli_vm.diagnostics.had_error
    assert "=== ARENA CLASH ROYALE & LADDER EN LOX ===" in out_vm
    assert out_vm == out_tw
