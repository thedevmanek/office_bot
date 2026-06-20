import json
import math
import os
import platform
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunManifestConfig:
    enabled: bool = True
    manifest_dir: str = "log/manifests"
    manifest_path: str = ""
    run_id: str = ""
    scenario: str = "object_search_approach"
    trial_id: str = ""
    world: str = "office_world"
    robot_start_pose: str = ""
    target_class: str = ""
    target_object_pose: str = ""
    random_seed: str = ""
    notes: str = ""
    recipe_path: str = ""
    run_dir: str = ""
    filename_prefix: str = "openhri_object_search"


def run_manifest_config_from_params(params):
    return RunManifestConfig(
        enabled=bool(params.get("run_manifest_enabled", True)),
        manifest_dir=str(params.get("run_manifest_dir", "log/manifests")),
        manifest_path=str(params.get("run_manifest_path", "")),
        run_id=str(params.get("event_log_run_id", "")),
        scenario=str(params.get("event_log_scenario", "object_search_approach")),
        trial_id=str(params.get("run_manifest_trial_id", "")),
        world=str(params.get("run_manifest_world", "office_world")),
        robot_start_pose=str(params.get("run_manifest_robot_start_pose", "")),
        target_class=str(params.get("run_manifest_target_class", "")),
        target_object_pose=str(params.get("run_manifest_target_object_pose", "")),
        random_seed=str(params.get("run_manifest_random_seed", "")),
        notes=str(params.get("run_manifest_notes", "")),
        recipe_path=str(params.get("run_manifest_recipe_path", "")),
        run_dir=str(params.get("run_manifest_run_dir", "")),
    )


class RunManifestWriter:
    def __init__(
        self,
        config,
        run_id,
        params,
        event_log_path=None,
        logger=None,
        env=None,
    ):
        self.config = config or RunManifestConfig()
        self.run_id = run_id or self.config.run_id or "unknown-run"
        self.params = dict(params or {})
        self.event_log_path = event_log_path
        self.logger = logger
        self.env = dict(env or os.environ)
        self.enabled = bool(self.config.enabled)
        self.path = None

    def write(self):
        if not self.enabled:
            return False

        try:
            self.path = self._resolve_path()
            manifest = self.build_manifest()
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self.path.with_name(self.path.name + ".tmp")
            tmp_path.write_text(to_yaml(manifest), encoding="utf-8")
            tmp_path.replace(self.path)
            return True
        except OSError as exc:
            self._disable(f"Could not write run manifest: {exc}")
            return False

    def build_manifest(self):
        repo_root = find_repo_root(self.env)
        git = git_context(repo_root)
        manifest_path = str(self.path) if self.path is not None else None
        event_log_path = (
            str(self.event_log_path)
            if self.event_log_path is not None
            else None
        )

        return _json_ready(
            {
                "manifest_version": 1,
                "run_id": self.run_id,
                "trial_id": self.config.trial_id or None,
                "created_at_utc": utc_now(),
                "scenario": {
                    "name": self.config.scenario,
                    "world": self.config.world or None,
                    "robot_start_pose": parse_structured_text(
                        self.config.robot_start_pose
                    ),
                    "target_object": {
                        "class": self.config.target_class or None,
                        "pose": parse_structured_text(
                            self.config.target_object_pose
                        ),
                    },
                    "random_seed": parse_scalar(self.config.random_seed),
                    "notes": self.config.notes or None,
                },
                "runtime": runtime_context(self.env),
                "code": {
                    "repo_root": str(repo_root) if repo_root else None,
                    "git_commit": git.get("commit"),
                    "git_branch": git.get("branch"),
                    "git_dirty": git.get("dirty"),
                },
                "artifacts": {
                    "run_dir": self.config.run_dir or None,
                    "trial_recipe_path": self.config.recipe_path or None,
                    "run_manifest_path": manifest_path,
                    "event_log_path": event_log_path,
                    "detector_params_path": self.env.get(
                        "OPENHRI_DETECTOR_PARAMS"
                    ),
                    "detector_param_args": self.env.get(
                        "OPENHRI_DETECTOR_PARAM_ARGS"
                    ),
                },
                "config": {
                    "object_detector": self.params,
                },
            }
        )

    def trial_start_fields(self):
        fields = {
            "trial_id": self.config.trial_id or None,
            "world": self.config.world or None,
            "target_class": self.config.target_class or None,
            "robot_start_pose": parse_structured_text(
                self.config.robot_start_pose
            ),
            "target_object_pose": parse_structured_text(
                self.config.target_object_pose
            ),
            "random_seed": parse_scalar(self.config.random_seed),
            "trial_recipe_path": self.config.recipe_path or None,
            "run_dir": self.config.run_dir or None,
            "run_manifest_path": str(self.path) if self.path is not None else None,
        }
        return _json_ready(fields)

    def _resolve_path(self):
        if self.config.manifest_path:
            return Path(self.config.manifest_path).expanduser()
        filename = f"{self.config.filename_prefix}_{self.run_id}_manifest.yaml"
        return Path(self.config.manifest_dir).expanduser() / filename

    def _disable(self, message):
        self.enabled = False
        if self.logger is not None:
            self.logger.warning(message)


def utc_now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def runtime_context(env):
    return {
        "ros_distro": env.get("ROS_DISTRO"),
        "ros_version": env.get("ROS_VERSION"),
        "platform": env.get("OPENHRI_PLATFORM"),
        "container": {
            "image": env.get("OPENHRI_IMAGE"),
            "image_digest": env.get("OPENHRI_IMAGE_DIGEST"),
            "hostname": env.get("HOSTNAME") or socket.gethostname(),
        },
        "python_version": sys.version.split()[0],
        "system": platform.system(),
        "machine": platform.machine(),
    }


def find_repo_root(env=None):
    env = env or os.environ
    candidates = []
    for name in ("OPENHRI_REPO_ROOT", "GITHUB_WORKSPACE"):
        value = env.get(name)
        if value:
            candidates.append(Path(value))

    ws = env.get("OPENHRI_WS")
    if ws:
        candidates.append(Path(ws).parent)

    candidates.append(Path.cwd())
    candidates.append(Path(__file__).resolve())

    for candidate in candidates:
        for path in [candidate, *candidate.parents]:
            if (path / ".git").exists():
                return path
    return None


def git_context(repo_root):
    if repo_root is None:
        return {"commit": None, "branch": None, "dirty": None}

    commit = _git(repo_root, "rev-parse", "HEAD")
    branch = _git(repo_root, "rev-parse", "--abbrev-ref", "HEAD")
    status = _git(repo_root, "status", "--short")
    return {
        "commit": commit,
        "branch": branch,
        "dirty": bool(status) if status is not None else None,
    }


def _git(repo_root, *args):
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=2.0,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def parse_structured_text(value):
    text = str(value or "").strip()
    if not text:
        return None

    try:
        return _json_ready(json.loads(text))
    except json.JSONDecodeError:
        pass

    parts = [part.strip() for part in text.split(",") if part.strip()]
    if parts and all(("=" in part or ":" in part) for part in parts):
        parsed = {}
        for part in parts:
            separator = "=" if "=" in part else ":"
            key, raw_value = part.split(separator, 1)
            parsed[key.strip()] = parse_scalar(raw_value.strip())
        return parsed

    return text


def parse_scalar(value):
    text = str(value or "").strip()
    if not text:
        return None
    lowered = text.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in ("none", "null"):
        return None
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def to_yaml(value):
    return "\n".join(_yaml_lines(value, 0)) + "\n"


def _yaml_lines(value, indent):
    prefix = " " * indent
    if isinstance(value, dict):
        if not value:
            return [prefix + "{}"]
        lines = []
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}{key}:")
                lines.extend(_yaml_lines(item, indent + 2))
            else:
                lines.append(f"{prefix}{key}: {_yaml_scalar(item)}")
        return lines

    if isinstance(value, list):
        if not value:
            return [prefix + "[]"]
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(prefix + "-")
                lines.extend(_yaml_lines(item, indent + 2))
            else:
                lines.append(f"{prefix}- {_yaml_scalar(item)}")
        return lines

    return [prefix + _yaml_scalar(value)]


def _yaml_scalar(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value))


def _json_ready(value):
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    if hasattr(value, "item"):
        return _json_ready(value.item())
    return str(value)
