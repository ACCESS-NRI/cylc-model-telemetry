# cylc-model-telemetry

A small client for sending model run telemetry from Cylc
suites to the ACCESS-NRI tracking services.

It is designed to run as the final task in a suite on the localhost
(login/persistent session) and POST a JSON record of run information —
user, model, suite name, build mode, spack version — to a telemetry ingestion endpoint.

Telemetry is **best-effort and opt-in**: if telemetry is not configured,
or sending fails for any reason, the task logs a warning and exits
successfully. Telemetry can never fail a suite run.

## How it works

1. The suite's telemetry task invokes the `cylc-model-telemetry` command
   with run information passed as CLI arguments.
2. The client looks up the environment variable
   `CYLC_MODEL_TELEMETRY_CONFIG_PATH`. If unset, telemetry is skipped.
3. The external configuration file at that path (endpoint URL, token,
   service name — see below) is loaded and validated against a JSON schema.
4. The run information is POSTed to the configured endpoint.

Run data is passed as CLI arguments and deployment details come from the environment variables. The configuration file is
deployed separately from the package so that the endpoint URL and token
can be updated or rotated without a new package release.

## Installation

```sh
pip install cylc-model-telemetry
```

On Gadi, the package will be installed in a conda environment under
`/g/data/vk83/modules`, with `CYLC_MODEL_TELEMETRY_CONFIG_PATH`
and `CYLC_MODEL_TELEMETRY_ENV_VERSION` set by the module/environment. #TODO: Update with exact deployment

## Usage

```
usage: cylc-model-telemetry [-h] --model MODEL --user USER --suite-name SUITE_NAME
                            [--cylc-version CYLC_VERSION]
                            [--build-mode BUILD_MODE]
                            [--spack-version SPACK_VERSION]
```

`--model` identifies which model produced the record (e.g. `access-ram3`)
— all models share one telemetry service and are distinguished by this
field.

Example telemetry task in `flow.cylc` / `suite.rc`:

```ini
[[record_telemetry]]
    inherit = HOST_LOCAL
    pre-script = module load cylc-model-telemetry
    script = """
        cylc-model-telemetry \
            --model access-ram3 \
            --user "$USER" \
            --suite-name "$CYLC_SUITE_NAME" \
            --cylc-version "$CYLC_VERSION" \
            --build-mode "{{ BUILD_MODE }}"{% if BUILD_MODE == 'spack' %} \
            --spack-version "{{ SPACK_VERSION }}"{% endif %}
    """
```

## Configuration file

The file pointed to by `CYLC_MODEL_TELEMETRY_CONFIG_PATH` must follow
[telemetry_config.schema.json](src/cylc_model_telemetry/telemetry_config.schema.json):

```json
{
    "version": "1.0.0",
    "telemetry_url": "https://<tracking-services-host>/api/cylc-model/ingest_raw/",
    "telemetry_proxy_url": "<optional proxy URL>",
    "telemetry_token": "<token>",
    "telemetry_service_name": "cylc-model",
    "hostname": "gadi"
}
```

| Field | Required | Description |
|---|---|---|
| `telemetry_url` | yes | Ingestion endpoint URL |
| `telemetry_token` | yes | Authorization token for the endpoint |
| `telemetry_service_name` | yes | Service name recorded with each payload |
| `hostname` | yes | HPC host name added to each payload |
| `telemetry_proxy_url` | no | HTTP(S) proxy for the request |
| `version` | no | Version of the configuration file |

A deployment template is provided in
[templates/telemetry_config.json](templates/telemetry_config.json).

#TODO: Update this section with how this file is deployed.

## Payload format

```json
{
    "service": "cylc-model",
    "version": "1.0.0",
    "telemetry": {
        "model": "access-ram3",
        "user": "abc123",
        "suite_name": "u-by395",
        "cylc_version": "7.3.0",
        "build_mode": "spack",
        "spack_version": "2024.12.0",
        "hostname": "gadi",
        "env_version": "2026.10",
        "timestamp": "2026-10-01T12:00:00Z"
    }
}
```

`version` is the telemetry payload format version, used by the
server-side parser.

## Development

```sh
pip install -e '.[test]'
pytest
```

## License

Apache License 2.0 (see [LICENSE](LICENSE))