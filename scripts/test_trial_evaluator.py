#!/usr/bin/env python3
"""Unit tests for no-Podman workflow helper scripts."""

import json
import tempfile
import unittest
from pathlib import Path

from trial_evaluator import evaluate_segment, load_events, split_segments
from trial_packager import resolve_trial_id
from trial_runner import TrialError, reset_run_artifacts


class TrialEvaluatorTests(unittest.TestCase):
    def test_evaluator_uses_latest_segment_and_target_success(self):
        events = [
            {
                "event": "trial_start",
                "run_id": "old",
                "trial_id": "old",
                "scenario": "object_search_approach",
                "target_class": "bottle",
                "t": 0.0,
            },
            {"event": "object_localized", "class": "chair", "t": 0.4},
            {
                "event": "trial_start",
                "run_id": "new",
                "trial_id": "new",
                "scenario": "object_search_approach",
                "world": "office_world",
                "target_class": "bottle",
                "t": 0.0,
            },
            {"event": "object_localized", "class": "bottle", "track_id": 2, "t": 0.5},
            {"event": "track_confirmed", "class": "bottle", "track_id": 2, "t": 1.0},
            {
                "event": "navigation_requested",
                "class": "bottle",
                "track_id": 2,
                "t": 1.2,
            },
            {
                "event": "navigation_result",
                "track_id": 2,
                "status": "succeeded",
                "t": 2.0,
            },
        ]

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.write_text(
                "\n".join(json.dumps(event) for event in events) + "\n",
                encoding="utf-8",
            )

            segments = split_segments(load_events(path))
            evaluation = evaluate_segment(
                segments[-1],
                segment_index=len(segments),
                segment_count=len(segments),
            )
            self.assertNotIn(tmp, json.dumps(evaluation))

        self.assertEqual(evaluation["source"]["segment_count"], 2)
        self.assertEqual(evaluation["run"]["trial_id"], "new")
        self.assertEqual(evaluation["metrics"]["first_target_localized_s"], 0.5)
        self.assertEqual(
            evaluation["metrics"]["terminal_status"],
            "target_navigation_succeeded",
        )
        self.assertEqual(evaluation["navigation"]["last_result_class"], "bottle")
        self.assertTrue(evaluation["metrics"]["success"])
        self.assertTrue(
            any("latest segment" in warning for warning in evaluation["warnings"])
        )

    def test_evaluator_flags_non_target_navigation(self):
        segment = [
            {
                "event": "trial_start",
                "run_id": "run",
                "trial_id": "run",
                "scenario": "object_search_approach",
                "target_class": "bottle",
                "t": 0.0,
            },
            {"event": "object_localized", "class": "chair", "track_id": 1, "t": 0.5},
            {"event": "track_confirmed", "class": "chair", "track_id": 1, "t": 1.0},
            {
                "event": "navigation_requested",
                "class": "chair",
                "track_id": 1,
                "t": 1.5,
            },
            {
                "event": "navigation_result",
                "class": "chair",
                "track_id": 1,
                "status": "error",
                "message": "Navigation finished with status 6.",
                "t": 2.0,
            },
        ]

        evaluation = evaluate_segment(segment, segment_index=1, segment_count=1)

        self.assertEqual(
            evaluation["metrics"]["terminal_status"],
            "no_target_localized",
        )
        self.assertFalse(evaluation["metrics"]["success"])
        self.assertEqual(evaluation["navigation"]["last_requested_class"], "chair")
        self.assertEqual(evaluation["navigation"]["last_result_class"], "chair")
        self.assertTrue(
            any(
                "No localized event matched target_class=bottle" in warning
                for warning in evaluation["warnings"]
            )
        )
        self.assertTrue(
            any("non-target class" in warning for warning in evaluation["warnings"])
        )

    def test_evaluator_serializes_events_with_missing_class(self):
        segment = [
            {
                "event": "trial_start",
                "run_id": "run",
                "trial_id": "run",
                "scenario": "object_search_approach",
                "target_class": "bottle",
                "t": 0.0,
            },
            {"event": "object_localized", "track_id": 1, "t": 0.5},
            {"event": "track_confirmed", "track_id": 1, "t": 1.0},
        ]

        evaluation = evaluate_segment(segment, segment_index=1, segment_count=1)
        encoded = json.dumps(evaluation, sort_keys=True)

        self.assertIn('"unknown": 1', encoded)
        self.assertEqual(evaluation["metrics"]["localized_classes"]["unknown"], 1)
        self.assertEqual(evaluation["metrics"]["confirmed_classes"]["unknown"], 1)

    def test_reset_run_artifacts_keeps_recipe_and_removes_stale_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            keep = run_dir / "recipe.yaml"
            keep.write_text("trial_id: demo\n", encoding="utf-8")
            for name in (
                "events.jsonl",
                "manifest.yaml",
                "detector.log",
                "evaluation.json",
            ):
                (run_dir / name).write_text("stale\n", encoding="utf-8")

            reset_run_artifacts(run_dir)

            self.assertTrue(keep.exists())
            for name in (
                "events.jsonl",
                "manifest.yaml",
                "detector.log",
                "evaluation.json",
            ):
                self.assertFalse((run_dir / name).exists())

    def test_trial_id_rejects_path_traversal(self):
        with self.assertRaises(TrialError):
            resolve_trial_id(Path.cwd(), "../outside", "")

        with tempfile.TemporaryDirectory() as tmp:
            recipe = Path(tmp) / "bad.yaml"
            recipe.write_text("trial_id: ../outside\n", encoding="utf-8")
            with self.assertRaises(TrialError):
                resolve_trial_id(Path.cwd(), "", str(recipe))


if __name__ == "__main__":
    unittest.main()
