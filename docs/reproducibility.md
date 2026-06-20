# Reproducibility

The reproducible workflow is recipe-first. A user should not need to hand-write
ROS parameter overrides for a normal trial.

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
experiments/trials/bottle-demo.yaml
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

notes: Baseline bottle search trial for reproducibility checks.
```

Required fields:

- `trial_id`
- `world`
- `seed`
- `robot.start_pose`
- `target.class`
- `target.pose`

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
robot stack.

## Reproduce From A Run Folder

Every run folder contains a self-contained launcher:

```bash
runs/bottle-demo/reproduce.sh
```

It reruns the copied `recipe.yaml` from that folder:

```bash
make trial RECIPE="/absolute/path/to/runs/bottle-demo/recipe.yaml"
```

## Package A Trial

Create a shareable artifact:

```bash
make trial-pack TRIAL=bottle-demo
```

Default output:

```text
runs/openhri-bottle-demo-repro.zip
```

The package contains the run directory, including the recipe, manifest, event
log, summary, generated detector params, and reproduction script. Packaging is
allowed before a trial finishes, but the packager warns if `manifest.yaml` or
`events.jsonl` do not exist yet.

## Tool Split

The repo now exposes four small tools:

- Trial Runner: `make trial`, backed by `scripts/trial_runner.py`.
- Event Recorder: JSONL events emitted by `object_detector.event_log`.
- Run Manifest Generator: YAML manifests emitted by `object_detector.run_manifest`.
- Reproducibility Packager: `make trial-pack`, backed by `scripts/trial_packager.py`.

## Advanced Overrides

`make detector` still supports low-level ROS overrides through
`DETECTOR_ROS_ARGS`, but reproducible runs should prefer recipes. The recipe
runner generates a per-run `detector_params.yaml` and starts the detector with
both the normal config and the generated override file.
