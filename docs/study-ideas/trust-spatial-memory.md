# Trust in Robot Spatial Memory

## Research Question

How do users decide whether to trust a robot's remembered object location after the object is no longer visible?

Object memory is a strong HRI topic because remembered locations can make robots feel more capable, but users still need to understand when that memory is reliable.

## Research Setup

- The robot detects and localizes an office object.
- The object becomes a confirmed remembered track.
- The object is then unchanged, occluded, moved, or removed according to the trial condition.
- The operator decides whether to navigate to the remembered location, wait for a new observation, or clear the track.

## Robot Behavior

1. The robot observes and localizes an object.
2. The UI displays the confirmed track.
3. The object leaves the camera view or changes condition.
4. The UI keeps the remembered track available for decision-making.
5. The operator chooses the next action.
6. The robot navigates to the selected remembered location when requested.

## What This Enables

Researchers can compare:

- Visible versus hidden memory age.
- Fresh detections versus remembered tracks.
- Different confidence displays.
- Different object movement and occlusion conditions.
- User trust before and after the robot's navigation result.

## Signals To Capture

- Track age at decision time.
- Last-seen timestamp.
- Current visibility state.
- Position confidence or localization support.
- User trust decision before navigation.
- Navigation result and final distance.
- Clear-track actions and memory recovery actions.
- Change in trust rating after outcome is revealed.

## Preview Procedure

1. Detect and confirm a target object.
2. Move the object into one of the scripted memory conditions.
3. Ask the operator whether they trust the remembered location.
4. Let the operator navigate, wait, or clear the track.
5. Record the decision, outcome, and trust rating.
