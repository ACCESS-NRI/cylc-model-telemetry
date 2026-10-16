"""CLI entrypoint for sending ACCESS-RAM3 run telemetry from a cylc task."""

import argparse
import logging
import os
import sys
from typing import Optional

from .client import record_telemetry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cylc-model-telemetry",
        description="Send cylc suite run telemetry for a model, if configured.",
    )
    parser.add_argument(
        "--model", 
        default="access-ram3",
        help="Model name, default is 'access-ram3'"
    )
    parser.add_argument(
        "--suite-name",
        default=os.environ.get("CYLC_SUITE_NAME"),
        help="Suite Name/ID, (default: $CYLC_SUITE_NAME)"
    )
    parser.add_argument(
        "--cylc-version",
        default=os.environ.get("CYLC_VERSION"),
        help="Cylc version (default: $CYLC_VERSION)"
    )
    parser.add_argument(
        "--build-mode",
        default=os.environ.get("BUILD_MODE"),
        help="Build mode used for the model, e.g. spack"
    )
    parser.add_argument(
        "--spack-version",
        default=os.environ.get("SPACK_VERSION"),
        help="Spack model build version if a spack build was used (default: $BUILD_MODE)"
    )
    parser.add_argument(
        "--fail-on-error",
        action="store_true",
        help="Exit with status 1 if telemetry cannot be sent (default: $SPACK_VERSION)",
    )
    # In future, could add --extra KEY=VALUE list for model-specific options
    return parser


def find_missing_args(args: argparse.Namespace) -> list[str]:
    """Return descriptions of required arguments that are unset or empty."""
    missing = [
        name for name, value in [
            ("--suite-name (or CYLC_SUITE_NAME)", args.suite_name),
            ("--cylc-version (or CYLC_VERSION)", args.cylc_version),
            ("--build-mode (or BUILD_MODE)", args.build_mode),
        ]
        if not value
    ]
    if args.build_mode == "spack" and not args.spack_version:
        missing.append("--spack-version (or SPACK_VERSION) for spack builds")
    return missing


def main(argv: Optional[list[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    args = build_parser().parse_args(argv)

    missing = find_missing_args(args)
    if missing:
        logging.error("Missing required telemetry values: %s", ", ".join(missing))
        return 1 if args.fail_on_error else 0

    # Check for required values
    run_info = {
        k: v for k, v in vars(args).items()
          if v is not None and k != "fail_on_error"
    }

    try: 
        record_telemetry(run_info)
    except Exception as e:
        logging.error("Telemetry failed: %s", e)
        if args.fail_on_error:
            return 1

    # For testing purposes - as telemetry is at the end of the suite,
    # setting the job exit status to 1 would allow easy re-running of the job
    # return 1 

    # By default, telemetry is best-effort; never fail the suite task
    return 0


if __name__ == "__main__":
    sys.exit(main())