# cylc-model-telemetry

A small client for sending model run telemetry from Cylc
suites to the ACCESS-NRI tracking services.

It is designed to run as the final task in a suite on the localhost
(login/persistent session) and POST a JSON record of run information
(user, model, suite name, build mode, spack version) to a telemetry ingestion endpoint.

Telemetry is **best-effort and opt-in** by default: if telemetry is not configured,
or sending fails, the task logs a warning and exits successfully.
With `--fail-on-error`, a missing required value or a failed send makes the task exit with status 1.

## How it works

1. The suite's telemetry task invokes the `cylc-model-telemetry` command.
   Run information is taken from command-line arguments, falling back to
   environment variables.
2. The CLI checks that the required values are set: suite name, Cylc version,
   build mode, and spack version for spack builds. Missing values are logged
   as errors and telemetry is not sent.
3. The client looks up the environment variable
   `CYLC_MODEL_TELEMETRY_CONFIG_PATH`. If unset, telemetry is skipped.
4. The external configuration file at that path (endpoint URL, token,
   service name, see below) is loaded and validated against a JSON schema.
5. The client adds the `user` (the username of the process), `timestamp`,
   `hostname` and `env_version` fields, and POSTs the record to the configured endpoint.

The configuration file is deployed separately from the package so that the
endpoint URL and token can be updated or rotated without a new package release.

## Installation

```sh
pip install cylc-model-telemetry
```

On Gadi, the package will be installed in a conda environment under
`/g/data/vk83/modules`, with `CYLC_MODEL_TELEMETRY_CONFIG_PATH`
and `CYLC_MODEL_TELEMETRY_ENV_VERSION` set by the module/environment. #TODO: Update with exact deployment

## Usage

```
usage: cylc-model-telemetry [-h] [--model MODEL] [--suite-name SUITE_NAME]
                            [--cylc-version CYLC_VERSION]
                            [--build-mode BUILD_MODE]
                            [--spack-version SPACK_VERSION]
                            [--fail-on-error]
```

| Argument | Default | Required | Description |
|---|---|---|---|
| `--model` | `access-ram3` | no | Model that produced the record. All models share one telemetry service and are distinguished by this field. |
| `--suite-name` | `$CYLC_SUITE_NAME` | yes | Suite name or ID |
| `--cylc-version` | `$CYLC_VERSION` | yes | Cylc version |
| `--build-mode` | `$BUILD_MODE` | yes | Build mode, e.g. `spack` |
| `--spack-version` | `$SPACK_VERSION` | if build mode is `spack` | Spack model build version |
| `--fail-on-error` | off | no | Exit with status 1 if a required value is missing or telemetry cannot be sent |

Telemetry that is not configured (`CYLC_MODEL_TELEMETRY_CONFIG_PATH` unset) is
always skipped without error.

Example telemetry task in `flow.cylc` / `suite.rc`:

```ini
[[record_telemetry]]
    inherit = HOST_LOCAL
    pre-script = module load cylc-model-telemetry
    script = "cylc-model-telemetry"
    [[[environment]]]
        BUILD_MODE="{{ BUILD_MODE }}"
        SPACK_VERSION="{{ SPACK_VERSION }}"
```

The suite name and Cylc version are read from `$CYLC_SUITE_NAME` and
`$CYLC_VERSION`, which Cylc sets in the task environment.

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
server-side parser. `user` is set by the client and is not trusted as an
identity. The server should validate it.

## Development

```sh
pip install -e '.[test]'
pytest
```

## License

Apache License 2.0 (see [LICENSE](LICENSE))