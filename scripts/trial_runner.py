#!/usr/bin/env python3
"""Prepare and start reproducible object-search trials."""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path, PurePosixPath


CONTAINER_REPO_ROOT = PurePosixPath("/workspace/openhri-office")
DEFAULT_IMAGE = "ghcr.io/thedevmanek/openhri-office:latest-preview"
DEFAULT_DETECTOR_PARAMS = (
    "/workspace/openhri-office/dev_ws/src/object_detector/config/"
    "object_detector.yaml"
)
TRIAL_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def main(argv=None):
    args = parse_args(argv)
    repo_root = Path(__file__).resolve().parents[1]

    try:
        recipe_path = resolve_recipe_path(repo_root, args.trial, args.recipe)
        recipe = load_simple_yaml(recipe_path)
        trial = normalize_trial(recipe, args.trial, recipe_path)
        run = prepare_run(repo_root, recipe_path, trial, args.runs_dir)
        write_run_files(run, trial, args.detector_params)
        write_summary(run, trial, "prepared", args.no_start)

        if args.no_start:
            print_plan(run, trial)
            return 0

        start_detector(repo_root, run, args)
        write_summary(run, trial, "detector_started", args.no_start)
        print_started(run, trial)
        return 0
    except TrialError as exc:
        print(f"trial_runner: {exc}", file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as exc:
        message = f"detector start failed with exit code {exc.returncode}"
        try:
            write_summary(run, trial, message, args.no_start)
        except Exception:
            pass
        print(f"trial_runner: {message}", file=sys.stderr)
        return exc.returncode


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Run an OpenHRI object-search recipe."
    )
    parser.add_argument("--trial", default="", help="Trial name in recipes/trials")
    parser.add_argument("--recipe", default="", help="Explicit recipe YAML path")
    parser.add_argument("--runs-dir", default="runs", help="Host run output directory")
    parser.add_argument("--container", default="openhri-office")
    parser.add_argument(
        "--image",
        default=os.environ.get("OPENHRI_IMAGE", DEFAULT_IMAGE),
    )
    parser.add_argument(
        "--platform",
        default=os.environ.get("OPENHRI_PLATFORM", "linux/arm64"),
    )
    parser.add_argument("--detector-params", default=DEFAULT_DETECTOR_PARAMS)
    parser.add_argument(
        "--no-start",
        action="store_true",
        help="Prepare run files without starting the detector.",
    )
    return parser.parse_args(argv)


def resolve_recipe_path(repo_root, trial_name, recipe):
    recipe = recipe.strip()
    trial_name = trial_name.strip()
    if recipe:
        path = Path(recipe)
        if not path.is_absolute():
            path = repo_root / path
        if not path.exists():
            raise TrialError(f"recipe not found: {path}")
        return path.resolve()

    if not trial_name:
        raise TrialError("set TRIAL=<name> or RECIPE=<path>")

    path = repo_root / "recipes" / "trials" / f"{trial_name}.yaml"
    if not path.exists():
        raise TrialError(f"trial recipe not found: {path}")
    return path.resolve()


def load_simple_yaml(path):
    root = {}
    stack = [(-1, root)]

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = strip_comment(raw_line).rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent % 2:
            raise TrialError(f"{path}:{line_number}: indentation must use two spaces")

        text = line.strip()
        if text.startswith("- "):
            raise TrialError(f"{path}:{line_number}: lists are not supported")
        key, separator, raw_value = text.partition(":")
        if not separator or not key.strip():
            raise TrialError(f"{path}:{line_number}: expected key: value")

        while stack and indent <= stack[-1][0]:
            stack.pop()
        if not stack:
            raise TrialError(f"{path}:{line_number}: invalid indentation")

        parent = stack[-1][1]
        key = key.strip()
        raw_value = raw_value.strip()
        if not raw_value:
            child = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = parse_scalar(raw_value)

    return root


def strip_comment(line):
    in_single = False
    in_double = False
    escaped = False
    result = []
    for char in line:
        if char == "\\" and in_double and not escaped:
            escaped = True
            result.append(char)
            continue
        if char == "'" and not in_double and not escaped:
            in_single = not in_single
        elif char == '"' and not in_single and not escaped:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            break
        result.append(char)
        escaped = False
    return "".join(result)


def parse_scalar(value):
    value = value.strip()
    lowered = value.lower()
    if lowered in ("true", "false"):
        return lowered == "true"
    if lowered in ("null", "none"):
        return None
    if value.startswith('"') and value.endswith('"'):
        return json.loads(value)
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def normalize_trial(recipe, trial_name, recipe_path):
    trial_id = str(recipe.get("trial_id") or trial_name or recipe_path.stem)
    if not TRIAL_ID_RE.match(trial_id):
        raise TrialError(
            "trial_id may only contain letters, numbers, dash, underscore, and dot"
        )

    robot = recipe.get("robot") or {}
    target = recipe.get("target") or {}
    start_pose = recipe.get("robot_start_pose") or robot.get("start_pose")
    target_pose = recipe.get("target_object_pose") or target.get("pose")
    target_class = recipe.get("target_class") or target.get("class")
    seed = recipe.get("seed", recipe.get("random_seed"))

    missing = []
    if not recipe.get("world"):
        missing.append("world")
    if start_pose is None:
        missing.append("robot.start_pose")
    if not target_class:
        missing.append("target.class")
    if target_pose is None:
        missing.append("target.pose")
    if seed is None:
        missing.append("seed")
    if missing:
        raise TrialError(f"recipe is missing required field(s): {', '.join(missing)}")

    notes = str(recipe.get("notes") or "")
    operator_setup = str(recipe.get("operator_setup") or "")
    if operator_setup:
        setup_note = f"Operator setup: {operator_setup}"
        notes = f"{notes} {setup_note}".strip()

    return {
        "trial_id": trial_id,
        "scenario": str(recipe.get("scenario") or "object_search_approach"),
        "world": str(recipe["world"]),
        "seed": seed,
        "robot_start_pose": pose_to_param(start_pose),
        "target_class": str(target_class),
        "target_object_pose": pose_to_param(target_pose),
        "notes": notes,
        "operator_setup": operator_setup,
    }


def pose_to_param(value):
    if isinstance(value, dict):
        ordered = []
        seen = set()
        for key in ("x", "y", "z", "roll", "pitch", "yaw"):
            if key in value:
                ordered.append(f"{key}={format_scalar(value[key])}")
                seen.add(key)
        for key in sorted(set(value) - seen):
            ordered.append(f"{key}={format_scalar(value[key])}")
        return ",".join(ordered)
    return str(value)


def format_scalar(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    return str(value)


def prepare_run(repo_root, recipe_path, trial, runs_dir):
    runs_root = (repo_root / runs_dir).resolve()
    assert_inside_repo(repo_root, runs_root, "runs-dir")
    run_dir = runs_root / trial["trial_id"]
    run_dir.mkdir(parents=True, exist_ok=True)

    recipe_copy = run_dir / "recipe.yaml"
    if recipe_path.resolve() != recipe_copy.resolve():
        shutil.copyfile(recipe_path, recipe_copy)
    reset_run_artifacts(run_dir)

    rel_run_dir = run_dir.relative_to(repo_root)
    container_run_dir = CONTAINER_REPO_ROOT / rel_run_dir.as_posix()
    return {
        "host_dir": run_dir,
        "recipe_copy": recipe_copy,
        "container_dir": container_run_dir,
        "container_recipe": container_run_dir / "recipe.yaml",
        "container_events": container_run_dir / "events.jsonl",
        "container_manifest": container_run_dir / "manifest.yaml",
        "container_params": container_run_dir / "detector_params.yaml",
        "container_log": container_run_dir / "detector.log",
    }


def reset_run_artifacts(run_dir):
    for name in ("events.jsonl", "manifest.yaml", "detector.log", "evaluation.json"):
        path = run_dir / name
        if path.exists():
            path.unlink()


def assert_inside_repo(repo_root, path, label):
    try:
        path.relative_to(repo_root)
    except ValueError as exc:
        raise TrialError(f"{label} must stay inside the repository: {path}") from exc


def write_run_files(run, trial, detector_params):
    repo_root = Path(__file__).resolve().parents[1]
    params = {
        "object_detection_node": {
            "ros__parameters": {
                "event_log_enabled": True,
                "event_log_run_id": trial["trial_id"],
                "event_log_path": str(run["container_events"]),
                "event_log_scenario": trial["scenario"],
                "run_manifest_enabled": True,
                "run_manifest_path": str(run["container_manifest"]),
                "run_manifest_trial_id": trial["trial_id"],
                "run_manifest_world": trial["world"],
                "run_manifest_robot_start_pose": trial["robot_start_pose"],
                "run_manifest_target_class": trial["target_class"],
                "run_manifest_target_object_pose": trial["target_object_pose"],
                "run_manifest_random_seed": str(trial["seed"]),
                "run_manifest_notes": trial["notes"],
                "run_manifest_recipe_path": str(run["container_recipe"]),
                "run_manifest_run_dir": str(run["container_dir"]),
            }
        }
    }
    (run["host_dir"] / "detector_params.yaml").write_text(
        to_yaml(params), encoding="utf-8"
    )

    detector_param_args = (
        f"--params-file {detector_params} "
        f"--params-file {run['container_params']}"
    )
    (run["host_dir"] / "detector_param_args.txt").write_text(
        detector_param_args + "\n", encoding="utf-8"
    )
    (run["host_dir"] / "command.txt").write_text(
        f"make trial RECIPE=\"{run['host_dir'].relative_to(repo_root) / 'recipe.yaml'}\"\n",
        encoding="utf-8",
    )
    write_reproduce_sh(run)


def write_reproduce_sh(run):
    repo_root = Path(__file__).resolve().parents[1]
    rel_repo = os.path.relpath(repo_root, run["host_dir"])
    script = f"""#!/usr/bin/env bash
set -euo pipefail

RUN_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
REPO_ROOT="$(cd "${{RUN_DIR}}/{rel_repo}" && pwd)"

cd "${{REPO_ROOT}}"
make trial RECIPE="${{RUN_DIR}}/recipe.yaml"
"""
    path = run["host_dir"] / "reproduce.sh"
    path.write_text(script, encoding="utf-8")
    path.chmod(0o755)


def write_summary(run, trial, status, no_start):
    lines = [
        f"trial_id: {trial['trial_id']}",
        f"status: {status}",
        f"updated_at_utc: {utc_now()}",
        f"mode: {'plan_only' if no_start else 'detector_background'}",
        "",
        "artifacts:",
        "  recipe: recipe.yaml",
        "  detector_params: detector_params.yaml",
        "  event_log: events.jsonl",
        "  manifest: manifest.yaml",
        "  detector_log: detector.log",
        "  reproduce_command: ./reproduce.sh",
        "",
        "declared_trial:",
        f"  scenario: {trial['scenario']}",
        f"  world: {trial['world']}",
        f"  seed: {trial['seed']}",
        f"  robot_start_pose: {trial['robot_start_pose']}",
        f"  target_class: {trial['target_class']}",
        f"  target_object_pose: {trial['target_object_pose']}",
    ]
    if trial["operator_setup"]:
        lines.extend(["", "operator_setup:", f"  {trial['operator_setup']}"])
    if trial["notes"]:
        lines.extend(["", "notes:", f"  {trial['notes']}"])
    (run["host_dir"] / "summary.txt").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def start_detector(repo_root, run, args):
    detector_param_args = (
        f"--params-file {args.detector_params} "
        f"--params-file {run['container_params']}"
    )
    command = [
        "make",
        "detector-bg",
        f"CONTAINER={args.container}",
        f"IMAGE={args.image}",
        f"OPENHRI_PLATFORM={args.platform}",
        f"DETECTOR_PARAMS={args.detector_params}",
        f"DETECTOR_PARAM_ARGS={detector_param_args}",
        f"DETECTOR_LOG={run['container_log']}",
        "DETECTOR_ROS_ARGS=",
    ]
    subprocess.run(command, cwd=repo_root, check=True)


def print_plan(run, trial):
    print(f"Prepared trial: {trial['trial_id']}")
    print(f"Run directory: {run['host_dir']}")
    print("Detector was not started because --no-start was used.")
    print(f"Reproduce: {run['host_dir'] / 'reproduce.sh'}")


def print_started(run, trial):
    print(f"Started trial: {trial['trial_id']}")
    print(f"Run directory: {run['host_dir']}")
    print(f"Event log: {run['host_dir'] / 'events.jsonl'}")
    print(f"Manifest: {run['host_dir'] / 'manifest.yaml'}")
    print(f"Detector log: {run['host_dir'] / 'detector.log'}")


def to_yaml(value):
    return "\n".join(yaml_lines(value, 0)) + "\n"


def yaml_lines(value, indent):
    prefix = " " * indent
    if isinstance(value, dict):
        lines = []
        for key, item in value.items():
            if isinstance(item, dict):
                lines.append(f"{prefix}{key}:")
                lines.extend(yaml_lines(item, indent + 2))
            else:
                lines.append(f"{prefix}{key}: {yaml_scalar(item)}")
        return lines
    raise TypeError(f"cannot write YAML value: {type(value).__name__}")


def yaml_scalar(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value))


def utc_now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class TrialError(Exception):
    pass


if __name__ == "__main__":
    raise SystemExit(main())
