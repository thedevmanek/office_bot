import json

from object_detector.event_log import (
    EventLogConfig,
    JsonlEventLogger,
    event_log_config_from_params,
)


class RecordingLogger:
    def __init__(self):
        self.warnings = []

    def warning(self, message):
        self.warnings.append(message)


def test_event_logger_writes_jsonl_common_fields(tmp_path):
    path = tmp_path / "events.jsonl"
    logger = JsonlEventLogger(
        EventLogConfig(
            enabled=True,
            log_path=str(path),
            run_id="run-001",
            scenario="object_search_approach",
        )
    )

    assert logger.record(
        "object_localized",
        {
            "track_id": 7,
            "class": "chair",
            "x": 1.25,
            "y": -0.5,
            "position_confidence": 0.8,
        },
        t=12.3456789,
    )
    logger.close()

    events = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
    ]
    assert events == [
        {
            "run_id": "run-001",
            "t": 12.345679,
            "event": "object_localized",
            "scenario": "object_search_approach",
            "track_id": 7,
            "class": "chair",
            "x": 1.25,
            "y": -0.5,
            "position_confidence": 0.8,
        }
    ]


def test_event_log_config_defaults_to_workspace_log_dir():
    config = event_log_config_from_params({})

    assert config.enabled
    assert config.log_dir == "log/events"
    assert config.scenario == "object_search_approach"


def test_event_logger_can_be_disabled(tmp_path):
    path = tmp_path / "disabled.jsonl"
    logger = JsonlEventLogger(EventLogConfig(enabled=False, log_path=str(path)))

    assert not logger.record("tracks_cleared", {"track_count": 1})
    assert not path.exists()


def test_event_logger_uses_run_id_filename_in_log_dir(tmp_path):
    logger = JsonlEventLogger(
        EventLogConfig(enabled=True, log_dir=str(tmp_path), run_id="known-run")
    )

    assert logger.path == tmp_path / "openhri_object_search_known-run.jsonl"
    assert logger.record("track_confirmed", {"track_id": 3}, t=1.0)
    logger.close()
    assert logger.path.exists()


def test_event_logger_disables_when_path_cannot_be_opened(tmp_path):
    recording_logger = RecordingLogger()
    logger = JsonlEventLogger(
        EventLogConfig(enabled=True, log_path=str(tmp_path)),
        logger=recording_logger,
    )

    assert not logger.enabled
    assert not logger.record("object_localized", {"track_id": 1})
    assert recording_logger.warnings
