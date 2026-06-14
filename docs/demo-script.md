# Demo Script

Target length: 60 to 90 seconds.

## Core Message

OpenHRI Office is an open-source ROS 2 reference scenario for reproducible HRI research in office service environments.

## Demo Flow

1. **Office World**
   - Visual: Gazebo office environment.
   - Message: "A shared simulated environment for repeatable HRI scenarios."

2. **Reference Robot**
   - Visual: robot in Gazebo and RViz.
   - Message: "A mobile service robot with ROS 2 navigation, sensors, and inspectable state."

3. **Autonomy Stack**
   - Visual: RViz with map, robot pose, lidar, camera, and Nav2 elements.
   - Message: "The stack connects SLAM, localization, Nav2, ros2_control, and Gazebo simulation."

4. **Object Perception**
   - Visual: camera detections, object markers, and localized tracks.
   - Message: "Objects are detected with YOLOX-X, localized with lidar/camera fusion, tracked, and exposed to the robot."

5. **Research UI**
   - Visual: object-location UI.
   - Message: "Researchers can inspect robot belief state, select targets, and build interaction studies on top of the same scenario."

6. **OpenHRI**
   - Visual: repo, domain, or OpenHRI wordmark.
   - Message: "OpenHRI gives researchers a practical base for repeatable HRI experiments."

## Voiceover Draft

OpenHRI is an open-source platform for reproducible human-robot interaction research.

This is OpenHRI Office, the first reference scenario: a ROS 2 office environment with a mobile service robot, navigation, perception, object tracking, and a lightweight interaction UI.

The task is simple to understand and rich enough for research: detect an object, localize it with camera and lidar, show the robot's belief state, and navigate to a useful stand-off position.

Researchers can run it in a browser, inspect the ROS 2 stack, modify the task parameters, and extend it into studies of guidance, transparency, trust, and robot approach behavior.

## Commands To Record

```bash
make start
make sim
make detector
```

Useful topic checks:

```bash
ros2 topic list
ros2 topic echo /detected_objects_markers --once
ros2 topic echo /detected_object_obstacles --once
```

Web UI:

```text
http://localhost:8080/
```
