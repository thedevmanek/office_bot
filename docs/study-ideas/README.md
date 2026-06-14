# Research Scenarios

OpenHRI Office starts with one concrete task, Object Search and Approach, and expands naturally into HRI scenarios around guidance, transparency, trust, and approach behavior.

The scenarios below are designed to help researchers see where OpenHRI can fit into their work.

## Scenario Matrix

| Scenario | Research Focus | What OpenHRI Provides |
| --- | --- | --- |
| [Human-Guided Object Finding](human-guided-object-finding.md) | How human hints and operator choices shape object-finding performance. | Object detection, remembered tracks, target selection, navigation requests, and visible robot state. |
| [Transparent Recovery](transparent-recovery.md) | How robot status and recovery controls affect operator confidence and decision-making. | Status API, UI messages, object memory, clear-track controls, and navigation result state. |
| [Trust in Robot Spatial Memory](trust-spatial-memory.md) | How users judge whether a remembered object location is still reliable. | Confirmed object tracks, remembered locations, track ids, visibility state, and target navigation. |
| [Proxemic Approach Comfort](proxemic-approach-comfort.md) | How approach distance and orientation affect perceived comfort and usefulness. | Configurable stand-off behavior, navigation goals around objects, and repeatable office layouts. |

## Why These Scenarios Matter

Each scenario uses the same research substrate:

- A shared office world.
- A reference mobile robot.
- ROS 2 Humble launch wiring.
- Nav2, SLAM, localization, and controller integration.
- YOLOX-X object detection.
- Lidar/camera object localization.
- Object memory and track selection.
- A browser-accessible operator UI.
- Lightweight event logging for repeatable comparison.

That shared substrate is the value of OpenHRI: researchers can focus on the interaction question instead of rebuilding the robot stack from scratch.

## Research Expansion Path

1. Object Search and Approach.
2. Human-Guided Object Finding.
3. Transparent Recovery.
4. Trust in Robot Spatial Memory.
5. Proxemic Approach Comfort.

Together, these scenarios show how OpenHRI Office can grow from one concrete task into a reusable HRI research platform.
