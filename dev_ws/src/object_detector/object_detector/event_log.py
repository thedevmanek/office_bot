import json
import math
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from threading import Lock


@dataclass(frozen=True)
class EventLogConfig:
    enabled: bool = True
    log_dir: str = "log/events"
    log_path: str = ""
    run_id: str = ""
    scenario: str = "object_search_approach"
    filename_prefix: str = "openhri_object_search"


def event_log_config_from_params(params):
    return EventLogConfig(
        enabled=bool(params.get("event_log_enabled", True)),
        log_dir=str(params.get("event_log_dir", "log/events")),
        log_path=str(params.get("event_log_path", "")),
        run_id=str(params.get("event_log_run_id", "")),
        scenario=str(params.get("event_log_scenario", "object_search_approach")),
    )


class JsonlEventLogger:
    def __init__(self, config=None, logger=None):
        self.config = config or EventLogConfig()
        self.logger = logger
        self.enabled = bool(self.config.enabled)
        self.run_id = self.config.run_id or default_run_id()
        self.scenario = self.config.scenario
        self.path = None
        self._file = None
        self._lock = Lock()
        self._start_time = time.monotonic()

        if self.enabled:
            self._open()

    def record(self, event, fields=None, t=None, **extra_fields):
        if not self.enabled or self._file is None:
            return False

        payload = {
            "run_id": self.run_id,
            "t": round(float(t) if t is not None else self._elapsed_seconds(), 6),
            "event": event,
            "scenario": self.scenario,
        }
        if fields:
            payload.update(fields)
        payload.update(extra_fields)
        payload = _json_ready(payload)

        try:
            line = json.dumps(payload, sort_keys=False, separators=(",", ":"))
            with self._lock:
                self._file.write(line + "\n")
                self._file.flush()
            return True
        except (OSError, TypeError, ValueError) as exc:
            self._disable(f"Could not write object search event log: {exc}")
            return False

    def close(self):
        with self._lock:
            if self._file is not None:
                self._file.close()
                self._file = None

    def _open(self):
        try:
            self.path = self._resolve_path()
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._file = self.path.open("a", encoding="utf-8", buffering=1)
        except OSError as exc:
            self._disable(f"Could not open object search event log: {exc}")

    def _resolve_path(self):
        if self.config.log_path:
            return Path(self.config.log_path).expanduser()
        filename = f"{self.config.filename_prefix}_{self.run_id}.jsonl"
        return Path(self.config.log_dir).expanduser() / filename

    def _elapsed_seconds(self):
        return time.monotonic() - self._start_time

    def _disable(self, message):
        self.enabled = False
        self.close()
        if self.logger is not None:
            self.logger.warning(message)


def default_run_id():
    timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    return f"{timestamp}-{uuid.uuid4().hex[:8]}"


def _json_ready(value):
    if isinstance(value, dict):
        return {
            str(key): _json_ready(item)
            for key, item in value.items()
            if item is not None
        }
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    if hasattr(value, "item"):
        return _json_ready(value.item())
    return str(value)
