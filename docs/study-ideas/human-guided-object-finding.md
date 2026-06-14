# Human-Guided Object Finding

## Research Question

How do different forms of human guidance affect a robot's ability to find and approach an office object?

This scenario studies low-bandwidth guidance such as:

- "Look near the refreshment area."
- "Try the desk cluster."
- "The object was last seen by the meeting table."
- "That is the wrong object."

## Research Setup

- The participant provides a constrained hint about the target object's likely location or identity.
- The operator uses the OpenHRI web UI to inspect object tracks, choose a target, request navigation, and clear stale tracks.
- The robot uses YOLOX-X detections, lidar/camera localization, and remembered tracks to support the task.

## Robot Behavior

1. The robot starts in the office world with the object-search pipeline active.
2. The participant gives a hint from a predefined set.
3. The operator selects a target class or remembered object track.
4. The robot confirms object tracks from camera and lidar evidence.
5. The robot navigates to a stand-off pose near the selected target.
6. The UI exposes progress and final status.

## What This Enables

Researchers can compare:

- Region hints versus object-class hints.
- First-person operator control versus participant-guided control.
- Visible robot belief state versus minimal status display.
- Fresh detections versus remembered object tracks.
- Different UI wording for uncertainty and confidence.

## Signals To Capture

- Time from hint to first relevant detection.
- Time from hint to navigation request.
- Time from navigation request to result.
- Number of hints per trial.
- Number of track selections, retries, and clear-track actions.
- Final distance from robot base to object.
- Participant rating of guidance usefulness.
- Operator confidence in selected target.

## Preview Procedure

1. Choose a target class.
2. Place the object in a known office region.
3. Give the participant a scripted hint.
4. Let the operator use the UI to select and approach the object.
5. Capture event logs and participant/operator ratings.
