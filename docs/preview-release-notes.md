# OpenHRI office_bot 0.1.0 Preview Release Notes

Release date: 2026-06-21

This preview is a source-ready public release for `office_bot`, the reference
office-robot project inside OpenHRI. It covers the simulation and repeatable
object-search workflow and is intended for review, reproduction, extension, and
issue-driven collaboration.

## Scope

- ROS 2 Humble simulation workspace under `dev_ws/`.
- Container-first workflow with noVNC, Gazebo/Ignition, RViz, Nav2, SLAM
  Toolbox, and YOLOX object detection.
- Recipe-backed object-search runs under `recipes/trials/`.
- Run artifacts under `runs/<trial_id>/` when live runtime trials are completed.
- Public docs for setup, workflow, logging, reproducibility, hardware status,
  component swaps, troubleshooting, security, notices, and asset attribution.

## Source Validation Completed

The source gate passed with Podman excluded:

- `make repo-check`
- helper tests: 5 tests
- Python syntax check: 30 files
- YAML/CFF parse: 20 files
- XML/SDF/Xacro parse: 83 files
- shell syntax check
- `git diff --check`
- stale release-term scan
- generated-artifact scan
- Git attribute audit: 423 releasable files, 0 unresolved text/binary attrs
- merge-conflict marker scan

## Scope Limits

- Live runtime behavior depends on the host platform and container runtime.
- Hardware deployment readiness depends on the dated subsystem evidence tracked
  in [hardware-readiness-checklist.md](hardware-readiness-checklist.md).
- Commercial redistribution of bundled simulation world assets depends on
  upstream license evidence recorded in
  [asset-attribution.md](asset-attribution.md).
- `bottle-demo` does not spawn a target automatically. Confirm the manual target
  setup in `recipes/trials/bottle-demo.yaml` before treating a live run as
  complete.

## Current Limits

- The published runtime image tag is expected to remain
  `ghcr.io/thedevmanek/openhri-office:latest-preview`; image publishing happens
  from `main` when runtime-image inputs change.
- Template recipes validate structure; scenarios without completed run outputs
  should be treated as examples.
- The hardware BOM records current known components and readiness gaps; it is
  not a deployment-ready build sheet.
- Third-party model, mesh, texture, animation, and shared world-media assets are
  attribution-recorded but license-review-required.
