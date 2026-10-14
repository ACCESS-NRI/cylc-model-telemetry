import json

import pytest
import requests

from cylc_model_telemetry import client


@pytest.fixture
def valid_config(tmp_path, monkeypatch):
    config = {
        "version": "1.0.0",
        "telemetry_url": "https://example.com/api/ingest/",
        "telemetry_token": "secret",
        "telemetry_service_name": "cylc-model",
        "hostname": "gadi",
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config))
    monkeypatch.setenv(client.TELEMETRY_CONFIG_PATH_ENV, str(config_file))
    return config


def test_load_config_unset_env(monkeypatch):
    monkeypatch.delenv(client.TELEMETRY_CONFIG_PATH_ENV, raising=False)
    assert client.load_config() is None


def test_load_config_empty_env(monkeypatch):
    monkeypatch.setenv(client.TELEMETRY_CONFIG_PATH_ENV, "")
    assert client.load_config() is None


def test_load_config_missing_file(monkeypatch, tmp_path):
    monkeypatch.setenv(client.TELEMETRY_CONFIG_PATH_ENV, str(tmp_path / "nope.json"))
    with pytest.raises(client.TelemetryError, match="No config file"):
        client.load_config()


def test_load_config_invalid_json(monkeypatch, tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text("{not json")
    monkeypatch.setenv(client.TELEMETRY_CONFIG_PATH_ENV, str(config_file))
    with pytest.raises(client.TelemetryError, match="Invalid JSON"):
        client.load_config()


def test_load_config_schema_violation(monkeypatch, tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"telemetry_url": "https://example.com"}))
    monkeypatch.setenv(client.TELEMETRY_CONFIG_PATH_ENV, str(config_file))
    with pytest.raises(client.TelemetryError, match="schema"):
        client.load_config()


def test_load_config_valid(valid_config):
    assert client.load_config() == valid_config


def test_post_telemetry_success(valid_config, requests_mock):
    requests_mock.post(valid_config["telemetry_url"], status_code=201)
    client.post_telemetry(valid_config, {"user": "abc123"})

    request = requests_mock.last_request
    sent = request.json()
    assert sent["service"] == "cylc-model"
    assert sent["version"] == client.TELEMETRY_VERSION
    assert sent["telemetry"] == {"user": "abc123"}
    assert request.headers["Authorization"] == "Token secret"
    assert request.headers["Content-type"] == "application/json"


def test_post_telemetry_error_response(valid_config, requests_mock):
    requests_mock.post(
        valid_config["telemetry_url"], status_code=403, json={"detail": "bad token"}
    )
    with pytest.raises(client.TelemetryError, match="403"):
        client.post_telemetry(valid_config, {})


def test_post_telemetry_error_response_non_json(valid_config, requests_mock):
    requests_mock.post(valid_config["telemetry_url"], status_code=502, text="Bad Gateway")
    with pytest.raises(client.TelemetryError, match="502.*Bad Gateway"):
        client.post_telemetry(valid_config, {})


def test_post_telemetry_request_failure(valid_config, requests_mock):
    requests_mock.post(
        valid_config["telemetry_url"], exc=requests.exceptions.ConnectTimeout
    )
    with pytest.raises(client.TelemetryError, match="Request failed"):
        client.post_telemetry(valid_config, {})


def test_post_telemetry_uses_proxy_when_configured(valid_config, requests_mock):
    config = {**valid_config, "telemetry_proxy_url": "http://proxy.example.com:8005"}
    requests_mock.post(config["telemetry_url"], status_code=201)

    client.post_telemetry(config, {"user": "abc123"})

    assert requests_mock.last_request.proxies == {
        "https": "http://proxy.example.com:8005",
        "http": "http://proxy.example.com:8005",
    }


def test_post_telemetry_no_proxy_by_default(valid_config, requests_mock):
    requests_mock.post(valid_config["telemetry_url"], status_code=201)

    client.post_telemetry(valid_config, {"user": "abc123"})

    assert requests_mock.last_request.proxies == {}


def test_record_telemetry_skips_when_unconfigured(monkeypatch, requests_mock):
    monkeypatch.delenv(client.TELEMETRY_CONFIG_PATH_ENV, raising=False)

    client.record_telemetry({"user": "abc123"})

    assert requests_mock.call_count == 0


def test_record_telemetry_never_raises(monkeypatch, tmp_path):
    monkeypatch.setenv(client.TELEMETRY_CONFIG_PATH_ENV, str(tmp_path / "nope.json"))
    client.record_telemetry({"user": "abc123"})  # misconfigured: logs, no raise


def test_record_telemetry_never_raises_on_error_response(valid_config, requests_mock):
    requests_mock.post(valid_config["telemetry_url"], status_code=500)
    client.record_telemetry({"user": "abc123"})


def test_record_telemetry_adds_config_fields(valid_config, requests_mock, monkeypatch):
    monkeypatch.setenv(client.TELEMETRY_ENV_VERSION_ENV, "2024.01")
    requests_mock.post(valid_config["telemetry_url"], status_code=201)

    client.record_telemetry({"user": "abc123"})

    sent = requests_mock.last_request.json()["telemetry"]
    assert sent["user"] == "abc123"
    assert sent["hostname"] == "gadi"
    assert sent["env_version"] == "2024.01"
    assert "timestamp" in sent


def test_record_telemetry_env_version_unset(valid_config, requests_mock, monkeypatch):
    monkeypatch.delenv(client.TELEMETRY_ENV_VERSION_ENV, raising=False)
    requests_mock.post(valid_config["telemetry_url"], status_code=201)

    client.record_telemetry({"user": "abc123"})

    assert requests_mock.last_request.json()["telemetry"]["env_version"] is None