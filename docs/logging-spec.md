# Research Event Log

OpenHRI Office uses lightweight event logging so researchers can compare runs, inspect decisions, and discuss study design from concrete traces.

The recommended first format is JSONL: each line is one event.

## File Name

```text
logs/openhri_object_search_<run_id>.jsonl
```

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

### trial_start

```json
{"run_id":"001","t":0.0,"event":"trial_start","scenario":"object_search_approach","target_class":"chair","world":"office_world"}
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
{"run_id":"001","t":5.8,"event":"track_confirmed","scenario":"object_search_approach","track_id":1,"detections":2}
```

### navigation_requested

```json
{"run_id":"001","t":6.0,"event":"navigation_requested","scenario":"object_search_approach","track_id":1,"source":"web_ui"}
```

### navigation_result

```json
{"run_id":"001","t":18.5,"event":"navigation_result","scenario":"object_search_approach","track_id":1,"status":"succeeded","final_distance_m":1.1}
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

## Research Feedback Targets

Ask researchers whether the log contains enough information to support:

- Object placement and robot start-pose replication.
- Comparison across runs.
- Analysis of recovery and outcome patterns.
- Participant-facing transparency studies.
- Trust and perceived-competence studies.
