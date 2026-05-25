# Object Search And Approach

Object Search and Approach is the primary OpenHRI Office research task. It demonstrates a complete HRI-relevant robot loop: detect an everyday object, localize it in the world, expose the robot's belief state to a human, and navigate to a useful stand-off pose.

## Demo Goal

Show that a researcher can run a repeatable office scenario where a mobile robot:

1. Sees an object.
2. Estimates where that object is in the map.
3. Remembers the object as a track.
4. Shows the track to a human operator.
5. Accepts a navigation request.
6. Approaches the object and stops at a safe offset.

## Run The Task

Start the preview container:

```bash
make start
```

Launch the simulation:

```bash
make sim
```

Start object detection in another terminal:

```bash
make detector
```

Open the object search console:

```text
http://localhost:8080/
```

## What To Watch

In Gazebo:

- The robot in the office world.
- Obstacles and furniture around the robot.
- Robot movement after a navigation request.

In RViz:

- `/map`
- `/tf` and `/tf_static`
- robot pose and odometry
- lidar scans and point clouds
- object markers
- Nav2 global and local plans

In the object search console:

- connection state
- confirmed object tracks
- class name and track id
- confidence and detection count
- map coordinates
- active navigation target

## System Behavior

1. Camera images arrive on `/camera/image_raw`.
2. YOLOX-X detects COCO object classes.
3. The detection box is fused with lidar/camera geometry.
4. The object is localized in the map frame.
5. A confirmed object track is created after repeated observations.
6. Markers and object obstacle clouds are published.
7. The web UI exposes object class, track id, location, and robot status.
8. A researcher or operator requests navigation to the tracked object.
9. Nav2 evaluates reachable approach options.
10. The robot navigates to a stand-off pose and stops.

## Useful ROS Topics

```text
/clock
/camera/image_raw
/camera/camera_info
/lidar
/lidar/points
/detected_objects_markers
/detected_object_obstacles
/cmd_vel_stamped
/map
/tf
/tf_static
```

Quick checks from `make shell`:

```bash
ros2 topic list
ros2 topic echo /camera/image_raw --once --field header
ros2 topic echo /detected_objects_markers --once
ros2 topic echo /detected_object_obstacles --once
```

## What Researchers Can Modify

- Target object class.
- Detector confidence threshold.
- Track confirmation threshold.
- Object association radius.
- Approach offset and stop distance.
- Dynamic replanning behavior.
- UI wording and status presentation.
- Object placement and robot start pose.
- Trial outcome labels and event logging.

Common tuning files:

```text
dev_ws/src/object_detector/config/object_detector.yaml
dev_ws/src/object_detector/object_detector/localization.py
dev_ws/src/object_detector/object_detector/tracking.py
dev_ws/src/object_detector/object_detector/navigation.py
dev_ws/src/object_detector/web/index.html
```

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
