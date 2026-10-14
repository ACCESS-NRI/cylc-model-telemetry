"""Load telemetry configuration and post run telemetry for ACCESS-RAM3 suites."""

from datetime import datetime, timezone
import json
import logging
import os
from importlib.resources import files
from pathlib import Path
from typing import Any, Optional, TypedDict

import jsonschema
import requests

logger = logging.getLogger(__name__)

# Environment variables set by the containerised environment
TELEMETRY_CONFIG_PATH_ENV = "CYLC_MODEL_TELEMETRY_CONFIG_PATH"
TELEMETRY_ENV_VERSION_ENV = "CYLC_MODEL_TELEMETRY_ENV_VERSION"

SCHEMA_RESOURCE = files("cylc_model_telemetry") / "telemetry_config.schema.json"

REQUEST_TIMEOUT = 10
# Version of the telemetry payload format, not the package
TELEMETRY_VERSION = "1.0.0"


class TelemetryConfig(TypedDict, total=False):
    version: str
    telemetry_url: str
    telemetry_token: str
    telemetry_service_name: str
    hostname: str
    telemetry_proxy_url: str


class TelemetryError(Exception):
    """Any failure loading configuration or sending telemetry."""


def load_config() -> Optional[TelemetryConfig]:
    """Load and schema-validate the external telemetry configuration.

    Returns None if telemetry is not configured (environment variable
    unset or empty). Raises TelemetryError if telemetry is configured
    but the configuration file is missing or invalid.
    """
    config_path_str = os.environ.get(TELEMETRY_CONFIG_PATH_ENV)
    if not config_path_str:
        return None

    config_path = Path(config_path_str)
    if not config_path.is_file():
        raise TelemetryError(
            f"No config file at path given by {TELEMETRY_CONFIG_PATH_ENV}: {config_path}"
        )

    try:
        config = json.loads(config_path.read_text())
    except json.JSONDecodeError as e:
        raise TelemetryError(f"Invalid JSON in {config_path}: {e}") from e

    schema = json.loads(SCHEMA_RESOURCE.read_text())
    try:
        jsonschema.validate(instance=config, schema=schema)
    except jsonschema.ValidationError as e:
        raise TelemetryError(
            f"{config_path} does not follow the required schema: {e.message}"
        ) from e

    return config


def post_telemetry(
    config: TelemetryConfig,
    data: dict[str, Any],
    timeout: int = REQUEST_TIMEOUT,
) -> None:
    """Post telemetry data to the configured endpoint.

    Raises TelemetryError on any request failure or error response.
    """
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Token {config['telemetry_token']}",
    }
    payload = {
        "service": config["telemetry_service_name"],
        "version": TELEMETRY_VERSION,
        "telemetry": data,
    }
    proxy_url = config.get("telemetry_proxy_url")
    proxies = {"https": proxy_url, "http": proxy_url} if proxy_url else None

    try:
        response = requests.post(
            config["telemetry_url"],
            json=payload,
            headers=headers,
            timeout=timeout,
            proxies=proxies,
        )
    except requests.exceptions.RequestException as e:
        raise TelemetryError(f"Request failed: {e}") from e

    if response.status_code >= 400:
        try:
            body: Any = response.json()
        except ValueError:
            body = response.text
        raise TelemetryError(f"Status {response.status_code}: {body}")


def record_telemetry(run_info: dict[str, Any]) -> None:
    """Post run telemetry if configured.

    Best-effort: failures are logged, never raised, so telemetry
    problems cannot fail the suite task.
    """
    try:
        config = load_config()
        if config is None:
            logger.info("Telemetry not configured; skipping.")
            return
        payload = {
            **run_info,
            "timestamp":datetime.now(timezone.utc).isoformat(),
            "hostname": config["hostname"],
            "env_version": os.environ.get(TELEMETRY_ENV_VERSION_ENV),
        }
        post_telemetry(config, payload)
        logger.info("Telemetry sent.")
    except TelemetryError as e:
        logger.warning("Telemetry failed: %s", e)