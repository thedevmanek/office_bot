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
- 8 GB or more free disk space for the published image and runtime data.
- A machine with enough memory for Gazebo, RViz, Nav2, and PyTorch CPU inference.
- On macOS, a running Podman machine:

```bash
podman machine start
```

Apple Silicon macOS defaults to `linux/arm64`. Intel Linux and Windows users can run commands with:

```bash
OPENHRI_PLATFORM=linux/amd64
```

The supported runtime is Podman. The runtime image is published on GitHub Container Registry as:

```text
ghcr.io/thedevmanek/openhri-office:0.1.0-preview
```

## Quickstart

From the repository root:

```bash
make doctor
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

The first `make start` runs read-only preflight checks, pulls `ghcr.io/thedevmanek/openhri-office:0.1.0-preview`, starts the container, mounts this checkout read-only, builds the mounted ROS workspace into named Podman volumes, and prints browser URLs. It does not build the image locally. Use `make start-local` when you intentionally want to build the runtime image from this checkout.

The runtime image contains ROS, Gazebo, RViz, Nav2, PyTorch, YOLOX, noVNC, startup scripts, and the YOLOX checkpoint. The repository checkout provides the ROS packages, launch files, world assets, object detector code, web UI, docs, and configs at runtime.

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
make doctor         # Check Podman, platform, ports, and disk space
make start          # Pull runtime, mount source, and bootstrap workspace
make start-cached   # Run the cached image without pulling
make start-local    # Build the runtime image locally and run it
make bootstrap      # Rebuild the mounted ROS workspace
make test           # Rebuild and run package tests inside the container
make sim            # Launch Gazebo, RViz, SLAM, Nav2, and the robot
make researcher-session  # Recreate a 2x2 tmux split grid for logs and artifacts
make detector       # Start/restart object detection and stream logs
make detector-bg    # Start/restart detection without following logs
make detector-logs  # Follow detector logs
make detector-stop  # Stop the detector process
make shell          # Open a ROS-ready shell in the container
make urls           # Print browser URLs
make restart        # Pull and recreate the runtime preview container
make restart-local  # Build the runtime image locally and recreate the preview
make down           # Stop and remove the preview container
make clean-volumes  # Remove cached build/install/log volumes
```

## Troubleshooting

- Run `make doctor` for read-only preflight checks and exact fix commands.
- If `make start` cannot connect to Podman on macOS, run `podman machine start` and retry.
- If ports are already in use, override them, for example `OPENHRI_NOVNC_PORT=6081 OPENHRI_OBJECT_UI_PORT=8081 make start`.
- If Gazebo reports `Unable to find uri[model://...]`, recreate the container with `make restart`; the simulation launch also sets the model path at runtime.
- If you changed source under `dev_ws/`, run `make bootstrap` before launching again.
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

## Researcher Workflow

Use [docs/researcher-guide.md](docs/researcher-guide.md) when sharing the
project with researchers who need to evaluate, modify, or package studies.

The recommended validation path is:

```bash
make doctor
make start
make researcher-session
make trial-pack TRIAL=bottle-demo
```

`make researcher-session` opens one tmux `run` window split into a 2x2 grid:
simulation and detector on the left, container logs and run artifacts on the
right. It replaces any stale `openhri` tmux session instead of reusing old
layouts. Mouse scrolling is enabled. Use `Ctrl-b` then `X` or `F12` to stop the
simulation, detector, and tmux session. Use `make researcher-attach` only when
you intentionally want to reattach to the existing session, and
`make researcher-stop` to stop from a normal terminal.
If a pane command exits or fails, that pane stays open at a shell prompt; type
`rerun` in the pane to execute the same command again.

Most study changes should start by copying a recipe in `experiments/trials/`
and validating it with the preview container running:

```bash
make trial-plan TRIAL=<trial-id>
make test
```

## Documentation

- [Quickstart](docs/quickstart.md): shortest path to a working demo.
- [Container quickstart](docs/container-quickstart.md): image, ports, platform, and operations notes.
- [Researcher guide](docs/researcher-guide.md): trial recipes, tinker points, artifacts, and validation.
- [Reproducibility](docs/reproducibility.md): recipe-backed runs, manifests, logs, and packaging.
- [Runtime image release](docs/runtime-image-release.md): GHCR publishing and tag policy.
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
