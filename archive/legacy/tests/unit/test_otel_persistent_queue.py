from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COLLECTOR_CONFIG = ROOT / "monitoring" / "otel-collector-config.yaml"
COMPOSE_FILE = ROOT / "docker-compose.yml"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_backend_outage_queues_telemetry_exports_on_disk():
    config = read(COLLECTOR_CONFIG)

    assert "file_storage:" in config
    assert "directory: /var/lib/otelcol/file_storage" in config
    assert "sending_queue:" in config
    assert "enabled: true" in config
    assert "storage: file_storage" in config
    assert "queue_size: 10000" in config
    assert "retry_on_failure:" in config


def test_collector_restart_reuses_persistent_queue_directory():
    compose = read(COMPOSE_FILE)
    config = read(COLLECTOR_CONFIG)

    assert "otel-collector:" in compose
    assert "otel/opentelemetry-collector-contrib" in compose
    assert "./.data/otelcol/file_storage:/var/lib/otelcol/file_storage" in compose
    assert "./monitoring/otel-collector-config.yaml:/etc/otelcol/config.yaml:ro" in compose
    assert "directory: /var/lib/otelcol/file_storage" in config
    assert "profiles:" in compose
    assert "- telemetry" in compose


def test_queue_drains_after_backend_recovery_without_audit_pipeline_changes():
    config = read(COLLECTOR_CONFIG)
    compose = read(COMPOSE_FILE)

    assert "endpoint: ${env:OTEL_EXPORTER_OTLP_BACKEND_ENDPOINT}" in config
    assert "processors:\n  batch:" in config
    assert "exporters:\n  otlp:" in config
    assert "exporters:\n        - otlp" in config
    assert "max_elapsed_time: 0s" in config
    assert "audit" not in config.lower()
    assert "OTEL_EXPORTER_OTLP_ENDPOINT: http://otel-collector:4317" in compose
