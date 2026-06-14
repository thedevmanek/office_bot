# Transparent Recovery

## Research Question

What robot status information helps a human operator understand the current situation and choose the next action?

This scenario treats transparency as operational clarity: the robot exposes what it is trying to do, what it currently believes, and which recovery options are available.

## Research Setup

- The operator watches the OpenHRI object UI, RViz markers, and robot behavior.
- The UI exposes object tracks, navigation state, status messages, and recovery controls.
- The operator chooses actions such as retrying navigation, selecting a different track, waiting for a fresh observation, or clearing stale memory.

## Robot Behavior

1. The robot detects and localizes a target object.
2. The status API reports the active state.
3. The UI displays remembered tracks and status messages.
4. The operator chooses a recovery or continuation action when the task state changes.
5. The event log captures status transitions and operator actions.

## What This Enables

Researchers can study:

- Whether visible state improves operator confidence.
- How quickly operators choose useful recovery actions.
- Which status wording produces the clearest mental model.
- How remembered objects affect recovery decisions.
- How UI design changes intervention timing.

## Signals To Capture

- Time from state change to displayed status update.
- Number of status changes per trial.
- Operator action selected.
- Time from status update to operator action.
- Number of retries, alternate selections, and clear-track actions.
- Operator rating of status clarity.
- Operator confidence before and after recovery.

## Preview Procedure

1. Start the object-search task.
2. Present the operator with a clear task goal.
3. Introduce controlled task variations such as occlusion, moved objects, or unreachable approach poses.
4. Let the operator choose the next action from the UI.
5. Record status transitions, actions, outcome labels, and confidence ratings.
