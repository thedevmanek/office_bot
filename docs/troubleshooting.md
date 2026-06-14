# Troubleshooting

Use this guide when the preview does not start cleanly or the object search workflow does not produce tracks.

Start with the read-only preflight checks:

```bash
make doctor
```

## Podman Is Not Running

Symptom:

```text
Cannot connect to Podman
```

Fix on macOS:

```bash
podman machine start
make start
```

Check status:

```bash
podman machine list
make ps
```

## Port Already In Use

Symptoms:

- noVNC does not open.
- Podman reports a bind error for `6080`, `5900`, or `8080`.

Fix:

```bash
OPENHRI_NOVNC_PORT=6081 OPENHRI_VNC_PORT=5901 OPENHRI_OBJECT_UI_PORT=8081 make start
```

Open:

```text
http://localhost:6081/vnc.html?autoconnect=1&resize=remote
http://localhost:8081/
```

## Gazebo Cannot Find `model://...` Assets

Symptom:

```text
Unable to find uri[model://toilet]
Failed to load a world
```

The simulation launch sets both Gazebo and Ignition resource paths at runtime. If you still see this after pulling source changes, rebuild the mounted workspace:

```bash
make bootstrap
```

If the runtime image changed, recreate the container from the published image:

```bash
make restart
```

If you changed local container scripts or the `Containerfile`, rebuild the runtime image from this checkout instead:

```bash
make restart-local
```

For a running development container, rebuild the model package:

```bash
make bootstrap
```

Then rerun:

```bash
make sim
```

## noVNC Opens But The Desktop Is Blank

Try refreshing:

```text
http://localhost:6080/vnc.html?autoconnect=1&resize=remote
```

Check container logs:

```bash
make logs
```

Restart the container:

```bash
make restart
```

## Gazebo Or RViz Is Slow

The preview uses software rendering for broad compatibility. It can be CPU-heavy.

Try:

- Close other heavy applications.
- Give the Podman machine more CPU and memory.
- Keep only one simulation launch running.
- Use `make down` before starting a fresh run.

## Detector Checkpoint Missing

Symptom:

```text
YOLOX checkpoint not found
```

Fix:

```bash
make checkpoint
make detector
```

## Object UI Shows No Tracks

Checks:

1. Confirm the simulation is still running:

```bash
make ps
```

2. Confirm the detector is running:

```bash
make detector-logs
```

3. Confirm camera frames exist:

```bash
make shell
ros2 topic echo /camera/image_raw --once --field header
```

4. Confirm detections and markers:

```bash
ros2 topic echo /detected_objects_markers --once
```

Notes:

- Tracks appear only after repeated stable detections.
- The detector uses COCO class names.
- Move the robot camera view or object placement if the target is not visible.

## Navigation Request Does Not Move The Robot

Checks:

```bash
make shell
ros2 topic echo /map --once --field info --qos-durability transient_local
ros2 action list
ros2 lifecycle get /bt_navigator
ros2 topic echo /cmd_vel_stamped --once
```

Common causes:

- The target is too close to a wall or obstacle.
- SLAM has not produced a useful map yet.
- Nav2 is still waiting for transforms.
- The object track is stale or poorly localized.

Wait for Nav2 lifecycle nodes to become active, then retry from the object search console.

## Clean Reset

Stop detector and remove the preview container:

```bash
make detector-stop
make down
```

Start again:

```bash
make start
make sim
make detector
```

For a full local rebuild:

```bash
make restart-local
```

To clear cached ROS build artifacts stored in named Podman volumes:

```bash
make clean-volumes
make start
```
