# OpenHRI Office Simulation

OpenHRI Office Simulation is a ROS 2 Humble reference scenario for reproducible human-robot interaction research in office service environments.

This branch contains the containerized simulation preview, reference mobile robot model, navigation stack, object detection/localization pipeline, and browser-based object search console. Hardware-backed Raspberry Pi bringup lives on the `hardware` branch.

## Fastest Preview

From the repository root:

```bash
make start
```

Open the noVNC desktop:

```text
http://localhost:6080/vnc.html?autoconnect=1&resize=remote
```

Start the object detector and web console. This streams detector logs in the terminal:

```bash
make detector
```

Press `Ctrl-C` to stop following the logs. The detector keeps running in the container; use `make detector-stop` to stop it.

Open the object search console:

```text
http://localhost:8080/
```

For a guided run, use [docs/quickstart.md](docs/quickstart.md).

## What To Look At

- **Office world**: Gazebo/Ignition assets for a repeatable indoor service environment.
- **Reference robot**: robot model, sensors, controllers, TF frames, and RViz configuration.
- **Autonomy stack**: Nav2, SLAM Toolbox, robot localization, ros2_control, and Gazebo bridge wiring.
- **Object pipeline**: YOLOX-X detection, lidar/camera localization, track confirmation, obstacle publishing, and navigation-to-object support.
- **Object search console**: browser UI for confirmed tracks, confidence, coordinates, navigation requests, and robot status.

The primary research demo is [Object Search and Approach](docs/object-search-and-approach.md).

## Where To Modify

```text
dev_ws/
  launch_sim.sh
  src/
    office_bot_model/                 Robot model, world, launch, Nav2, RViz
    office_bot_controller_handlers/   Controller helper nodes
    object_detector/                  Perception, tracking, navigation, web UI
docs/
  quickstart.md                       Main simulation run path
  object-search-and-approach.md       Research task walkthrough
  logging-spec.md                     Trial event logging shape
```

Common object-search tuning points live in:

- `dev_ws/src/object_detector/config/object_detector.yaml`
- `dev_ws/src/object_detector/object_detector/localization.py`
- `dev_ws/src/object_detector/object_detector/tracking.py`
- `dev_ws/src/object_detector/object_detector/navigation.py`
- `dev_ws/src/object_detector/web/index.html`

## Useful Commands

```bash
make help           # Show available simulation commands
make start          # Build and run the browser preview
make sim            # Launch the office simulation in the container
make detector       # Start/restart detection and stream logs
make detector-bg    # Start/restart detection without following logs
make detector-logs  # Follow existing object detector logs
make shell          # Open a ROS-ready shell in the container
make detector-stop  # Stop the background detector
make down           # Stop and remove the preview container
```

Apple Silicon macOS defaults to `linux/arm64`. Intel Linux and Windows users can run:

```bash
OPENHRI_PLATFORM=linux/amd64 make start
```

## Native ROS 2 Workflow

Use the container path above for handoff and review. For native Ubuntu 22.04 / ROS 2 Humble development:

```bash
cd dev_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/local_setup.bash
./launch_sim.sh
```

Targeted builds:

```bash
colcon build --symlink-install --packages-select office_bot_model
colcon build --symlink-install --packages-select office_bot_controller_handlers
colcon build --symlink-install --packages-select object_detector
```

## More Docs

- [Container quickstart](docs/container-quickstart.md)
- [Demo script](docs/demo-script.md)
- [Study ideas](docs/study-ideas)

## License

OpenHRI Office Simulation is licensed under the Apache License 2.0. See [LICENSE](LICENSE).
