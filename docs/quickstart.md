# Quickstart

This is the shortest handoff path for OpenHRI Office. It runs the containerized ROS 2 preview, opens the noVNC desktop, starts object detection, and exposes the object search console.

## 1. Start The Preview

From the repository root:

```bash
make start
```

Open the noVNC desktop:

```text
http://localhost:6080/vnc.html?autoconnect=1&resize=remote
```

On macOS, start the Podman machine first if Podman is not already running:

```bash
podman machine start
```

## 2. Launch The Office Simulation

Use either path:

```bash
make sim
```

Or, inside the noVNC desktop, open the **OpenHRI Office** launcher.

The desktop should show the office world, the reference robot, and RViz.

## 3. Start Object Detection

From the repository root:

```bash
make detector
```

The command starts the detector in the background and immediately streams its logs. Press `Ctrl-C` to stop following logs; use `make detector-stop` when you want to stop the detector process.

Open the object search console:

```text
http://localhost:8080/
```

The console shows confirmed object tracks, confidence, map coordinates, navigation requests, and robot status.

## 4. Run The Demo Task

Follow [Object Search and Approach](object-search-and-approach.md):

1. Place or identify a target object in the office scene.
2. Wait for a confirmed track in the object search console.
3. Check the class, confidence, detections, and coordinates.
4. Select **Navigate** for the target track.
5. Observe Nav2 and RViz while the robot approaches a stand-off pose.

## Common Commands

```bash
make help           # Show all preview commands
make start          # Build and run the noVNC preview
make sim            # Launch the office simulation
make detector       # Start/restart detection and stream logs
make detector-bg    # Start/restart detection without following logs
make detector-logs  # Follow existing object detector logs
make detector-stop  # Stop the background detector
make urls           # Print noVNC and object console URLs
make down           # Stop and remove the preview container
```

## Platform Notes

Apple Silicon macOS uses `linux/arm64` by default. Intel Linux and Intel Windows users can run:

```bash
OPENHRI_PLATFORM=linux/amd64 make start
```

The full container notes are in [container-quickstart.md](container-quickstart.md). Native ROS 2 development is documented in the repository README.
