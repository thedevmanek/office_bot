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
make test           # Rebuild and run package tests inside the container
make sim            # Launch Gazebo, RViz, SLAM, Nav2, and the robot
make researcher-session  # Recreate a 2x2 tmux split grid for logs and artifacts
make trial TRIAL=bottle-demo  # Run a reproducible recipe-backed detector trial
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

For the most transparent researcher run, use one tmux session:

```bash
make researcher-session
```

It opens one tmux `run` window split into a 2x2 grid:

- top-left: simulation launch logs
- bottom-left: recipe-backed detector logs
- top-right: container logs
- bottom-right: live run artifacts

Mouse scrolling is enabled, and pane names are shown in the pane borders. A
separate `shell` window gives an interactive ROS-ready shell, and a `help`
window repeats the controls. Click panes/window names or use tmux keyboard
navigation.

If a pane command exits or fails, that pane stays open at a shell prompt. Type
`rerun` in the pane to execute the same command again, or press Up then Enter to
edit and rerun the last command.

`make researcher-session` replaces any existing `openhri` tmux session, so stale
split-pane layouts are not reused. Use `make researcher-attach` only when you
want to return to the existing session without recreating it.

Stop everything from inside tmux with `Ctrl-b` then `X`, or press `F12`. From a
normal terminal, use `make researcher-stop`.

For a manual run, use three views:

1. Browser: noVNC desktop.
2. Terminal 1: `make sim`.
3. Terminal 2: `make trial TRIAL=bottle-demo`.

Then open the object UI at:

```text
http://localhost:8080/
```

## Notes For Researchers

- The container uses software rendering for broad laptop compatibility.
- The first `make start` pulls the published runtime image, then bootstraps the mounted ROS workspace.
- Source changes under `dev_ws/` usually need `make bootstrap`, not a new image.
- Runtime image changes under `Containerfile`, `compose.yaml`, or `container/` need `make start-local` during development and a new published image for evaluators.
- Run `make test` before sharing a changed branch; tests execute inside the preview container after rebuilding the mounted workspace.
- `make researcher-session` requires tmux on the host and gives researchers full-screen, scrollable views of runtime logs and generated artifacts.
- Object detection is CPU-only by default; frame rate depends on host performance.
- The simulation launch sets Gazebo model paths so `model://...` assets resolve inside the installed workspace.
- The browser preview is the best path for evaluation, demos, and study-design feedback.
- Recipe-backed trials write artifacts under `runs/<trial_id>/`.
- Use `make trial-plan TRIAL=bottle-demo` to validate and materialize a run directory without starting the detector.
- Use `make trial-pack TRIAL=bottle-demo` to create a shareable reproducibility zip.

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
