# Container Quickstart

The OpenHRI Office container is the recommended way to run and share the simulation preview. It packages ROS 2 Humble, Gazebo/Ignition, RViz, Nav2, SLAM Toolbox, YOLOX-X, noVNC, and the object search web UI behind a small set of commands.

## Start

From the repository root:

```bash
make start
```

Open the desktop:

```text
http://localhost:6080/vnc.html?autoconnect=1&resize=remote
```

Open the object UI:

```text
http://localhost:8080/
```

## What The Container Provides

- A noVNC desktop on port `6080`.
- Optional direct VNC access on port `5900`.
- The object search console on port `8080`.
- ROS 2 workspace at `/workspace/openhri-office/dev_ws`.
- Shell profile at `/etc/profile.d/openhri-container-env.sh`.
- Desktop launchers for the office simulation and object UI.
- A downloaded YOLOX-X checkpoint during image build.

## Platform Selection

Apple Silicon macOS and Raspberry Pi class ARM hosts use:

```text
linux/arm64
```

Intel Linux and Intel Windows users should run:

```bash
OPENHRI_PLATFORM=linux/amd64 make start
```

The default local image tag is:

```text
openhri-office:0.1.0-preview
```

To use a published image:

```bash
OPENHRI_IMAGE=ghcr.io/openhri/openhri-office:0.1.0-preview make start
```

## Port Overrides

If a host port is already in use:

```bash
OPENHRI_NOVNC_PORT=6081 OPENHRI_OBJECT_UI_PORT=8081 make start
```

Then open:

```text
http://localhost:6081/vnc.html?autoconnect=1&resize=remote
http://localhost:8081/
```

## Daily Operations

```bash
make ps             # Show compose container status
make logs           # Follow container logs
make shell          # Open a ROS-ready shell
make sim            # Launch Gazebo, RViz, SLAM, Nav2, and the robot
make detector       # Start object detection and stream logs
make detector-bg    # Start object detection without following logs
make detector-logs  # Follow detector logs
make detector-stop  # Stop object detection
make checkpoint     # Revalidate/download the YOLOX-X checkpoint
make restart        # Rebuild and recreate the preview container
make down           # Stop and remove the preview container
```

## Recommended Run Order

Use three views:

1. Browser: noVNC desktop.
2. Terminal 1: `make sim`.
3. Terminal 2: `make detector`.

Then open the object UI at:

```text
http://localhost:8080/
```

## Notes For Researchers

- The container uses software rendering for broad laptop compatibility.
- The first build downloads ROS packages, PyTorch CPU wheels, YOLOX, and the YOLOX-X checkpoint.
- Object detection is CPU-only by default; frame rate depends on host performance.
- The simulation launch sets Gazebo model paths so `model://...` assets resolve inside the installed workspace.
- The browser preview is the best path for evaluation, demos, and study-design feedback.

## When To Rebuild

Run `make restart` after changing:

- `Containerfile`
- `compose.yaml`
- `container/*.sh`
- package dependencies
- installed model assets

For pure Python or launch-file edits during development, you can usually rebuild only the affected package inside the container:

```bash
make shell
colcon build --symlink-install --packages-select office_bot_model
source install/setup.bash
```

## Troubleshooting

Use [troubleshooting.md](troubleshooting.md) for common Podman, Gazebo, detector, and browser issues.
