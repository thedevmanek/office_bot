# Object Search and Approach

Object Search and Approach is the primary OpenHRI Office research task. It demonstrates a complete HRI-relevant robot loop: detect an everyday object, localize it in the world, expose the robot's belief state to a human, and navigate to a useful stand-off pose.

## Research Value

This task gives researchers a concrete base for studying:

- Human-guided object search.
- Trust in robot perception and remembered object locations.
- Transparency of robot state during perception and navigation.
- Operator decision-making in shared-autonomy workflows.
- Service-robot approach behavior in office environments.

## System Behavior

1. Camera images arrive on `/camera/image_raw`.
2. YOLOX-X detects target objects.
3. Lidar data is fused with the detection box.
4. The object is localized in the map frame.
5. A confirmed object track is created.
6. Markers and obstacle clouds are published.
7. The web UI exposes object class, track id, location, and robot status.
8. A researcher or operator requests navigation to the tracked object.
9. Nav2 evaluates reachable approach options.
10. The robot navigates to a stand-off pose and stops.

## What Researchers Can Modify

- Target object class.
- Detector confidence threshold.
- Track confirmation threshold.
- Object association radius.
- Approach offset and stop distance.
- Dynamic replanning behavior.
- UI wording and status presentation.
- Object placement and robot start pose.

## Simulation Workflow

Start the preview:

```bash
make start
```

Launch the detector:

```bash
make detector
```

Open:

```text
http://localhost:8080/
```

Useful ROS topics:

- `/clock`
- `/camera/image_raw`
- `/camera/camera_info`
- `/lidar`
- `/lidar/points`
- `/detected_objects_markers`
- `/detected_object_obstacles`
- `/cmd_vel_stamped`

## Trial Template

A compact repeatable trial can use:

1. Target class, such as `chair`, `bottle`, or `backpack`.
2. Fixed object placement.
3. Fixed robot start pose.
4. Detector and tracking enabled.
5. Confirmed object track in the UI.
6. Navigation request from the UI.
7. Final distance and outcome label.
8. Reset before the next run.

## Research Signals

Core signals:

- Time to first detection.
- Time to confirmed track.
- Localized object pose.
- Position confidence.
- Navigation request time.
- Final robot-to-object distance.
- Number of operator interventions.
- Final outcome label.

HRI signals:

- Operator confidence in the robot's displayed state.
- Perceived clarity of status messages.
- Perceived safety of final approach.
- Perceived robot competence.

## Event Logging

Use [logging-spec.md](logging-spec.md) to capture a lightweight JSONL trace for repeatable comparison across runs.
