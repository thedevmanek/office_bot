#!/usr/bin/env python3
"""Evaluate an OpenHRI object-search trial event log."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from trial_packager import resolve_trial_id  # noqa: E402
from trial_runner import TrialError, assert_inside_repo  # noqa: E402


SUCCESS_STATUSES = {"succeeded", "success", "completed"}


def main(argv=None):
    args = parse_args(argv)
    repo_root = Path(__file__).resolve().parents[1]

    try:
        run_dir = resolve_run_dir(repo_root, args)
        events_path = resolve_events_path(run_dir, args.events)
        events = load_events(events_path)
        segments = split_segments(events)
        if not segments:
            raise TrialError(f"event log has no events: {events_path}")

        segment = segments[-1]
        evaluation = evaluate_segment(
            segment,
            segment_index=len(segments),
            segment_count=len(segments),
            target_class_override=args.target_class.strip(),
        )
        output = resolve_output(run_dir, args.output)
        if output is not None:
            output.write_text(
                json.dumps(evaluation, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

        print_summary(run_dir, output, evaluation)
        return 0
    except TrialError as exc:
        print(f"trial_evaluator: {exc}", file=sys.stderr)
        return 2


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Summarize events.jsonl into object-search trial metrics."
    )
    parser.add_argument("--trial", default="", help="Trial ID under runs/")
    parser.add_argument("--recipe", default="", help="Recipe path to infer trial ID")
    parser.add_argument("--runs-dir", default="runs")
    parser.add_argument("--events", default="", help="Explicit events.jsonl path")
    parser.add_argument(
        "--output",
        default="",
        help=(
            "JSON output path. Default: runs/<trial>/evaluation.json. "
            "Use '-' to skip writing."
        ),
    )
    parser.add_argument(
        "--target-class",
        default="",
        help="Override target class when the event log has no trial_start target.",
    )
    return parser.parse_args(argv)


def resolve_run_dir(repo_root, args):
    if args.events.strip():
        return resolve_path(repo_root, args.events).parent

    trial_id = resolve_trial_id(repo_root, args.trial, args.recipe)
    run_dir = (repo_root / args.runs_dir / trial_id).resolve()
    assert_inside_repo(repo_root, run_dir, "run directory")
    if not run_dir.exists():
        raise TrialError(f"run directory not found: {run_dir}")
    return run_dir


def resolve_events_path(run_dir, events):
    if events.strip():
        path = resolve_path(Path.cwd(), events)
    else:
        path = run_dir / "events.jsonl"
    if not path.exists():
        raise TrialError(f"event log not found: {path}")
    return path


def resolve_path(base, value):
    path = Path(value)
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def resolve_output(run_dir, output):
    output = output.strip()
    if output == "-":
        return None
    if output:
        path = Path(output)
        if not path.is_absolute():
            path = Path.cwd() / path
        return path.resolve()
    return run_dir / "evaluation.json"


def load_events(path):
    events = []
    for line_no, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise TrialError(f"{path}:{line_no}: invalid JSON: {exc.msg}") from exc
        if not isinstance(event, dict):
            raise TrialError(f"{path}:{line_no}: JSONL event must be an object")
        if not event.get("event"):
            raise TrialError(f"{path}:{line_no}: JSONL event is missing event")
        events.append(event)
    return events


def split_segments(events):
    segments = []
    current = []
    for event in events:
        if event.get("event") == "trial_start" and current:
            segments.append(current)
            current = []
        current.append(event)
    if current:
        segments.append(current)
    return segments


def evaluate_segment(segment, segment_index, segment_count, target_class_override=""):
    start_event = first_event(segment, "trial_start")
    target_class = target_class_override or str(
        (start_event or {}).get("target_class") or ""
    )
    localized = events_named(segment, "object_localized")
    confirmed = events_named(segment, "track_confirmed")
    nav_requested = events_named(segment, "navigation_requested")
    nav_results = events_named(segment, "navigation_result")
    class_by_track_id = track_class_index(
        localized + confirmed + nav_requested + nav_results
    )

    target_localized = events_for_class(localized, target_class, class_by_track_id)
    target_confirmed = events_for_class(confirmed, target_class, class_by_track_id)
    target_nav_requested = events_for_class(
        nav_requested, target_class, class_by_track_id
    )
    target_nav_results = events_for_class(nav_results, target_class, class_by_track_id)

    min_t, max_t = time_bounds(segment)
    terminal_status = infer_terminal_status(
        target_class,
        localized,
        confirmed,
        nav_requested,
        nav_results,
        target_localized,
        target_confirmed,
        target_nav_requested,
        target_nav_results,
    )
    warnings = build_warnings(
        segment,
        segment_count,
        target_class,
        target_localized,
        target_confirmed,
        target_nav_requested,
        target_nav_results,
        nav_requested,
        nav_results,
        class_by_track_id,
    )

    return {
        "schema": "openhri.trial_evaluation.v1",
        "run": {
            "run_id": value_from(segment, "run_id"),
            "trial_id": (start_event or {}).get("trial_id"),
            "scenario": value_from(segment, "scenario"),
            "world": (start_event or {}).get("world"),
            "target_class": target_class or None,
        },
        "source": {
            "events": "events.jsonl",
            "segment_policy": "latest",
            "segment_index": segment_index,
            "segment_count": segment_count,
            "event_count": len(segment),
        },
        "metrics": {
            "duration_s": round_number(max_t - min_t) if max_t is not None else None,
            "first_object_localized_s": event_time(first(localized)),
            "first_target_localized_s": event_time(first(target_localized)),
            "first_track_confirmed_s": event_time(first(confirmed)),
            "first_target_confirmed_s": event_time(first(target_confirmed)),
            "first_navigation_requested_s": event_time(first(nav_requested)),
            "first_target_navigation_requested_s": event_time(
                first(target_nav_requested)
            ),
            "first_navigation_result_s": event_time(first(nav_results)),
            "object_localized_count": len(localized),
            "target_localized_count": len(target_localized),
            "track_confirmed_count": len(confirmed),
            "target_confirmed_count": len(target_confirmed),
            "navigation_requested_count": len(nav_requested),
            "target_navigation_requested_count": len(target_nav_requested),
            "navigation_result_count": len(nav_results),
            "target_navigation_result_count": len(target_nav_results),
            "localized_classes": dict(
                Counter(class_label(event) for event in localized)
            ),
            "confirmed_classes": dict(
                Counter(class_label(event) for event in confirmed)
            ),
            "terminal_status": terminal_status,
            "success": terminal_status in {
                "navigation_succeeded",
                "target_navigation_succeeded",
            },
        },
        "navigation": navigation_summary(nav_requested, nav_results, class_by_track_id),
        "warnings": warnings,
    }


def infer_terminal_status(
    target_class,
    localized,
    confirmed,
    nav_requested,
    nav_results,
    target_localized,
    target_confirmed,
    target_nav_requested,
    target_nav_results,
):
    if target_class:
        if target_nav_results:
            return "target_navigation_" + normalize_status(target_nav_results[-1])
        if target_nav_requested:
            return "target_navigation_requested_no_result"
        if target_confirmed:
            return "target_confirmed_no_navigation"
        if target_localized:
            return "target_localized_no_confirmation"
        return "no_target_localized"

    if nav_results:
        return "navigation_" + normalize_status(nav_results[-1])
    if nav_requested:
        return "navigation_requested_no_result"
    if confirmed:
        return "track_confirmed_no_navigation"
    if localized:
        return "object_localized_no_confirmation"
    return "no_object_localized"


def normalize_status(event):
    status = str(event.get("status") or "unknown").strip().lower()
    if status in SUCCESS_STATUSES:
        return "succeeded"
    return status or "unknown"


def build_warnings(
    segment,
    segment_count,
    target_class,
    target_localized,
    target_confirmed,
    target_nav_requested,
    target_nav_results,
    nav_requested,
    nav_results,
    class_by_track_id,
):
    warnings = []
    if segment_count > 1:
        warnings.append(
            f"Event log contains {segment_count} segments; evaluated the latest segment."
        )
    if not first_event(segment, "trial_start"):
        warnings.append("Segment has no trial_start event.")
    if not target_class:
        warnings.append("No target_class found; target-specific metrics are disabled.")
    elif not target_localized:
        warnings.append(f"No localized event matched target_class={target_class}.")
    elif not target_confirmed:
        warnings.append(f"Target class {target_class} was localized but not confirmed.")
    elif not target_nav_requested:
        warnings.append(
            f"Target class {target_class} was confirmed but no target navigation "
            "was requested."
        )
    elif not target_nav_results:
        warnings.append(
            f"Target class {target_class} had a navigation request but no result event."
        )

    non_target_nav = [
        event_class_name(event, class_by_track_id)
        for event in nav_requested
        if target_class and event_class_name(event, class_by_track_id) != target_class
    ]
    if non_target_nav:
        warnings.append(
            "Navigation was requested for non-target class(es): "
            + ", ".join(sorted(set(non_target_nav)))
        )
    if nav_requested and not nav_results:
        warnings.append("Navigation was requested but no navigation_result was recorded.")
    return warnings


def navigation_summary(nav_requested, nav_results, class_by_track_id):
    last_request = nav_requested[-1] if nav_requested else None
    last_result = nav_results[-1] if nav_results else None
    return {
        "last_requested_track_id": (last_request or {}).get("track_id"),
        "last_requested_class": (
            event_class_name(last_request, class_by_track_id)
            if last_request
            else None
        ),
        "last_result_class": (
            event_class_name(last_result, class_by_track_id)
            if last_result
            else None
        ),
        "last_result_status": (last_result or {}).get("status"),
        "last_result_message": (last_result or {}).get("message"),
    }


def print_summary(run_dir, output, evaluation):
    metrics = evaluation["metrics"]
    run = evaluation["run"]
    source = evaluation["source"]
    print(f"Evaluated trial: {run.get('trial_id') or run.get('run_id') or 'unknown'}")
    print(f"Run directory: {run_dir}")
    print(
        "Segment: "
        f"{source['segment_index']}/{source['segment_count']} "
        f"({source['event_count']} events)"
    )
    print(f"Target class: {run.get('target_class') or 'unknown'}")
    print(f"Terminal status: {metrics['terminal_status']}")
    print(f"Success: {str(metrics['success']).lower()}")
    print(
        "First object localized: "
        f"{display_seconds(metrics['first_object_localized_s'])}"
    )
    print(
        "First target localized: "
        f"{display_seconds(metrics['first_target_localized_s'])}"
    )
    print(
        "First target confirmed: "
        f"{display_seconds(metrics['first_target_confirmed_s'])}"
    )
    print(
        "First target navigation requested: "
        f"{display_seconds(metrics['first_target_navigation_requested_s'])}"
    )
    print(
        "Navigation result: "
        f"{evaluation['navigation']['last_result_status'] or 'none'}"
    )
    if output is not None:
        print(f"Wrote: {output}")
    if evaluation["warnings"]:
        print("Warnings:")
        for warning in evaluation["warnings"]:
            print(f"- {warning}")


def display_seconds(value):
    if value is None:
        return "n/a"
    return f"{value:.3f}s"


def events_named(events, name):
    return [event for event in events if event.get("event") == name]


def first_event(events, name):
    return first(events_named(events, name))


def events_for_class(events, wanted_class, class_by_track_id=None):
    if not wanted_class:
        return []
    return [
        event
        for event in events
        if event_class_name(event, class_by_track_id or {}) == wanted_class
    ]


def first(values):
    return values[0] if values else None


def class_name(event):
    if not event:
        return None
    value = event.get("class") or event.get("class_name")
    return str(value) if value is not None else None


def event_class_name(event, class_by_track_id):
    explicit = class_name(event)
    if explicit:
        return explicit
    track_id = event.get("track_id") if event else None
    if track_id is None:
        return None
    return class_by_track_id.get(str(track_id))


def track_class_index(events):
    index = {}
    for event in events:
        track_id = event.get("track_id")
        name = class_name(event)
        if track_id is not None and name:
            index[str(track_id)] = name
    return index


def class_label(event):
    return class_name(event) or "unknown"


def event_time(event):
    if not event:
        return None
    try:
        return round_number(float(event.get("t")))
    except (TypeError, ValueError):
        return None


def time_bounds(events):
    times = [event_time(event) for event in events]
    times = [time for time in times if time is not None]
    if not times:
        return None, None
    return min(times), max(times)


def value_from(events, key):
    for event in events:
        if key in event:
            return event[key]
    return None


def round_number(value):
    return round(float(value), 6)


if __name__ == "__main__":
    raise SystemExit(main())
