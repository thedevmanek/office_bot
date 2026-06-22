# Recipe-Backed Runs

The current workflow is recipe-first. A user should not need to hand-write ROS
parameter overrides for a normal trial. Template recipes are examples until
object spawning/reset support and completed run outputs exist for those
scenarios.

## One Command

Start the container and simulation as usual:

```bash
make start
make sim
```

Then run a named recipe from another terminal:

```bash
make trial TRIAL=bottle-demo
```

The checked-in recipe lives at:

```text
recipes/trials/bottle-demo.yaml
```

## Recipe Format

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

operator_setup: Place a COCO-recognizable bottle in the robot camera view or at the declared target pose; this recipe does not spawn objects automatically yet.
notes: Baseline bottle search trial for reproducibility checks with manual target setup.
```

Required fields:

- `trial_id`
- `world`
- `seed`
- `robot.start_pose`
- `target.class`
- `target.pose`

For non-template recipes, include `operator_setup` so reviewers know what must
be placed, moved, or confirmed manually. The current recipe runner records
declared setup and target poses; it does not spawn or reset objects in Gazebo.

## Run Directory

`make trial TRIAL=bottle-demo` creates one run folder:

```text
runs/bottle-demo/
  recipe.yaml
  detector_params.yaml
  detector_param_args.txt
  command.txt
  summary.txt
  reproduce.sh
  detector.log
  events.jsonl
  manifest.yaml
  evaluation.json
```

The detector writes `events.jsonl` and `manifest.yaml` into this folder. The
first JSONL event is `trial_start` and links to `manifest.yaml`; the manifest
links back to the recipe, run directory, event log, generated detector params,
Git state, container metadata, runtime metadata, and the full detector parameter
snapshot.

## Plan Without Running

Validate a recipe and generate the run files without touching Podman:

```bash
make trial-plan TRIAL=bottle-demo
```

This is useful when reviewing or sharing a proposed trial before running the
robot stack. Plan mode validates recipe structure; it is not proof that the
scenario actually executed in Gazebo. Preparing a run removes stale detector
outputs from that run folder so old `events.jsonl`, `manifest.yaml`, detector
logs, or evaluations are not accidentally packaged as fresh output.

## Reproduce From A Run Folder

Every run folder contains a self-contained launcher:

```bash
runs/bottle-demo/reproduce.sh
```

It reruns the copied `recipe.yaml` from that folder:

```bash
make trial RECIPE="/absolute/path/to/runs/bottle-demo/recipe.yaml"
```

## Evaluate A Trial

After a live detector run has produced `events.jsonl`, summarize the latest
trial segment:

```bash
make trial-evaluate TRIAL=bottle-demo
```

Default output:

```text
runs/bottle-demo/evaluation.json
```

The evaluator reports first object localization time, first target localization
time, first target confirmation time, navigation request/result timing, class
counts, terminal status, and warnings such as "no target localized" or
"navigation requested for non-target class." This is a minimal output check,
not a full grading scorer.

## Package A Trial

Create a shareable package:

```bash
make trial-pack TRIAL=bottle-demo
```

Default output:

```text
runs/openhri-bottle-demo-repro.zip
```

The package contains the run directory, including the recipe, manifest, event
log, summary, generated detector params, and reproduction script when those
outputs exist. Packaging is allowed before a trial finishes, but the packager
warns if `manifest.yaml` or `events.jsonl` do not exist yet. When completed
detector outputs exist, the packager also warns if `evaluation.json` is
missing.

## Tool Split

The repo now exposes five small tools:

- Trial Runner: `make trial`, backed by `scripts/trial_runner.py`.
- Event Recorder: JSONL events emitted by `object_detector.event_log`.
- Run Manifest Generator: YAML manifests emitted by `object_detector.run_manifest`.
- Trial Evaluator: `make trial-evaluate`, backed by `scripts/trial_evaluator.py`.
- Reproducibility Packager: `make trial-pack`, backed by `scripts/trial_packager.py`.

## Advanced Overrides

`make detector` still supports low-level ROS overrides through
`DETECTOR_ROS_ARGS`, but public trial runs should prefer recipes. The recipe
runner generates a per-run `detector_params.yaml` and starts the detector with
both the normal config and the generated override file.
