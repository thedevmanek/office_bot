# Component Swap Guide

`office_bot` is meant to be replaceable at the component level within OpenHRI. A swap is acceptable when the interface stays documented and the rest of the workflow still runs.

## Swap Rules

1. Name the component being replaced and the reason for the swap.
2. Record the old part, new part, expected cost, supplier, and mechanical/electrical constraints.
3. Update the interface contract: ROS topic, frame name, message type, voltage, mount pattern, calibration, or launch parameter.
4. Add a test that proves the swap still supports the expected workflow.
5. Update [hardware-bom.md](hardware-bom.md) and any affected docs.

## Stable Interfaces

| Area | Stable contract |
| --- | --- |
| Camera | Publishes `/camera/image_raw` and camera info with documented frame naming. |
| Lidar | Publishes scan or point-cloud data used by localization and obstacle handling. |
| Mobile base | Accepts velocity commands and reports odometry with a stable base frame. |
| Object detector | Emits localized object tracks and markers consumed by the web console. |
| Navigation | Accepts object-approach goals and reports navigation results. |
| Run tooling | Writes recipe, manifest, events, summary, and optional evaluation output under `runs/<trial_id>/`. |

## Common Swaps

- Camera model or resolution.
- Lidar model or mount height.
- Wheel diameter or wheelbase.
- Motor controller.
- Compute board.
- Battery capacity.
- Object detector model.
- Operator-console wording or layout.

## Acceptance Notes

A swap is not complete because the robot moves once. It is complete when another operator can reproduce the setup from docs, run the baseline recipe, and understand what changed if the output differs.
