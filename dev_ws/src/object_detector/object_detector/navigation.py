import math
from dataclasses import dataclass


@dataclass
class NavigationConfig:
    approach_offset_m: float
    min_approach_offset_m: float
    close_stop_distance_m: float
    dynamic_replan_min_interval_s: float
    dynamic_replan_min_shift_m: float
    dynamic_replan_min_confidence_gain: float
    dynamic_replanning_enabled: bool
    max_object_goal_distance_m: float
    goal_candidate_angle_step_deg: float
    max_approach_angle_offset_deg: float
    nav_action_server_timeout_s: float
    map_frame: str
    base_frame: str


class ObjectNavigator:
    def __init__(self, node, config, tf_lookup, visibility_check, set_status):
        from geometry_msgs.msg import Twist
        from nav2_msgs.action import ComputePathToPose, NavigateToPose
        from rclpy.action import ActionClient

        self.node = node
        self.config = config
        self.tf_lookup = tf_lookup
        self.visibility_check = visibility_check
        self.set_status = set_status
        self.ComputePathToPose = ComputePathToPose
        self.NavigateToPose = NavigateToPose
        self.cmd_vel_pub = node.create_publisher(Twist, "/cmd_vel", 10)
        self.nav_client = ActionClient(node, NavigateToPose, "/navigate_to_pose")
        self.path_client = ActionClient(node, ComputePathToPose, "/compute_path_to_pose")
        self.active_goal_handle = None
        self.active_track_id = None
        self.active_track = None
        self.active_stand_off_m = None
        self.last_replan_time = 0.0
        self.nav_generation = 0
        self.pending_plans = {}

    def navigate_to_track(self, track):
        track_id = track["track_id"]
        distance = self.distance_to_surface(track)
        if distance is not None and distance <= self.config.close_stop_distance_m:
            self._stop_for_close_surface(track, distance)
            return True, "Already close enough to the observed object surface."

        timeout = self.config.nav_action_server_timeout_s
        if not self.nav_client.wait_for_server(timeout_sec=timeout):
            message = (
                "Nav2 navigate_to_pose action server is not available yet. "
                "Wait until Nav2 has finished starting, then try again."
            )
            self._publish_stop()
            self.set_status("error", message, track_id)
            return False, message

        if not self.path_client.wait_for_server(timeout_sec=timeout):
            message = (
                "Nav2 compute_path_to_pose action server is not available yet. "
                "Wait until the Nav2 planner has finished starting, then try again."
            )
            self._publish_stop()
            self.set_status("error", message, track_id)
            return False, message

        candidates = self.build_goal_candidates(track)
        if not candidates:
            message = "Could not compute approach candidates near the object surface."
            self._publish_stop()
            self.set_status("error", message, track_id)
            return False, message

        self.pending_plans[track_id] = {
            "track": track,
            "candidates": candidates,
            "index": 0,
        }
        self.set_status(
            "planning",
            f"Checking reachable approach poses near {track['class_name']} #{track_id}.",
            track_id,
        )
        self._try_next_goal_candidate(track_id)
        message = (
            f"Planning reachable surface-approach poses for "
            f"{track['class_name']} #{track_id}."
        )
        return True, message

    def observe_track(self, track):
        if self.active_track_id != track["track_id"]:
            return

        distance = self.distance_to_surface(track)
        if distance is None:
            return

        if distance <= self.config.close_stop_distance_m:
            self._stop_for_close_surface(track, distance)
            return

        if self._should_replan(track, distance):
            self.nav_generation += 1
            if self.active_goal_handle is not None:
                self.active_goal_handle.cancel_goal_async()
            self.active_goal_handle = None
            self.active_track_id = None
            self.active_track = None
            self.active_stand_off_m = None
            self.set_status(
                "planning",
                f"Updating approach to {track['class_name']} "
                f"#{track['track_id']} as range confidence improves.",
                track["track_id"],
            )
            self.navigate_to_track(dict(track))

    def clear_plans(self):
        self.nav_generation += 1
        if self.active_goal_handle is not None:
            self.active_goal_handle.cancel_goal_async()
        self.pending_plans.clear()
        self.active_goal_handle = None
        self.active_track_id = None
        self.active_track = None
        self.active_stand_off_m = None
        self._publish_stop()

    def build_goal_candidates(self, track):
        robot_xy = self.robot_xy()
        if robot_xy is None:
            return []

        robot_x, robot_y = robot_xy
        dx = track["x"] - robot_x
        dy = track["y"] - robot_y
        distance = math.hypot(dx, dy)
        if distance < 1e-6:
            dx = 1.0
            dy = 0.0

        base_angle = math.atan2(dy, dx)
        stand_off = adaptive_stand_off(
            distance_to_surface=distance,
            confidence=track.get("position_confidence", 0.0),
            far_stand_off_m=self.config.approach_offset_m,
            min_stand_off_m=self.config.min_approach_offset_m,
            close_stop_distance_m=self.config.close_stop_distance_m,
            max_distance_m=self.config.max_object_goal_distance_m,
        )
        self.active_stand_off_m = stand_off
        candidates = []
        for radius in candidate_radii(
            stand_off, self.config.max_object_goal_distance_m
        ):
            for offset in candidate_angle_offsets(
                self.config.goal_candidate_angle_step_deg,
                self.config.max_approach_angle_offset_deg,
            ):
                angle = normalize_angle(base_angle + offset)
                goal_x, goal_y, yaw = surface_approach_pose(
                    track["x"], track["y"], angle, radius
                )
                candidates.append(self._make_pose(goal_x, goal_y, yaw))

        return candidates

    def distance_to_surface(self, track):
        robot_xy = self.robot_xy()
        if robot_xy is None:
            return None
        robot_x, robot_y = robot_xy
        return math.hypot(track["x"] - robot_x, track["y"] - robot_y)

    def robot_xy(self):
        import rclpy

        try:
            transform = self.tf_lookup(
                self.config.map_frame, self.config.base_frame, rclpy.time.Time()
            )
        except Exception as exc:
            self.node.get_logger().debug(f"Base pose transform unavailable: {exc}")
            return None

        return transform.transform.translation.x, transform.transform.translation.y

    def _make_pose(self, x, y, yaw):
        from geometry_msgs.msg import PoseStamped

        pose = PoseStamped()
        pose.header.frame_id = self.config.map_frame
        pose.header.stamp = self.node.get_clock().now().to_msg()
        pose.pose.position.x = x
        pose.pose.position.y = y
        pose.pose.position.z = 0.0
        pose.pose.orientation.z = math.sin(yaw / 2.0)
        pose.pose.orientation.w = math.cos(yaw / 2.0)
        return pose

    def _try_next_goal_candidate(self, track_id):
        plan = self.pending_plans.get(track_id)
        if plan is None:
            return

        if plan["index"] >= len(plan["candidates"]):
            self.pending_plans.pop(track_id, None)
            self._abort_navigation(
                track_id,
                "No reachable approach pose found within "
                f"{self.config.max_object_goal_distance_m:.1f} m of the observed surface.",
            )
            return

        goal_pose = plan["candidates"][plan["index"]]
        plan["index"] += 1
        generation = self.nav_generation

        goal_msg = self.ComputePathToPose.Goal()
        goal_msg.goal = goal_pose
        goal_msg.use_start = False
        future = self.path_client.send_goal_async(goal_msg)
        future.add_done_callback(
            lambda result: self._path_goal_response(
                result, track_id, goal_pose, generation
            )
        )

    def _path_goal_response(self, future, track_id, goal_pose, generation):
        if generation != self.nav_generation:
            return

        try:
            goal_handle = future.result()
        except Exception as exc:
            self.node.get_logger().debug(f"Path goal failed to send: {exc}")
            self._try_next_goal_candidate(track_id)
            return

        if not goal_handle.accepted:
            self._try_next_goal_candidate(track_id)
            return

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(
            lambda result: self._path_result(result, track_id, goal_pose, generation)
        )

    def _path_result(self, future, track_id, goal_pose, generation):
        if generation != self.nav_generation:
            return

        try:
            wrapped_result = future.result()
            result = wrapped_result.result
        except Exception as exc:
            self.node.get_logger().debug(f"Path planning failed: {exc}")
            self._try_next_goal_candidate(track_id)
            return

        if wrapped_result.status != 4:
            self._try_next_goal_candidate(track_id)
            return

        if not result.path.poses:
            self._try_next_goal_candidate(track_id)
            return

        plan = self.pending_plans.pop(track_id, None)
        if plan is None:
            return

        plan["track"]["remaining_candidates"] = plan["candidates"][plan["index"]:]
        self._send_navigation_goal(goal_pose, plan["track"])

    def _send_navigation_goal(self, goal_pose, track):
        if self.active_goal_handle is not None:
            self.active_goal_handle.cancel_goal_async()

        self.nav_generation += 1
        generation = self.nav_generation
        goal_msg = self.NavigateToPose.Goal()
        goal_msg.pose = goal_pose
        future = self.nav_client.send_goal_async(goal_msg)
        future.add_done_callback(
            lambda result: self._nav_goal_response(result, track, generation)
        )
        self.set_status(
            "requested",
            f"Reachable approach pose selected for {track['class_name']} #{track['track_id']}.",
            track["track_id"],
        )

    def _nav_goal_response(self, future, track, generation):
        if generation != self.nav_generation:
            return

        try:
            goal_handle = future.result()
        except Exception as exc:
            self._abort_navigation(
                track["track_id"], f"Navigation goal failed to send: {exc}"
            )
            return

        if not goal_handle.accepted:
            self._abort_navigation(
                track["track_id"],
                f"Navigation goal rejected for {track['class_name']} #{track['track_id']}.",
            )
            return

        self.active_goal_handle = goal_handle
        self.active_track_id = track["track_id"]
        self.active_track = dict(track)
        self.last_replan_time = self._now_seconds()
        self.set_status(
            "accepted",
            f"Navigation goal accepted for {track['class_name']} #{track['track_id']}.",
            track["track_id"],
        )
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(
            lambda result: self._nav_result(result, track, generation)
        )

    def _nav_result(self, future, track, generation):
        if generation != self.nav_generation:
            return

        track_id = track["track_id"]
        try:
            result = future.result()
            status_code = result.status
        except Exception as exc:
            self._abort_navigation(track_id, f"Navigation failed: {exc}")
            return

        self.active_goal_handle = None
        self.active_track_id = None
        self.active_track = None
        self.active_stand_off_m = None
        if status_code == 4:
            if self._track_is_visible(track):
                self._publish_stop()
                self.set_status("succeeded", "Navigation succeeded.", track_id)
            else:
                self._abort_navigation(
                    track_id,
                    "Reached a Nav2 approach pose, but the object surface is "
                    "not visible from there. It is likely blocked by an obstacle or wall.",
                )
        else:
            self._abort_navigation(
                track_id, f"Navigation finished with status {status_code}."
            )

    def _retry_remaining_goal(self, track, reason):
        track_id = track["track_id"]
        self.active_goal_handle = None
        remaining = track.pop("remaining_candidates", [])
        if not remaining:
            self.set_status("error", reason, track_id)
            return

        self.pending_plans[track_id] = {
            "track": track,
            "candidates": remaining,
            "index": 0,
        }
        self.set_status("planning", f"{reason} Trying another reachable goal.", track_id)
        self._try_next_goal_candidate(track_id)

    def _should_replan(self, track, distance_to_surface):
        if not self.config.dynamic_replanning_enabled:
            return False

        if self.active_track is None:
            return False

        now = self._now_seconds()
        if now - self.last_replan_time < self.config.dynamic_replan_min_interval_s:
            return False

        surface_shift = math.hypot(
            track["x"] - self.active_track["x"],
            track["y"] - self.active_track["y"],
        )
        confidence_gain = (
            track.get("position_confidence", 0.0)
            - self.active_track.get("position_confidence", 0.0)
        )
        desired_stand_off = adaptive_stand_off(
            distance_to_surface=distance_to_surface,
            confidence=track.get("position_confidence", 0.0),
            far_stand_off_m=self.config.approach_offset_m,
            min_stand_off_m=self.config.min_approach_offset_m,
            close_stop_distance_m=self.config.close_stop_distance_m,
            max_distance_m=self.config.max_object_goal_distance_m,
        )
        stand_off_change = abs(desired_stand_off - (self.active_stand_off_m or 0.0))
        return (
            surface_shift >= self.config.dynamic_replan_min_shift_m
            or confidence_gain >= self.config.dynamic_replan_min_confidence_gain
            or stand_off_change >= self.config.dynamic_replan_min_shift_m
        )

    def _stop_for_close_surface(self, track, distance):
        self.nav_generation += 1
        if self.active_goal_handle is not None:
            self.active_goal_handle.cancel_goal_async()
        self.active_goal_handle = None
        self.active_track_id = None
        self.active_track = None
        self.active_stand_off_m = None
        self.pending_plans.pop(track["track_id"], None)
        if not self._track_is_visible(track):
            self._publish_stop()
            self.set_status(
                "error",
                f"{track['class_name']} #{track['track_id']} is close in the map, "
                "but lidar cannot see the object surface. It is likely behind an obstacle or wall.",
                track["track_id"],
            )
            return

        self._publish_stop()
        self.set_status(
            "succeeded",
            f"Close enough to {track['class_name']} #{track['track_id']} "
            f"({distance:.2f} m). Stopping.",
            track["track_id"],
        )

    def _now_seconds(self):
        return self.node.get_clock().now().nanoseconds / 1e9

    def _abort_navigation(self, track_id, message):
        self.nav_generation += 1
        if self.active_goal_handle is not None:
            self.active_goal_handle.cancel_goal_async()
        self.active_goal_handle = None
        self.active_track_id = None
        self.active_track = None
        self.active_stand_off_m = None
        self.pending_plans.pop(track_id, None)
        self._publish_stop()
        self.set_status("error", message, track_id)

    def _publish_stop(self):
        from geometry_msgs.msg import Twist

        self.cmd_vel_pub.publish(Twist())

    def _track_is_visible(self, track):
        try:
            return bool(self.visibility_check(track))
        except Exception as exc:
            self.node.get_logger().debug(f"Object visibility check failed: {exc}")
            return False


def normalize_angle(angle):
    return math.atan2(math.sin(angle), math.cos(angle))


def candidate_radii(approach_offset_m, max_object_goal_distance_m):
    radii = [approach_offset_m]
    current = max(1.0, approach_offset_m + 0.75)
    while current < max_object_goal_distance_m:
        radii.append(current)
        current += 0.75
    radii.append(max_object_goal_distance_m)

    unique = []
    for radius in radii:
        clamped = max(0.1, min(max_object_goal_distance_m, radius))
        if not unique or abs(unique[-1] - clamped) > 1e-6:
            unique.append(clamped)
    return unique


def candidate_angle_offsets(goal_candidate_angle_step_deg, max_abs_angle_deg=180.0):
    step = math.radians(max(5.0, goal_candidate_angle_step_deg))
    max_abs_angle = math.radians(max(0.0, min(180.0, max_abs_angle_deg)))
    offsets = [0.0]
    rings = int(math.ceil(max_abs_angle / step))
    for i in range(1, rings + 1):
        offset = min(max_abs_angle, i * step)
        offsets.extend([offset, -offset])
    return offsets


def surface_approach_pose(surface_x, surface_y, approach_angle, stand_off_m):
    goal_x = surface_x - math.cos(approach_angle) * stand_off_m
    goal_y = surface_y - math.sin(approach_angle) * stand_off_m
    yaw = math.atan2(surface_y - goal_y, surface_x - goal_x)
    return goal_x, goal_y, yaw


def adaptive_stand_off(
    distance_to_surface,
    confidence,
    far_stand_off_m,
    min_stand_off_m,
    close_stop_distance_m,
    max_distance_m,
):
    confidence = max(0.0, min(1.0, confidence))
    min_stand_off_m = max(close_stop_distance_m, min_stand_off_m)
    far_stand_off_m = max(min_stand_off_m, far_stand_off_m)
    if max_distance_m <= close_stop_distance_m:
        distance_ratio = 0.0
    else:
        distance_ratio = (distance_to_surface - close_stop_distance_m) / (
            max_distance_m - close_stop_distance_m
        )
    distance_ratio = max(0.0, min(1.0, distance_ratio))
    caution = max(distance_ratio, 1.0 - confidence)
    return min_stand_off_m + (far_stand_off_m - min_stand_off_m) * caution
