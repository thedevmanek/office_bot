# Researcher Guide

This guide is for researchers evaluating or modifying OpenHRI Office. The
recommended workflow is container-first and recipe-first: run the published
runtime image, change trial recipes and detector parameters, then edit ROS code
only when the study needs new behavior.

## First Validation

From a clean checkout:

```bash
make doctor
make start
```

Open the desktop:

```text
http://localhost:6080/vnc.html?autoconnect=1&resize=remote
```

Launch the simulation in one terminal:

```bash
make sim
```

Run the baseline object-search trial in another terminal:

```bash
make trial TRIAL=bottle-demo
```

Open the object search console:

```text
http://localhost:8080/
```

Package the run for sharing:

```bash
make trial-pack TRIAL=bottle-demo
```

The package is written to:

```text
runs/openhri-bottle-demo-repro.zip
```

For a less black-box run, use the tmux session instead of separate terminals:

```bash
make researcher-session
```

The session opens one tmux `run` window split into a 2x2 grid:

- top-left: simulation launch logs
- bottom-left: recipe-backed detector startup and detector log stream
- top-right: container supervisor logs
- bottom-right: live `runs/<trial_id>/` artifacts, including event and manifest previews

It also opens a `shell` window for an interactive ROS-ready shell and a `help`
window with controls.

`make researcher-session` replaces any existing `openhri` tmux session, so stale
split-pane layouts are not reused. Use `make researcher-attach` only when you
want to return to the existing session without recreating it.

Mouse scrolling is enabled. Click a window in the bottom bar or use `Ctrl-b`
followed by the window number. Stop everything from inside tmux with `Ctrl-b`
then `X`, or press `F12`.

If a pane command exits or fails, the pane stays open at a shell prompt. Type
`rerun` in that pane to execute the same command again, or press Up then Enter
to edit and rerun the last command.

Use these commands from a normal terminal:

```bash
make researcher-attach
make researcher-stop
```

## Researcher Loop

Use this loop for most study-design changes:

1. Copy an existing recipe in `experiments/trials/`.
2. Change the trial ID, target class, object pose, robot start pose, seed, or notes.
3. Validate the recipe without starting the detector:

```bash
make trial-plan TRIAL=<trial-id>
```

4. Run the transparent tmux session:

```bash
make researcher-session TRIAL=<trial-id>
```

Or run the pieces manually:

```bash
make sim
make trial TRIAL=<trial-id>
```

5. Inspect the object UI, Gazebo, RViz, `runs/<trial-id>/events.jsonl`, and
   `runs/<trial-id>/manifest.yaml`.
6. Package the run:

```bash
make trial-pack TRIAL=<trial-id>
```

## Trial Recipes

Checked-in recipes live under:

```text
experiments/trials/
```

Minimal recipe:

```yaml
trial_id: bottle-demo
scenario: object_search_approach
world: office_world
seed: 42

robot:
  start_pose:
    x: 0.0
    y: 0.0
    yaw: 0.0

target:
  class: bottle
  pose:
    x: 2.4
    y: -0.8
    yaw: 0.0

notes: Baseline bottle search trial for reproducibility checks.
```

Required fields:

- `trial_id`
- `world`
- `seed`
- `robot.start_pose`
- `target.class`
- `target.pose`

Keep trial IDs filesystem-safe. Letters, numbers, dash, underscore, and dot are
supported.

## Tinker Points

Start with configuration before changing source code.

Trial design:

- `experiments/trials/*.yaml`: target object, pose, robot start pose, seed, and notes.
- `docs/study-ideas/`: example HRI study directions using the same task.

Detector and localization behavior:

- `dev_ws/src/object_detector/config/object_detector.yaml`
- `confidence_threshold`: object detector confidence cutoff.
- `min_confirmations`: repeated observations required before a track is confirmed.
- `cluster_radius_m`: grouping radius for raw object observations.
- `confirmed_association_radius_m`: matching radius for confirmed tracks.
- `track_timeout_s`: time before unconfirmed tracks expire.

Navigation and approach behavior:

- `approach_offset_m`: preferred stand-off distance from an object.
- `min_approach_offset_m`: minimum acceptable stand-off distance.
- `close_stop_distance_m`: close stopping threshold.
- `dynamic_replanning_enabled`: whether navigation updates as object confidence changes.
- `goal_candidate_angle_step_deg`: angular spacing for candidate approach poses.

UI and operator-facing behavior:

- `dev_ws/src/object_detector/web/index.html`
- `dev_ws/src/object_detector/object_detector/web.py`

Core implementation:

- `dev_ws/src/object_detector/object_detector/localization.py`
- `dev_ws/src/object_detector/object_detector/tracking.py`
- `dev_ws/src/object_detector/object_detector/navigation.py`
- `dev_ws/src/object_detector/object_detector/object_detect.py`

## Run Artifacts

Recipe-backed runs write one folder:

```text
runs/<trial_id>/
  recipe.yaml
  detector_params.yaml
  detector_param_args.txt
  command.txt
  summary.txt
  reproduce.sh
  detector.log
  events.jsonl
  manifest.yaml
```

Use these files as follows:

- `recipe.yaml`: copied recipe used for the run.
- `detector_params.yaml`: generated ROS parameter overrides for the run.
- `events.jsonl`: one JSON event per line for analysis.
- `manifest.yaml`: run metadata, code context, runtime context, recipe path, and detector parameters.
- `summary.txt`: quick human-readable run summary.
- `reproduce.sh`: reruns the copied recipe from that run folder.
- `detector.log`: detector process logs.

## Rebuild Rules

No rebuild is needed after editing:

- `experiments/trials/*.yaml`
- files under `runs/`
- most documentation

Run `make bootstrap` after editing:

- `dev_ws/**`
- package metadata such as `package.xml`, `setup.py`, `CMakeLists.txt`
- launch files, ROS configs, models, detector code, or web UI

Run `make start-local` or `make restart-local` after editing runtime image inputs:

- `Containerfile`
- `container/*.sh`
- desktop launcher files

Run `make restart` after editing `compose.yaml`.

## Validation Before Sharing

Before sending a modified study or branch to another researcher, with the
preview container running:

```bash
make trial-plan TRIAL=<trial-id>
make test
make trial-pack TRIAL=<trial-id>
```

For a full runtime smoke test:

```bash
make doctor
make start
make sim
make trial TRIAL=<trial-id>
```

Check that:

- Gazebo loads the office world.
- RViz shows the robot, map, lidar, and object markers.
- The object UI connects on `http://localhost:8080/`.
- A confirmed object card appears for the target class.
- `runs/<trial-id>/events.jsonl` contains `trial_start`.
- `runs/<trial-id>/manifest.yaml` exists and points back to the recipe.

## Current Limits

- The recommended handoff path is simulation-only.
- The runtime uses CPU object detection by default, so detector frame rate varies by host.
- The published image is the runtime base; the repository checkout supplies the ROS workspace and study files at container start.
- Source changes under `dev_ws/` require `make bootstrap` before relaunching.
- Recipe-backed trials capture detector and manifest artifacts, but final participant-study outcome labels still need study-specific annotation.
