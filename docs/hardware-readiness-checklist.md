# Hardware Readiness Checklist

Use this checklist before putting a physical `office_bot` build in a shared workspace, demo, evaluation, or hardware trial. The current public branch documents an early hardware prototype, but the main workflow remains simulation-first while full robot-stack integration is completed.

## Status Terms

- `pending`: no checked-in proof yet.
- `planned`: the check is defined, but no result has been collected.
- `partial`: some proof exists, but pass criteria are incomplete or not repeatable.
- `ready`: dated proof meets the stated pass criteria and can be shared.

## Checklist

| Subsystem | Status | Current evidence | Remaining checks | Minimum readiness criteria |
| --- | --- | --- | --- | --- |
| BOM | partial | Installed major parts are recorded in [hardware-bom.md](hardware-bom.md), including battery, Raspberry Pi 5, Axelera card, motor driver, lidar, camera, mecanum wheels, physical emergency stop, and frame/chassis. | Fill any exact model gaps, alternates, supplier links, replacement rules, and hardware-branch sync details. | `docs/hardware-bom.md` is complete enough for another builder to reorder, repair, and compare builds. |
| Compute and acceleration | partial | Raspberry Pi 5 plus Axelera hardware is installed, and the Axelera card is working. | Complete and document full project-stack integration on the Raspberry Pi hardware. | The robot boots the documented stack and exposes expected device permissions, runtime, and acceleration behavior. |
| Chassis | partial | The early hardware prototype is assembled as an open mobile platform. | Record structural integrity, payload, wheel geometry, sensor mounts, and fastener access. | No loose mounts, documented source or assembly notes, and repeatable assembly. |
| Motor control | partial | Mecanum wheels and motor controller are wired and can move under command; low-speed motion has been tested with a raw motor-controller Python script. | Document command interface, velocity limits, direction, acceleration, stop behavior, calibration, and ROS control path. | Controlled low-speed motion through the documented interface with repeatable calibration. |
| Odometry | pending | No checked-in straight-line, rotation, or square-path drift result yet. | Record drift bounds on the intended operating surface. | Repeatable drift bounds recorded for the operating surface. |
| Lidar | partial | Lidar is mounted and producing usable ROS data. | Record driver setup, frame, mount height, scan quality, obstacle visibility, and RViz evidence. | Stable data in RViz and documented frame transform. |
| Camera | partial | Camera is mounted and producing usable ROS data. | Record driver setup, frame, resolution, calibration, object visibility, and camera-info evidence. | Stable `/camera/image_raw` and camera info in the expected frame. |
| Battery | partial | Onboard battery power works, with observed runtime of more than 10 hours. | Record voltage stability, charging process, thermal behavior, low-power shutdown, fuse strategy, and mounting. | Runtime supports planned operating duration and safe shutdown. |
| Emergency stop | partial | A physical emergency stop is installed on the left side of the robot. | Record activation behavior, reachability, stop distance or stop timing, and recovery steps. | Documented stop method tested before shared use. |
| Object detection | planned | Object detection is currently simulation-only. | Run and document object detection on the physical robot after stack integration. | Physical camera detections produce expected object tracks and logs. |
| SLAM and navigation | planned | SLAM and navigation are currently simulation-only. | Run and document mapping, localization, and navigation behavior on hardware. | Hardware navigation is repeatable at documented speeds and operating conditions. |
| Operator area | pending | No checked-in workspace safety result yet. | Record space, barriers, speed limits, cable routing, floor condition, and supervision requirements. | Workspace setup prevents unsafe contact and tripping hazards. |
| Run outputs | partial | Public hardware photo and status notes are checked in. | Add hardware run logs, events, manifests, photos/video, and notes when hardware trials begin. | Each hardware run has enough output to explain failures. |

## Physical Build Status

The early hardware prototype is assembled with onboard battery power, Raspberry
Pi 5 plus Axelera compute, motor control, lidar, camera, mecanum drive, and a
physical emergency stop. Low-speed motor control has been tested directly.
Object detection, SLAM, navigation, and full robot-stack integration on the
Raspberry Pi hardware are still in progress or simulation-first while checklist
rows remain `pending`, `planned`, or `partial`.
