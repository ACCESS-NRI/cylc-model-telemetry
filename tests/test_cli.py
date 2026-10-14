from unittest.mock import patch

import pytest

from cylc_model_telemetry import cli

REQUIRED = ["--model", "access-ram3", "--user", "abc123", "--suite-name", "u-by395"]


def test_main_passes_args_as_run_info():
    with patch.object(cli, "record_telemetry") as mock_record:
        exit_code = cli.main(REQUIRED)

    assert exit_code == 0
    mock_record.assert_called_once_with(
        {"model": "access-ram3", "user": "abc123", "suite_name": "u-by395"}
    )


def test_main_passes_optional_args():
    with patch.object(cli, "record_telemetry") as mock_record:
        cli.main(
            REQUIRED
            + [
                "--cylc-version", "7.3.0",
                "--build-mode", "spack",
                "--spack-version", "0.22",
            ]
        )

    run_info = mock_record.call_args[0][0]
    assert run_info["cylc_version"] == "7.3.0"
    assert run_info["build_mode"] == "spack"
    assert run_info["spack_version"] == "0.22"


def test_main_omits_unset_optional_args():
    with patch.object(cli, "record_telemetry") as mock_record:
        cli.main(REQUIRED)

    run_info = mock_record.call_args[0][0]
    assert "cylc_version" not in run_info
    assert "build_mode" not in run_info
    assert "spack_version" not in run_info


@pytest.mark.parametrize("missing", ["--model", "--user", "--suite-name"])
def test_main_requires_core_args(missing):
    args = list(REQUIRED)
    i = args.index(missing)
    del args[i : i + 2]

    with patch.object(cli, "record_telemetry") as mock_record:
        with pytest.raises(SystemExit):
            cli.main(args)

    mock_record.assert_not_called()