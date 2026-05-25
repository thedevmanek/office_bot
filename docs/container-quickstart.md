# Container Quickstart

The OpenHRI Office container is the recommended way to share the preview with researchers. It packages the desktop, ROS 2 workspace, simulation tools, object detection stack, and browser access behind a small set of commands.

## Start With Podman Compose

From the repository root:

```bash
make start
```

Open:

```text
http://localhost:6080/vnc.html?autoconnect=1&resize=remote
```

On macOS, start the Podman machine first when needed:

```bash
podman machine start
```

## Platform Selection

Apple Silicon macOS uses the native ARM image by default:

```text
linux/arm64
```

Intel Linux and Intel Windows users can run:

```bash
OPENHRI_PLATFORM=linux/amd64 make start
```

The default image tag is:

```text
openhri-office:0.1.0-preview
```

Use a published image by overriding the tag:

```bash
OPENHRI_IMAGE=ghcr.io/openhri/openhri-office:0.1.0-preview make start
```

## Desktop And Web UI

The noVNC desktop includes:

- **OpenHRI Office**: office world, reference robot, RViz, navigation, and simulation launch.
- **OpenHRI Object UI**: YOLOX-X object detection, object tracks, status, and navigation controls.

The object UI is exposed on the host at:

```text
http://localhost:8080/
```

## YOLOX-X Checkpoint

The image build downloads and validates the official YOLOX-X checkpoint automatically. To refresh or revalidate it inside a running container:

```bash
make checkpoint
```

## Exposed Ports

- `6080`: noVNC browser desktop.
- `5900`: VNC access.
- `8080`: OpenHRI object UI.

## Notes For Researchers

- The container uses software rendering for broad laptop compatibility.
- The first build downloads ROS packages, PyTorch CPU wheels, YOLOX, and the YOLOX-X checkpoint.
- The browser preview is the best path for evaluation, demos, and study-design feedback.
