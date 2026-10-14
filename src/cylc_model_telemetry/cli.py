"""CLI entrypoint for sending ACCESS-RAM3 run telemetry from a cylc task."""

import argparse
import logging
import sys
from typing import Optional

from .client import record_telemetry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cylc-model-telemetry",
        description="Send cylc suite run telemetry for a model, if configured.",
    )
    parser.add_argument("--model", required=True, help="Model name, e.g. access-ram3")
    parser.add_argument("--user", required=True, help="Username running the suite")
    parser.add_argument("--suite-name", required=True, help="Suite Name/ID, e.g. u-by395")
    parser.add_argument("--cylc-version", help="Cylc engine version")
    parser.add_argument("--build-mode", help="Build mode used for the model, e.g. spack")
    parser.add_argument(
        "--spack-version", help="Spack model build version, if a spack build was used"
    )
    # In future, could add --extra KEY=VALUE list for model-specific options
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    args = build_parser().parse_args(argv)
    run_info = {k: v for k, v in vars(args).items() if v is not None}
    record_telemetry(run_info)
    # Telemetry is best-effort; never fail the suite task
    #return 0
    return 1 # For testing purposes


if __name__ == "__main__":
    sys.exit(main())