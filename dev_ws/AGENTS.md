# AGENTS.md

Guidance for coding agents working in this repository.

## Project Summary

This workspace is a ROS 2 Humble simulation stack for an office robot. It contains:

- `office_bot_model` (ament_python): robot description assets (xacro/URDF), launch files, Gazebo world assets, controller/nav configs.
- `office_bot_controller_handlers` (ament_cmake): C++ helper nodes for controller-facing behavior (`velstamper`).
- `object_detector` (ament_python): ROS node for camera-based object detection and marker publishing.

## Repository Layout

- `src/office_bot_model/launch/launch_sdf_into_gazebo.launch.py`: primary simulation launch entrypoint.
- `src/office_bot_model/models/officebot_xacro/`: robot model source of truth (`main.xacro` + components).
- `src/office_bot_model/models/officebot/robot.urdf`: generated/checked-in URDF artifact.
- `src/office_bot_model/models/worlds/office_world/`: Gazebo world + meshes/materials/models.
- `src/office_bot_model/controllers/*.yaml`: ros2_control, EKF, SLAM, Nav2 parameters.
- `src/office_bot_controller_handlers/src/velstamper.cpp`: `/cmd_vel` to `/cmd_vel_stamped` bridge node.
- `src/object_detector/object_detector/object_detect.py`: object detection runtime node.
- `launch_sim.sh`: convenience script for local simulation launch.

## Environment Assumptions

- ROS 2 Humble is installed at `/opt/ros/humble`.
- Gazebo Sim / Ignition tooling is available (`ign gazebo`).
- Commands are typically run from workspace root (`dev_ws`).

Load environment before build/run:

```bash
source /opt/ros/humble/setup.zsh
source install/local_setup.zsh
```

## Build, Test, and Run

Build all packages:

```bash
colcon build --symlink-install
```

Build a single package while iterating:

```bash
colcon build --symlink-install --packages-select office_bot_model
colcon build --symlink-install --packages-select office_bot_controller_handlers
colcon build --symlink-install --packages-select object_detector
```

Run simulation:

```bash
./launch_sim.sh
```

Equivalent direct launch:

```bash
ros2 launch office_bot_model launch_sdf_into_gazebo.launch.py
```

Run tests:

```bash
colcon test --packages-select office_bot_model object_detector office_bot_controller_handlers
colcon test-result --verbose
```

## Package-Specific Notes

### office_bot_model

- Prefer editing xacro files under `models/officebot_xacro/`; treat `models/officebot/robot.urdf` as a generated artifact.
- `launch_sdf_into_gazebo.launch.py` expands xacro twice:
  - `package://...` mesh URIs for ROS tools.
  - `file://...` mesh URIs for Gazebo spawn.
- Keep `use_sim_time` consistent across newly added nodes in simulation launch.
- Avoid moving world/model asset directories unless all path references are updated.

### office_bot_controller_handlers

- C++ standard is set to C++14 in `CMakeLists.txt`.
- Preserve topic contract:
  - Subscribes: `/cmd_vel` (`geometry_msgs/msg/Twist`)
  - Publishes: `/cmd_vel_stamped` (`geometry_msgs/msg/TwistStamped`)
- Maintain parameter compatibility (`publish_rate`, `input_timeout`) used by launch.

### object_detector

- Current node expects a YOLOX checkpoint at:
  - `/home/thedevmanek/office_bot/dev_ws/src/object_detector/resource/yolox_m.pth`
- `coco.names` is versioned; model weights are not currently present in repo.
- If changing detector paths, prefer package-relative resolution over hard-coded absolute paths.

## Agent Working Rules

- Keep edits minimal and scoped to the user request.
- Do not delete or rename large mesh/world directories unless explicitly requested.
- Validate with targeted builds/tests for touched packages before finalizing.
- For launch or topic wiring changes, include a short runtime verification checklist in your final report.
- Never use destructive git operations (`reset --hard`, mass checkout) unless explicitly requested.

## Quick Verification Checklist

After making simulation-related changes, verify:

1. `colcon build --symlink-install --packages-select <touched_packages>` succeeds.
2. `ros2 launch office_bot_model launch_sdf_into_gazebo.launch.py` starts without missing resource errors.
3. Controllers spawn (`joint_state_broadcaster`, `mecanum_drive_controller`).
4. Core topics exist (`/clock`, `/lidar`, `/camera/image_raw`, `/cmd_vel_stamped`).

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:

- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:

- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
