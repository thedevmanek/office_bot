# Event Log And Run Manifest

OpenHRI `office_bot` uses lightweight event logging and a per-run manifest so teams can compare runs, inspect decisions, and debug behavior from concrete traces.

The recommended first format is JSONL: each line is one event.

## File Name

```text
log/events/openhri_object_search_<run_id>.jsonl
```

The matching run manifest is written by default to:

```text
log/manifests/openhri_object_search_<run_id>_manifest.yaml
```

The `object_detector` node writes this format at runtime when `event_log_enabled` is true. If `event_log_path` is set, that exact path is used. Otherwise the node writes `<event_log_dir>/openhri_object_search_<event_log_run_id>.jsonl`; when `event_log_run_id` is empty the node generates a timestamped run ID. The default `event_log_dir` is under the ROS workspace `log/` directory, which is writable in the containerized workflow. If the log file cannot be opened or written, the node warns once and continues without event logging.

Runtime parameters:

- `event_log_enabled`: default `true`
- `event_log_dir`: default `log/events`
- `event_log_path`: default empty, overrides `event_log_dir`
- `event_log_run_id`: default empty, generated automatically
- `event_log_scenario`: default `object_search_approach`
- `run_manifest_enabled`: default `true`
- `run_manifest_dir`: default `log/manifests`
- `run_manifest_path`: default empty, overrides `run_manifest_dir`
- `run_manifest_trial_id`: default empty
- `run_manifest_world`: default `office_world`
- `run_manifest_robot_start_pose`: default empty
- `run_manifest_target_class`: default empty
- `run_manifest_target_object_pose`: default empty
- `run_manifest_random_seed`: default empty
- `run_manifest_notes`: default empty
- `run_manifest_recipe_path`: default empty
- `run_manifest_run_dir`: default empty

The manifest records the run ID, trial ID, declared scenario inputs, runtime context, Git context when available, recipe path, output paths, and full object-detector parameter snapshot. Use [reproducibility.md](reproducibility.md) for the recipe-based trial workflow.

## Common Fields

Every event:

- `run_id`
- `t`
- `event`
- `scenario`

Recommended context:

- `robot_pose`
- `target_class`
- `track_id`
- `source`
- `notes`

## Event Types

The current runtime emits `trial_start`, `object_localized`, `track_confirmed`, `navigation_requested`, `navigation_result`, and `tracks_cleared`. The remaining events below are useful for scripted trials and manual annotations.

### trial_start

```json
{"run_id":"001","t":0.0,"event":"trial_start","scenario":"object_search_approach","target_class":"chair","world":"office_world","run_dir":"/workspace/openhri-office/runs/chair-demo","trial_recipe_path":"/workspace/openhri-office/runs/chair-demo/recipe.yaml","run_manifest_path":"/workspace/openhri-office/runs/chair-demo/manifest.yaml"}
```

### object_detected

```json
{"run_id":"001","t":4.2,"event":"object_detected","scenario":"object_search_approach","class":"chair","confidence":0.82}
```

### object_localized

```json
{"run_id":"001","t":5.1,"event":"object_localized","scenario":"object_search_approach","track_id":1,"class":"chair","x":2.4,"y":-0.8,"position_confidence":0.66}
```

### track_confirmed

```json
{"run_id":"001","t":5.8,"event":"track_confirmed","scenario":"object_search_approach","track_id":1,"class":"chair","detections":2}
```

### navigation_requested

```json
{"run_id":"001","t":6.0,"event":"navigation_requested","scenario":"object_search_approach","track_id":1,"class":"chair","source":"web_ui"}
```

### navigation_result

```json
{"run_id":"001","t":18.5,"event":"navigation_result","scenario":"object_search_approach","track_id":1,"class":"chair","status":"succeeded","message":"Navigation succeeded."}
```

### tracks_cleared

```json
{"run_id":"001","t":19.0,"event":"tracks_cleared","scenario":"object_search_approach","track_count":3,"confirmed_count":2,"source":"api"}
```

### trial_end

```json
{"run_id":"001","t":20.0,"event":"trial_end","scenario":"object_search_approach","outcome":"success","interventions":0}
```

## Outcome States

Use a controlled set where possible:

- `success`
- `object_not_observed`
- `localization_pending`
- `track_pending`
- `planning_pending`
- `goal_unreachable`
- `navigation_stopped`
- `object_not_visible_at_goal`
- `operator_cancelled`

## Run Review Targets

Ask whether the log contains enough information to support:

- Object placement and robot start-pose replication.
- Comparison across runs.
- Analysis of recovery and outcome patterns.
- Review of configuration changes.
- Debugging of missed detections and navigation failures.
