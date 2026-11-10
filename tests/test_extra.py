import pytest
from lox.cli import LoxCLI


@pytest.mark.parametrize("use_vm", [False, True])
def test_compound_assignment_variables_and_strings(use_vm: bool, capsys):
    code = """
    var x = 10;
    x += 5;
    print x;
    x -= 3;
    print x;
    x *= 2;
    print x;
    x /= 4;
    print x;

    var saludo = "Hola";
    saludo += " Lox";
    print saludo;
    """
    cli = LoxCLI(use_vm=use_vm)
    cli.run(code, is_repl=False)
    assert not cli.diagnostics.had_error
    assert not cli.diagnostics.had_runtime_error
    stdout, _ = capsys.readouterr()
    assert stdout == "15\n12\n24\n6\nHola Lox\n"


@pytest.mark.parametrize("use_vm", [False, True])
def test_compound_assignment_on_locals_closures_and_properties(use_vm: bool, capsys):
    code = """
    class Cuenta {
        init(saldo) {
            this.saldo = saldo;
        }
        depositar(monto) {
            this.saldo += monto;
        }
        aplicar_interes(factor) {
            this.saldo *= factor;
        }
    }

    var c = Cuenta(100);
    c.depositar(50);
    c.aplicar_interes(2);
    c.saldo -= 20;
    print c.saldo;
    """
    cli = LoxCLI(use_vm=use_vm)
    cli.run(code, is_repl=False)
    assert not cli.diagnostics.had_error
    assert not cli.diagnostics.had_runtime_error
    stdout, _ = capsys.readouterr()
    assert stdout == "280\n"


@pytest.mark.parametrize("use_vm", [False, True])
def test_power_operator_precedence_and_associativity(use_vm: bool, capsys):
    code = """
    print 2 ** 10;
    print 2 + 3 * 2 ** 3;
    print 2 ** 3 ** 2;
    print 2 ** -2;
    print -2 ** 2;
    print (-2) ** 2;
    """
    cli = LoxCLI(use_vm=use_vm)
    cli.run(code, is_repl=False)
    assert not cli.diagnostics.had_error
    assert not cli.diagnostics.had_runtime_error
    stdout, _ = capsys.readouterr()
    assert stdout == "1024\n26\n512\n0.25\n-4\n4\n"


@pytest.mark.parametrize("use_vm", [False, True])
@pytest.mark.parametrize(
    "code",
    [
        'print "hola" ** 2;',
        "var x = 10; x -= true;",
        "var x = 10; x /= 0;",
    ],
)
def test_extra_operators_runtime_errors(use_vm: bool, code: str):
    cli = LoxCLI(use_vm=use_vm)
    cli.run(code, is_repl=False)
    assert cli.diagnostics.had_runtime_error

