# Container Quickstart

The OpenHRI Office container is the recommended way to run and share the simulation preview. It packages ROS 2 Humble, Gazebo/Ignition, RViz, Nav2, SLAM Toolbox, YOLOX-X, noVNC, and the runtime scripts behind a small set of Podman commands. The repository checkout is mounted into the runtime container when you start it.

## Start

From the repository root:

```bash
make doctor
make start
```

`make doctor` runs read-only preflight checks. `make start` pulls and runs the published GitHub Container Registry runtime image:

```text
ghcr.io/thedevmanek/openhri-office:0.1.0-preview
```

Open the desktop:

```text
http://localhost:6080/vnc.html?autoconnect=1&resize=remote
```

After starting the detector with `make detector`, open the object UI:

```text
http://localhost:8080/
```

## What The Container Provides

- A noVNC desktop on port `6080`.
- Optional direct VNC access on port `5900`.
- The object search console on port `8080` after `make detector`.
- A read-only mount of this checkout at `/workspace/openhri-office`.
- Named Podman volumes for `/workspace/openhri-office/dev_ws/build`, `install`, and `log`.
- Shell profile at `/etc/profile.d/openhri-container-env.sh`.
- Desktop launchers for the office simulation and object UI.
- The YOLOX-X checkpoint inside the published image.

## Platform Selection

Apple Silicon macOS and Raspberry Pi class ARM hosts use:

```text
linux/arm64
```

Intel Linux and Intel Windows users should run:

```bash
OPENHRI_PLATFORM=linux/amd64 make start
```

The default published runtime image tag is:

```text
ghcr.io/thedevmanek/openhri-office:0.1.0-preview
```

The project supports these image platforms:

```text
linux/amd64
linux/arm64
```

## Port Overrides

If a host port is already in use:

```bash
OPENHRI_NOVNC_PORT=6081 OPENHRI_OBJECT_UI_PORT=8081 make start
```

Then open noVNC:

```text
http://localhost:6081/vnc.html?autoconnect=1&resize=remote
```

After `make detector`, open the object UI:

```text
http://localhost:8081/
```

## Daily Operations

```bash
make doctor         # Run read-only preflight checks
make ps             # Show compose container status
make logs           # Follow container logs
make shell          # Open a ROS-ready shell
make start          # Pull runtime, mount source, and bootstrap workspace
make start-cached   # Run the cached image without pulling
make start-local    # Build the runtime image locally and run it
make bootstrap      # Rebuild the mounted ROS workspace
make sim            # Launch Gazebo, RViz, SLAM, Nav2, and the robot
make detector       # Start object detection and stream logs
make detector-bg    # Start object detection without following logs
make detector-logs  # Follow detector logs
make detector-stop  # Stop object detection
make checkpoint     # Revalidate/download the YOLOX-X checkpoint
make restart        # Pull and recreate the runtime preview
make restart-local  # Build the runtime image locally and recreate the preview
make down           # Stop and remove the preview container
make clean-volumes  # Remove cached build/install/log volumes
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
- The first `make start` pulls the published runtime image, then bootstraps the mounted ROS workspace.
- Source changes under `dev_ws/` usually need `make bootstrap`, not a new image.
- Runtime image changes under `Containerfile`, `compose.yaml`, or `container/` need `make start-local` during development and a new published image for evaluators.
- Object detection is CPU-only by default; frame rate depends on host performance.
- The simulation launch sets Gazebo model paths so `model://...` assets resolve inside the installed workspace.
- The browser preview is the best path for evaluation, demos, and study-design feedback.

## When To Rebuild

Run `make start-local` or `make restart-local` after changing runtime image inputs:

- `Containerfile`
- `compose.yaml`
- `container/*.sh`
- desktop launcher files

Run `make bootstrap` after changing mounted workspace inputs:

- `dev_ws/**`
- package dependencies in `package.xml`
- launch files, models, configs, object detector code, or web UI

For pure Python or launch-file edits during development, you can usually rebuild only the affected package inside the container:

```bash
make bootstrap
```

## Troubleshooting

Use [troubleshooting.md](troubleshooting.md) for common Podman, Gazebo, detector, and browser issues.

For GHCR publishing details, see [runtime-image-release.md](runtime-image-release.md).
