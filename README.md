# OpenHRI Office Simulation

OpenHRI Office Simulation is a containerized ROS 2 Humble demo for repeatable human-robot interaction research in office service environments.

It starts a browser-accessible desktop with Gazebo, RViz, Nav2, SLAM, a reference mobile robot, YOLOX-X object detection, object localization, object memory, and a web console for selecting objects and requesting navigation.

This is the simulation branch. Raspberry Pi hardware bringup lives on the `hardware` branch.

## What You Can Do

- Run the full office simulation from a browser.
- Watch the reference robot build a map and publish sensor data.
- Detect everyday objects from the robot camera.
- Localize confirmed objects with camera and lidar data.
- Inspect object tracks in a web UI.
- Send the robot to an approach pose near a selected object.
- Modify detection, localization, navigation, UI, and study parameters.

## Prerequisites

- Podman with Compose support.
- 8 GB or more free disk space for the image and model checkpoint.
- A machine with enough memory for Gazebo, RViz, Nav2, and PyTorch CPU inference.
- On macOS, a running Podman machine:

```bash
podman machine start
```

Apple Silicon macOS defaults to `linux/arm64`. Intel Linux and Windows users can run commands with:

```bash
OPENHRI_PLATFORM=linux/amd64
```

## Quickstart

From the repository root:

```bash
make start
```

Open the noVNC desktop:

```text
http://localhost:6080/vnc.html?autoconnect=1&resize=remote
```

Launch the office simulation:

```bash
make sim
```

When Gazebo and RViz are running, start object detection in another terminal:

```bash
make detector
```

Open the object search console:

```text
http://localhost:8080/
```

For a step-by-step walkthrough, use [docs/quickstart.md](docs/quickstart.md).

## Expected First Run

The first `make start` can take a while because it builds the ROS image, installs dependencies, installs YOLOX, and downloads the YOLOX-X checkpoint.

After `make sim`, you should see:

- Gazebo/Ignition loading the office world.
- The Office Bot robot spawned near the start pose.
- RViz showing the robot, lidar data, map, and Nav2 views.
- Nav2 lifecycle nodes becoming active after the map and transforms settle.

After `make detector`, you should see:

- Detector logs streaming in your terminal.
- The object search console at `http://localhost:8080/`.
- Confirmed object cards once detections are stable.

## Common Commands

```bash
make help           # Show simulation commands
make start          # Build and run the browser preview container
make sim            # Launch Gazebo, RViz, SLAM, Nav2, and the robot
make detector       # Start/restart object detection and stream logs
make detector-bg    # Start/restart detection without following logs
make detector-logs  # Follow detector logs
make detector-stop  # Stop the detector process
make shell          # Open a ROS-ready shell in the container
make urls           # Print browser URLs
make restart        # Rebuild/recreate the preview container
make down           # Stop and remove the preview container
```

## Troubleshooting

- If `make start` cannot connect to Podman, run `podman machine start` and retry.
- If ports are already in use, override them, for example `OPENHRI_NOVNC_PORT=6081 OPENHRI_OBJECT_UI_PORT=8081 make start`.
- If Gazebo reports `Unable to find uri[model://...]`, rebuild the container with `make restart`; the simulation launch also sets the model path at runtime.
- If the detector cannot find the YOLOX checkpoint, run `make checkpoint`.
- If the UI shows no objects, keep Gazebo and the detector running, confirm `/camera/image_raw` is publishing, and place a COCO-class object in view.

More detail is in [docs/troubleshooting.md](docs/troubleshooting.md).

## Project Layout

```text
dev_ws/
  launch_sim.sh
  src/
    office_bot_model/                 Robot model, office world, launch, Nav2, RViz
    office_bot_controller_handlers/   Controller helper nodes
    object_detector/                  Detection, localization, tracking, web UI
container/                            Desktop, detector, checkpoint, and shell scripts
docs/                                 Quickstart, task guide, study notes, troubleshooting
```

Common object-search tuning points:

- `dev_ws/src/object_detector/config/object_detector.yaml`
- `dev_ws/src/object_detector/object_detector/localization.py`
- `dev_ws/src/object_detector/object_detector/tracking.py`
- `dev_ws/src/object_detector/object_detector/navigation.py`
- `dev_ws/src/object_detector/web/index.html`

## Documentation

- [Quickstart](docs/quickstart.md): shortest path to a working demo.
- [Container quickstart](docs/container-quickstart.md): image, ports, platform, and operations notes.
- [Object Search and Approach](docs/object-search-and-approach.md): the primary research task.
- [Troubleshooting](docs/troubleshooting.md): common setup and runtime problems.
- [Demo script](docs/demo-script.md): suggested 60 to 90 second demo structure.
- [Study ideas](docs/study-ideas): HRI study directions built on the same task.

## Native ROS 2 Workflow

The container path is the recommended handoff path. For native Ubuntu 22.04 / ROS 2 Humble development:

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

## License

OpenHRI Office Simulation is licensed under the Apache License 2.0. See [LICENSE](LICENSE).
