#!/usr/bin/env python3
"""Package an OpenHRI run directory for sharing."""

import argparse
import sys
import zipfile
from pathlib import Path

from trial_runner import TrialError, load_simple_yaml, resolve_recipe_path


def main(argv=None):
    args = parse_args(argv)
    repo_root = Path(__file__).resolve().parents[1]

    try:
        trial_id = resolve_trial_id(repo_root, args.trial, args.recipe)
        run_dir = (repo_root / args.runs_dir / trial_id).resolve()
        if not run_dir.exists():
            raise TrialError(f"run directory not found: {run_dir}")

        output = resolve_output(repo_root, args.output, args.runs_dir, trial_id)
        output.parent.mkdir(parents=True, exist_ok=True)
        package_run(run_dir, output)
        print(f"Packaged trial: {trial_id}")
        print(f"Package: {output}")
        return 0
    except TrialError as exc:
        print(f"trial_packager: {exc}", file=sys.stderr)
        return 2


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Create a reproducibility zip from runs/<trial_id>/."
    )
    parser.add_argument("--trial", default="", help="Trial ID to package")
    parser.add_argument("--recipe", default="", help="Recipe path to infer trial ID")
    parser.add_argument("--runs-dir", default="runs")
    parser.add_argument("--output", default="", help="Optional output zip path")
    return parser.parse_args(argv)


def resolve_trial_id(repo_root, trial, recipe):
    trial = trial.strip()
    if trial:
        return trial
    recipe = recipe.strip()
    if not recipe:
        raise TrialError("set TRIAL=<name> or RECIPE=<path>")
    recipe_path = resolve_recipe_path(repo_root, "", recipe)
    data = load_simple_yaml(recipe_path)
    return str(data.get("trial_id") or recipe_path.stem)


def resolve_output(repo_root, output, runs_dir, trial_id):
    if output.strip():
        path = Path(output)
        if not path.is_absolute():
            path = repo_root / path
        return path.resolve()
    return (repo_root / runs_dir / f"openhri-{trial_id}-repro.zip").resolve()


def package_run(run_dir, output):
    required = ["recipe.yaml", "reproduce.sh", "summary.txt"]
    missing_required = [name for name in required if not (run_dir / name).exists()]
    if missing_required:
        raise TrialError(
            "run directory is missing required file(s): "
            + ", ".join(missing_required)
        )

    useful = ["manifest.yaml", "events.jsonl"]
    missing_useful = [name for name in useful if not (run_dir / name).exists()]
    if missing_useful:
        print(
            "trial_packager: warning: packaging before detector artifacts exist: "
            + ", ".join(missing_useful),
            file=sys.stderr,
        )

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(run_dir.rglob("*")):
            if path == output or path.suffix == ".zip" or path.is_dir():
                continue
            archive.write(path, arcname=Path(run_dir.name) / path.relative_to(run_dir))


if __name__ == "__main__":
    raise SystemExit(main())
