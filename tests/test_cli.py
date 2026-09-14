import sys
from unittest.mock import patch
import pytest
from lox.errors import DiagnosticReporter, LoxRuntimeError
from lox.cli import LoxCLI, main


def test_diagnostic_reporter_initial_state():
    reporter = DiagnosticReporter()
    assert not reporter.had_error
    assert not reporter.had_runtime_error


def test_diagnostic_reporter_error_tracking():
    reporter = DiagnosticReporter()
    reporter.report_error(1, "", "Unexpected token")
    assert reporter.had_error
    assert not reporter.had_runtime_error

    reporter.reset()
    assert not reporter.had_error


def test_diagnostic_reporter_runtime_error():
    reporter = DiagnosticReporter()
    error = LoxRuntimeError("Operando inválido", line=10)
    reporter.report_runtime_error(error)
    assert reporter.had_runtime_error
    assert not reporter.had_error


def test_cli_instantiation():
    cli = LoxCLI()
    assert cli.diagnostics is not None


def test_cli_run_file_non_existent(capsys):
    cli = LoxCLI()
    with pytest.raises(SystemExit) as exc_info:
        cli.run_file("archivo_fantasma_12345.lox")
    assert exc_info.value.code == 66
    _, stderr = capsys.readouterr()
    assert "No se pudo abrir el archivo" in stderr


def test_cli_run_file_existing(tmp_path):
    temp_file = tmp_path / "test.lox"
    temp_file.write_text('print "Hola Lox";', encoding="utf-8")
    
    cli = LoxCLI()
    cli.run_file(str(temp_file))
    assert not cli.diagnostics.had_error
    assert not cli.diagnostics.had_runtime_error


def test_cli_main_too_many_arguments(capsys):
    with patch.object(sys, "argv", ["pylox", "uno.lox", "dos.lox"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 64
        _, stderr = capsys.readouterr()
        assert "Uso: pylox [script.lox]" in stderr


