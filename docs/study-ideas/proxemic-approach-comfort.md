# Proxemic Approach Comfort

## Research Question

What robot approach distances, orientations, and stopping behaviors feel comfortable and useful when a service robot approaches office objects near people?

This scenario uses object approach behavior as a practical entry point into proxemics, comfort, and perceived safety.

## Research Setup

- A participant observes the robot approach an object near a desk, table, or refreshment area.
- The operator selects the target object and approach condition.
- The trial varies stand-off distance, approach angle, or object placement.
- The participant rates comfort, usefulness, and perceived safety.

## Robot Behavior

1. The robot detects and localizes an object.
2. The operator requests navigation to that object.
3. The robot selects an approach pose using configured stand-off parameters.
4. The robot navigates and stops near the object.
5. The participant rates the approach.

## What This Enables

Researchers can compare:

- Close versus far stand-off distances.
- Direct versus angled approaches.
- Object locations near desks, tables, and shared spaces.
- UI previews of selected approach pose.
- Participant comfort ratings across repeated approach conditions.

## Signals To Capture

- Configured approach offset.
- Selected approach pose.
- Final robot-object distance.
- Final robot-proxy distance when a human proxy zone is used.
- Navigation result and replanning events.
- Participant comfort rating.
- Participant perceived usefulness rating.
- Open-ended notes on approach quality.

## Preview Procedure

1. Choose an object placement and approach condition.
2. Start the object detection and localization pipeline.
3. Select the target object from the UI.
4. Let the robot navigate to the configured stand-off pose.
5. Collect comfort and usefulness ratings.
