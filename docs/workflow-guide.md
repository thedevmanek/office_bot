# Workflow Guide

This guide is for operators, maintainers, reviewers, and project teams using `office_bot` as the inspectable OpenHRI ROS 2 reference robot stack.

## Recommended Start

From a clean checkout:

```bash
make doctor
make repo-check
make start
make sim
```

Open the desktop:

```text
http://localhost:6080/vnc.html?autoconnect=1&resize=remote
```

Open the object console after starting the detector:

```text
http://localhost:8080/
```

## One-Screen Workflow Session

For a supervised run, use:

```bash
make workflow-session
```

It creates one tmux `run` window with:

- top-left: simulation launch logs
- bottom-left: recipe-backed detector logs
- top-right: container logs
- bottom-right: live run outputs

Mouse scrolling is enabled. A separate `shell` window gives an interactive ROS-ready shell, and a `help` window repeats the controls.

If a pane command exits or fails, the pane stays open at a shell prompt. Type `rerun` in the pane to execute the same command again.

Stop everything from inside tmux with `Ctrl-b` then `X`, or press `F12`. From a normal terminal, use:

```bash
make workflow-stop
```

Attach to an existing session:

```bash
make workflow-attach
```

## Run Loop

The default project loop is:

1. Pick or copy a recipe under `recipes/trials/`.
2. Validate the recipe:

```bash
make trial-plan TRIAL=<trial-id>
```

3. Start the simulator:

```bash
make sim
```

4. Run the recipe:

```bash
make trial TRIAL=<trial-id>
```

5. Evaluate the run:

```bash
make trial-evaluate TRIAL=<trial-id>
```

6. Package the run:

```bash
make trial-pack TRIAL=<trial-id>
```

7. Capture the changed files, `runs/<trial-id>/summary.txt`, `evaluation.json`, and notes on failures or interventions.

## Common Modification Tasks

- Change target object class in a recipe.
- Adjust object placement notes and start pose.
- Tune detector confidence and track confirmation thresholds.
- Modify localization or tracking behavior.
- Change approach offset and stop distance.
- Improve object-console wording or status display.
- Add a new evaluator warning.
- Document a hardware swap or calibration step.

## Useful Files

```text
recipes/trials/
dev_ws/src/object_detector/config/object_detector.yaml
dev_ws/src/object_detector/object_detector/localization.py
dev_ws/src/object_detector/object_detector/tracking.py
dev_ws/src/object_detector/object_detector/navigation.py
dev_ws/src/object_detector/web/index.html
docs/component-swap-guide.md
docs/hardware-bom.md
```

## What To Capture

For a normal run:

- Changed files or patch.
- Commands run.
- `runs/<trial-id>/summary.txt`.
- `runs/<trial-id>/evaluation.json` when available.
- Short explanation of observed behavior.
- Failure notes, including setup issues and manual interventions.

For a hardware-facing run:

- Updated BOM or swap notes.
- Photos or measurements when appropriate.
- Safety or stop-behavior notes.
- Any launch logs or device checks needed to repeat the result.

## Maintainer Notes

- Prefer simulation-only runs until the hardware checklist is filled.
- Keep the baseline `bottle-demo` recipe unchanged for comparison.
- Require packaged run outputs instead of screenshots alone.
- Treat failed runs as useful if the logs explain what happened.
- Keep hardware motion slow and supervised until stop behavior is tested.
- Keep reusable workflow instructions in this guide or in a checked-in recipe.
