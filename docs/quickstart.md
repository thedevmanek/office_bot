# Quickstart

This guide takes you from a clean checkout to a running OpenHRI Office simulation with object detection and the object search console.

Use the commands from the repository root unless a step says otherwise.

## 1. Start Podman

On macOS, start the Podman virtual machine first:

```bash
podman machine start
```

Linux users usually do not need this step.

## 2. Pull And Start The Preview Container

```bash
make doctor
make start
```

`make doctor` runs read-only preflight checks. `make start` pulls the published GitHub Container Registry runtime image, starts the container, mounts this checkout read-only, builds the mounted ROS workspace into named Podman volumes, and prints the browser URLs. It does not build the image locally.

Open the noVNC desktop:

```text
http://localhost:6080/vnc.html?autoconnect=1&resize=remote
```

Expected result:

- A browser-based Linux desktop opens.
- Desktop launchers are available for OpenHRI Office and the object UI.
- `make ps` shows the `openhri-office` container running.

## 3. Launch The Office Simulation

In a terminal on your host machine:

```bash
make sim
```

Leave this command running. It starts Gazebo, spawns the robot, opens RViz, starts SLAM, activates Nav2, and bridges the camera/lidar topics into ROS 2.

Expected result:

- Gazebo loads the office environment.
- RViz opens in the noVNC desktop.
- The robot appears in both Gazebo and RViz.
- Logs eventually show Nav2 managed nodes becoming active.

You can also launch the same simulation from the noVNC desktop by opening **OpenHRI Office**.

## 4. Start Object Detection

Open a second host terminal and run:

```bash
make detector
```

This starts the detector in the background and streams logs in the terminal.

Press `Ctrl-C` when you want to stop following logs. The detector keeps running. Stop it explicitly with:

```bash
make detector-stop
```

## 5. Open The Object Search Console

Open:

```text
http://localhost:8080/
```

Expected result:

- The console shows connection and navigation status.
- Confirmed object tracks appear after stable detections.
- Each object card shows class, track id, confidence, detections, and map coordinates.
- The **Navigate** button sends Nav2 to an approach pose near the selected object.

## 6. Run The Demo Task

Use [Object Search and Approach](object-search-and-approach.md) as the demo script:

1. Start the simulation with `make sim`.
2. Start detection with `make detector`.
3. Put a recognizable object in the robot camera view, or navigate the camera view toward an existing object.
4. Wait for a confirmed object card in the web console.
5. Check the class, confidence, detections, and coordinates.
6. Select **Navigate** for the target track.
7. Watch RViz and Gazebo while the robot approaches the stand-off pose.

## Useful Checks

Open a ROS-ready shell in the container:

```bash
make shell
```

Inside the container:

```bash
ros2 topic list
ros2 topic echo /camera/image_raw --once --field header
ros2 topic echo /lidar --once --field header
ros2 topic echo /detected_objects_markers --once
```

Follow detector logs:

```bash
make detector-logs
```

Print browser URLs:

```bash
make urls
```

## Stop And Reset

Stop the detector:

```bash
make detector-stop
```

Stop and remove the preview container:

```bash
make down
```

Build the local runtime image and recreate the container:

```bash
make restart-local
```

To recreate from the published runtime image instead, run:

```bash
make restart
```

## Platform Notes

Apple Silicon macOS uses `linux/arm64` by default.

Intel Linux and Intel Windows users can run:

```bash
OPENHRI_PLATFORM=linux/amd64 make start
```

For container details, ports, image tags, and troubleshooting, see [container-quickstart.md](container-quickstart.md) and [troubleshooting.md](troubleshooting.md).
