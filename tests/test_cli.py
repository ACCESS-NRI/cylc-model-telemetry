from unittest.mock import MagicMock

import pytest

from cylc_model_telemetry import cli
from cylc_model_telemetry.client import TelemetryError

ENV_VARS = ["CYLC_SUITE_NAME", "CYLC_VERSION", "BUILD_MODE", "SPACK_VERSION"]

BASE_ARGS = [
    "--suite-name", "suite-x",
    "--cylc-version", "7.3.0",
    "--build-mode", "custom",
]
SPACK_ARGS = [
    "--suite-name", "suite-x",
    "--cylc-version", "7.3.0",
    "--build-mode", "spack",
    "--spack-version", "0.20.1",
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def recorder(monkeypatch):
    fake = MagicMock(return_value=None)
    monkeypatch.setattr(cli, "record_telemetry", fake)
    return fake


def test_defaults_read_env(monkeypatch):
    monkeypatch.setenv("CYLC_SUITE_NAME", "suite-env")
    monkeypatch.setenv("CYLC_VERSION", "7.3.0")
    monkeypatch.setenv("BUILD_MODE", "spack")
    monkeypatch.setenv("SPACK_VERSION", "0.20.1")
    args = cli.build_parser().parse_args([])
    assert args.suite_name == "suite-env"
    assert args.cylc_version == "7.3.0"
    assert args.build_mode == "spack"
    assert args.spack_version == "0.20.1"


def test_args_override_env(monkeypatch):
    monkeypatch.setenv("CYLC_SUITE_NAME", "suite-env")
    args = cli.build_parser().parse_args(["--suite-name", "suite-arg"])
    assert args.suite_name == "suite-arg"


def test_find_missing_args_empty_when_all_set():
    args = cli.build_parser().parse_args(BASE_ARGS)
    assert cli.find_missing_args(args) == []


def test_find_missing_args_reports_unset_and_empty():
    args = cli.build_parser().parse_args(["--suite-name", "", "--build-mode", "custom"])
    missing = cli.find_missing_args(args)
    assert any("--suite-name" in m for m in missing)
    assert any("--cylc-version" in m for m in missing)
    assert not any("--build-mode" in m for m in missing)


def test_find_missing_args_requires_spack_version_for_spack():
    args = cli.build_parser().parse_args(
        ["--suite-name", "s", "--cylc-version", "7.3.0", "--build-mode", "spack"]
    )
    assert any("--spack-version" in m for m in cli.find_missing_args(args))


def test_find_missing_args_no_spack_version_needed_for_other_modes():
    args = cli.build_parser().parse_args(BASE_ARGS)
    assert cli.find_missing_args(args) == []


def test_main_sends_run_info_without_fail_flag(recorder):
    assert cli.main(SPACK_ARGS) == 0
    recorder.assert_called_once()
    assert recorder.call_args.args[0] == {
        "model": "access-ram3",
        "suite_name": "suite-x",
        "cylc_version": "7.3.0",
        "build_mode": "spack",
        "spack_version": "0.20.1",
    }


def test_main_excludes_fail_flag_from_payload(recorder):
    assert cli.main(BASE_ARGS + ["--fail-on-error"]) == 0
    assert "fail_on_error" not in recorder.call_args.args[0]


def test_main_omits_unset_spack_version(recorder):
    assert cli.main(BASE_ARGS) == 0
    assert "spack_version" not in recorder.call_args.args[0]


def test_main_missing_value_skips_send_by_default(recorder):
    assert cli.main(["--cylc-version", "7.3.0", "--build-mode", "custom"]) == 0
    recorder.assert_not_called()


def test_main_missing_value_fails_with_flag(recorder):
    args = ["--cylc-version", "7.3.0", "--build-mode", "custom", "--fail-on-error"]
    assert cli.main(args) == 1
    recorder.assert_not_called()


def test_main_missing_spack_version_fails_with_flag(recorder):
    args = [
        "--suite-name", "s",
        "--cylc-version", "7.3.0",
        "--build-mode", "spack",
        "--fail-on-error",
    ]
    assert cli.main(args) == 1
    recorder.assert_not_called()


def test_main_telemetry_error_warns_by_default(recorder):
    recorder.side_effect = TelemetryError("boom")
    assert cli.main(BASE_ARGS) == 0


def test_main_telemetry_error_fails_with_flag(recorder):
    recorder.side_effect = TelemetryError("boom")
    assert cli.main(BASE_ARGS + ["--fail-on-error"]) == 1