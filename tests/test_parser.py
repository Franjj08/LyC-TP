import pytest
from lox.syntax.scanner import Scanner
from lox.syntax.parser import Parser
from lox.syntax.ast import (
    BinaryExpr,
    UnaryExpr,
    GroupingExpr,
    LiteralExpr,
    GetExpr,
    SetExpr,
    ThisExpr,
    SuperExpr,
    ClassDecl,
    AstPrinter,
)
from lox.errors import DiagnosticReporter
from lox.cli import LoxCLI


def parse_expression(source: str, diagnostics: DiagnosticReporter | None = None):
    scanner = Scanner(source, diagnostics=diagnostics)
    tokens = scanner.scan_tokens()
    parser = Parser(tokens, diagnostics=diagnostics)
    return parser.parse_expression()


def test_literal_expressions():
    printer = AstPrinter()

    expr_num = parse_expression("123.45")
    assert isinstance(expr_num, LiteralExpr)
    assert expr_num.value == 123.45
    assert printer.print(expr_num) == "123.45"

    expr_str = parse_expression('"hola mundo"')
    assert isinstance(expr_str, LiteralExpr)
    assert expr_str.value == "hola mundo"
    assert printer.print(expr_str) == '"hola mundo"'

    expr_true = parse_expression("true")
    assert isinstance(expr_true, LiteralExpr)
    assert expr_true.value is True
    assert printer.print(expr_true) == "true"

    expr_nil = parse_expression("nil")
    assert isinstance(expr_nil, LiteralExpr)
    assert expr_nil.value is None
    assert printer.print(expr_nil) == "nil"


def test_unary_expressions():
    printer = AstPrinter()

    expr = parse_expression("-42")
    assert isinstance(expr, UnaryExpr)
    assert expr.operator.lexeme == "-"
    assert printer.print(expr) == "(- 42.0)"

    expr_not = parse_expression("!true")
    assert isinstance(expr_not, UnaryExpr)
    assert expr_not.operator.lexeme == "!"
    assert printer.print(expr_not) == "(! true)"

    expr_double = parse_expression("!-5")
    assert printer.print(expr_double) == "(! (- 5.0))"


def test_binary_arithmetic_precedence():
    printer = AstPrinter()

    # Multiplicación tiene mayor precedencia que suma
    expr1 = parse_expression("2 + 3 * 4")
    assert printer.print(expr1) == "(+ 2.0 (* 3.0 4.0))"

    # División tiene mayor precedencia que resta
    expr2 = parse_expression("10 - 8 / 2")
    assert printer.print(expr2) == "(- 10.0 (/ 8.0 2.0))"

    # Módulo tiene precedencia de factor
    expr3 = parse_expression("10 % 3 + 1")
    assert printer.print(expr3) == "(+ (% 10.0 3.0) 1.0)"


def test_left_associativity():
    printer = AstPrinter()

    # 10 - 5 - 2 debe asociar a izquierda: ((10 - 5) - 2)
    expr = parse_expression("10 - 5 - 2")
    assert printer.print(expr) == "(- (- 10.0 5.0) 2.0)"

    # 8 / 4 / 2 debe asociar a izquierda: ((8 / 4) / 2)
    expr2 = parse_expression("8 / 4 / 2")
    assert printer.print(expr2) == "(/ (/ 8.0 4.0) 2.0)"


def test_grouping_precedence_override():
    printer = AstPrinter()

    expr = parse_expression("(2 + 3) * 4")
    assert printer.print(expr) == "(* (group (+ 2.0 3.0)) 4.0)"

    expr_nested = parse_expression("((5))")
    assert printer.print(expr_nested) == "(group (group 5.0))"


def test_comparison_and_equality_precedence():
    printer = AstPrinter()

    # Comparación sobre términos: 1 + 2 > 3
    expr1 = parse_expression("1 + 2 > 3")
    assert printer.print(expr1) == "(> (+ 1.0 2.0) 3.0)"

    # Igualdad sobre comparaciones: 1 < 2 == true
    expr2 = parse_expression("1 < 2 == true")
    assert printer.print(expr2) == "(== (< 1.0 2.0) true)"

    # Desigualdad: 5 != 2 + 3
    expr3 = parse_expression("5 != 2 + 3")
    assert printer.print(expr3) == "(!= 5.0 (+ 2.0 3.0))"


def test_syntax_error_missing_closing_paren():
    diagnostics = DiagnosticReporter()
    expr = parse_expression("(1 + 2", diagnostics=diagnostics)

    assert expr is None
    assert diagnostics.had_error


def test_syntax_error_missing_operand():
    diagnostics = DiagnosticReporter()
    expr = parse_expression("1 + * 2", diagnostics=diagnostics)

    assert expr is None
    assert diagnostics.had_error


def test_syntax_error_unexpected_leading_token():
    diagnostics = DiagnosticReporter()
    expr = parse_expression("* 5", diagnostics=diagnostics)

    assert expr is None
    assert diagnostics.had_error


def test_cli_ast_mode(capsys):
    cli = LoxCLI(ast_mode=True)
    cli.run("2 + 3 * 4")
    stdout, _ = capsys.readouterr()
    assert "(+ 2.0 (* 3.0 4.0))" in stdout


def test_oop_expressions_parsing():
    printer = AstPrinter()

    expr_get = parse_expression("auto.motor.potencia")
    assert isinstance(expr_get, GetExpr)
    assert expr_get.name.lexeme == "potencia"
    assert printer.print(expr_get) == "(. (. auto motor) potencia)"

    expr_set = parse_expression("this.x = super.calcular(1)")
    assert isinstance(expr_set, SetExpr)
    assert isinstance(expr_set.object, ThisExpr)
    assert expr_set.name.lexeme == "x"
    assert printer.print(expr_set) == "(= this.x ((super calcular) 1.0))"

    expr_super = parse_expression("super.init")
    assert isinstance(expr_super, SuperExpr)
    assert expr_super.method.lexeme == "init"


def test_class_declaration_parsing():
    source = """
    class Perro < Animal {
        init(nombre) {
            this.nombre = nombre;
        }
        ladrar() {
            print "Guau";
        }
    }
    """
    scanner = Scanner(source)
    parser = Parser(scanner.scan_tokens())
    stmts = parser.parse()

    assert len(stmts) == 1
    cls = stmts[0]
    assert isinstance(cls, ClassDecl)
    assert cls.name.lexeme == "Perro"
    assert cls.superclass is not None
    assert cls.superclass.name.lexeme == "Animal"
    assert len(cls.methods) == 2
    assert cls.methods[0].name.lexeme == "init"
    assert cls.methods[1].name.lexeme == "ladrar"
