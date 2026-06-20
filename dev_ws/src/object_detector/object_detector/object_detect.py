import base64
import math
import threading

import cv2
import numpy as np
import rclpy
import sensor_msgs_py.point_cloud2 as point_cloud2
import tf2_ros
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, Image, LaserScan, PointCloud2
from std_msgs.msg import Header
from visualization_msgs.msg import Marker, MarkerArray

from object_detector.datatypes import NavigationStatus
from object_detector.event_log import JsonlEventLogger, event_log_config_from_params
from object_detector.localization import LocalizationConfig, ObjectLocalizer
from object_detector.model import ObjectDetectorModel
from object_detector.navigation import NavigationConfig, ObjectNavigator
from object_detector.run_manifest import (
    RunManifestWriter,
    run_manifest_config_from_params,
)
from object_detector.tracking import TrackManager, footprint_points
from object_detector.web import ObjectHuntWebServer


class ObjectDetectionNode(Node):
    def __init__(self):
        super().__init__("object_detection_node")

        self.params = self._declare_parameters()
        self.bridge = CvBridge()
        self.state_lock = threading.Lock()
        self.nav_status = NavigationStatus()
        self.event_log = JsonlEventLogger(
            event_log_config_from_params(self.params),
            logger=self.get_logger(),
        )
        if self.event_log.enabled and self.event_log.path is not None:
            self.get_logger().info(f"Object search event log: {self.event_log.path}")
        self.run_manifest = RunManifestWriter(
            run_manifest_config_from_params(self.params),
            run_id=self.event_log.run_id,
            params=self.params,
            event_log_path=self.event_log.path,
            logger=self.get_logger(),
        )
        if self.run_manifest.write() and self.run_manifest.path is not None:
            self.get_logger().info(f"Run manifest: {self.run_manifest.path}")
        self._record_trial_start()

        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)
        self.localizer = ObjectLocalizer(
            self._localization_config(), self.tf_buffer, self.get_logger()
        )
        self.tracks = TrackManager(
            self.params["cluster_radius_m"],
            self.params["confirmed_association_radius_m"],
            int(self.params["min_confirmations"]),
            self.params["track_timeout_s"],
            self.params["freeze_confirmed_tracks"],
            self.params["duplicate_track_merge_radius_m"],
        )
        self.navigator = ObjectNavigator(
            self,
            self._navigation_config(),
            self.localizer._lookup_transform,
            self.localizer.track_has_line_of_sight,
            self._set_status,
        )
        self.detector = ObjectDetectorModel(
            self.params["ckpt_path"],
            self.params["class_names_path"],
            self.params["confidence_threshold"],
            self.params["min_bbox_area_ratio"],
            self.params["model_name"],
            logger=self.get_logger(),
        )

        self._create_ros_interfaces()
        if not self.detector.load():
            self._set_status("model_unavailable", self.detector.status_message)
        self.web_server = ObjectHuntWebServer(
            self,
            self.params["web_host"],
            int(self.params["web_port"]),
            self.get_logger(),
        ).start()

    def _declare_parameters(self):
        defaults = {
            "confidence_threshold": 0.55,
            "scan_window_deg": 2.0,
            "bbox_sector_padding_deg": 4.0,
            "range_cluster_jump_m": 0.75,
            "min_lidar_points_per_object": 2,
            "min_bbox_area_ratio": 0.0002,
            "max_detection_range_m": 8.0,
            "reliable_detection_range_m": 4.0,
            "min_position_confidence": 0.05,
            "use_projected_pointcloud": True,
            "publish_projection_debug": True,
            "sofa_min_observed_radius_m": 0.35,
            "chair_max_observed_radius_m": 1.10,
            "default_object_radius_m": 0.5,
            "surface_obstacle_radius_m": 0.25,
            "obstacle_radius_padding_m": 0.1,
            "max_object_radius_m": 1.2,
            "projected_foreground_depth_margin_m": 0.35,
            "max_sensor_time_delta_s": 0.25,
            "line_of_sight_clearance_m": 0.35,
            "obstacle_point_spacing_m": 0.15,
            "obstacle_point_min_z_m": 0.05,
            "obstacle_point_max_z_m": 0.75,
            "obstacle_point_z_spacing_m": 0.15,
            "cluster_radius_m": 0.75,
            "confirmed_association_radius_m": 1.5,
            "duplicate_track_merge_radius_m": 1.5,
            "freeze_confirmed_tracks": True,
            "min_confirmations": 2,
            "track_timeout_s": 12.0,
            "approach_offset_m": 1.2,
            "min_approach_offset_m": 1.05,
            "close_stop_distance_m": 0.95,
            "dynamic_replan_min_interval_s": 2.0,
            "dynamic_replan_min_shift_m": 0.25,
            "dynamic_replan_min_confidence_gain": 0.15,
            "dynamic_replanning_enabled": False,
            "max_object_goal_distance_m": 5.0,
            "goal_candidate_angle_step_deg": 30.0,
            "max_approach_angle_offset_deg": 75.0,
            "nav_action_server_timeout_s": 5.0,
            "camera_horizontal_fov": 1.04,
            "camera_forward_axis": "z",
            "ray_projection_depth_m": 10.0,
            "lidar_bearing_offset_deg": 0.0,
            "web_host": "0.0.0.0",
            "web_port": 8080,
            "event_log_enabled": True,
            "event_log_dir": "log/events",
            "event_log_path": "",
            "event_log_run_id": "",
            "event_log_scenario": "object_search_approach",
            "run_manifest_enabled": True,
            "run_manifest_dir": "log/manifests",
            "run_manifest_path": "",
            "run_manifest_trial_id": "",
            "run_manifest_world": "office_world",
            "run_manifest_robot_start_pose": "",
            "run_manifest_target_class": "",
            "run_manifest_target_object_pose": "",
            "run_manifest_random_seed": "",
            "run_manifest_notes": "",
            "run_manifest_recipe_path": "",
            "run_manifest_run_dir": "",
            "lidar_frame": "lidar_link",
            "map_frame": "map",
            "base_frame": "base_footprint",
            "ckpt_path": "",
            "class_names_path": "",
            "model_name": "yolox-x",
        }
        return {
            name: self.declare_parameter(name, default).value
            for name, default in defaults.items()
        }

    def _localization_config(self):
        return LocalizationConfig(
            scan_window_deg=self.params["scan_window_deg"],
            bbox_sector_padding_deg=self.params["bbox_sector_padding_deg"],
            range_cluster_jump_m=self.params["range_cluster_jump_m"],
            min_lidar_points_per_object=int(
                self.params["min_lidar_points_per_object"]
            ),
            max_detection_range_m=self.params["max_detection_range_m"],
            reliable_detection_range_m=self.params["reliable_detection_range_m"],
            min_position_confidence=self.params["min_position_confidence"],
            use_projected_pointcloud=self.params["use_projected_pointcloud"],
            sofa_min_observed_radius_m=self.params["sofa_min_observed_radius_m"],
            chair_max_observed_radius_m=self.params["chair_max_observed_radius_m"],
            default_object_radius_m=self.params["default_object_radius_m"],
            obstacle_radius_padding_m=self.params["obstacle_radius_padding_m"],
            max_object_radius_m=self.params["max_object_radius_m"],
            projected_foreground_depth_margin_m=self.params[
                "projected_foreground_depth_margin_m"
            ],
            max_sensor_time_delta_s=self.params["max_sensor_time_delta_s"],
            line_of_sight_clearance_m=self.params["line_of_sight_clearance_m"],
            camera_horizontal_fov=self.params["camera_horizontal_fov"],
            camera_forward_axis=self.params["camera_forward_axis"],
            ray_projection_depth_m=self.params["ray_projection_depth_m"],
            lidar_bearing_offset_rad=math.radians(
                self.params["lidar_bearing_offset_deg"]
            ),
            lidar_frame=self.params["lidar_frame"],
            map_frame=self.params["map_frame"],
        )

    def _navigation_config(self):
        return NavigationConfig(
            approach_offset_m=self.params["approach_offset_m"],
            min_approach_offset_m=self.params["min_approach_offset_m"],
            close_stop_distance_m=self.params["close_stop_distance_m"],
            dynamic_replan_min_interval_s=self.params[
                "dynamic_replan_min_interval_s"
            ],
            dynamic_replan_min_shift_m=self.params["dynamic_replan_min_shift_m"],
            dynamic_replan_min_confidence_gain=self.params[
                "dynamic_replan_min_confidence_gain"
            ],
            dynamic_replanning_enabled=self.params["dynamic_replanning_enabled"],
            max_object_goal_distance_m=self.params["max_object_goal_distance_m"],
            goal_candidate_angle_step_deg=self.params["goal_candidate_angle_step_deg"],
            max_approach_angle_offset_deg=self.params[
                "max_approach_angle_offset_deg"
            ],
            nav_action_server_timeout_s=self.params["nav_action_server_timeout_s"],
            map_frame=self.params["map_frame"],
            base_frame=self.params["base_frame"],
        )

    def _create_ros_interfaces(self):
        self.image_sub = self.create_subscription(
            Image, "/camera/image_raw", self.image_callback, 1
        )
        self.camera_info_sub = self.create_subscription(
            CameraInfo, "/camera/camera_info", self.camera_info_callback, 10
        )
        self.scan_sub = self.create_subscription(
            LaserScan, "/lidar", self.scan_callback, 10
        )
        self.pointcloud_sub = self.create_subscription(
            PointCloud2, "/lidar/points", self.pointcloud_callback, 10
        )

        self.marker_pub = self.create_publisher(
            MarkerArray, "/detected_objects_markers", 10
        )
        self.image_pub = self.create_publisher(Image, "/camera/image_detections", 10)
        self.projection_debug_pub = self.create_publisher(
            Image, "/camera/projected_lidar_debug", 10
        )
        self.object_obstacle_pub = self.create_publisher(
            PointCloud2, "/detected_object_obstacles", 1
        )
        self.projected_points_pub = self.create_publisher(
            PointCloud2, "/detected_object_projected_points", 1
        )
        self.object_obstacle_timer = self.create_timer(
            0.5, self.publish_object_obstacles
        )

    def camera_info_callback(self, msg):
        self.localizer.set_camera_info(msg)

    def scan_callback(self, msg):
        self.localizer.set_scan(msg)

    def pointcloud_callback(self, msg):
        self.localizer.set_pointcloud(msg)

    def image_callback(self, msg):
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as exc:
            self._set_status("perception_error", f"Image conversion failed: {exc}")
            return

        if not self.detector.ready:
            self._draw_status_overlay(cv_image, self.get_nav_status()["message"])
            self._publish_detection_image(msg, cv_image)
            return

        detections = self.detector.detect(cv_image)
        if detections:
            self._handle_detections(msg, cv_image, detections)
        else:
            with self.state_lock:
                confirmed_count = self.tracks.confirmed_count(self._now_seconds())
            current_status = self.get_nav_status()
            if (
                current_status["state"]
                in ("planning", "requested", "accepted", "succeeded")
                and current_status["track_id"] is not None
            ):
                pass
            elif confirmed_count:
                self._set_status(
                    "tracking",
                    "No objects in frame; keeping "
                    f"{confirmed_count} remembered object(s).",
                )
            else:
                self._set_status("idle", "No objects currently detected.")

        self._publish_detection_image(msg, cv_image)
        self.publish_track_markers()

    def _handle_detections(self, image_msg, cv_image, detections):
        height, width = cv_image.shape[:2]
        localized_count = 0
        projected_cloud = self.localizer.project_latest_cloud_to_image(
            image_msg, width, height
        )
        debug_image = (
            cv_image.copy() if self.params["publish_projection_debug"] else None
        )
        debug_point_groups = []

        for detection in detections:
            snapshot = self._detection_snapshot(cv_image, detection)
            self._draw_detection(cv_image, detection)
            projected_indices = self.localizer.foreground_projected_indices(
                projected_cloud, detection
            )
            if debug_image is not None:
                self.localizer.draw_projection_debug(
                    debug_image, projected_cloud, projected_indices, detection
                )
            if projected_cloud is not None and len(projected_indices):
                debug_point_groups.append(projected_cloud["points"][projected_indices])

            localization = self.localizer.localize_detection(
                image_msg, projected_cloud, detection, width, height
            )
            if localization is None:
                continue

            observed_radius = self.localizer.object_radius(
                detection.class_name, localization.cluster
            )
            obstacle_radius = min(
                observed_radius, self.params["surface_obstacle_radius_m"]
            )
            position_confidence = self.localizer.position_confidence(
                detection.confidence, localization.cluster
            )
            now = self._now_seconds()
            with self.state_lock:
                previously_confirmed = {
                    track_id
                    for track_id, track in self.tracks.tracks.items()
                    if track.confirmed
                }
                track_id = self.tracks.update_track(
                    detection.class_name,
                    localization.point,
                    detection.confidence,
                    obstacle_radius,
                    position_confidence,
                    now,
                    snapshot=snapshot,
                )
                track, _ = self.tracks.get_confirmed_track(track_id, now)
                newly_confirmed = [
                    self.tracks.tracks[confirmed_id].as_dict()
                    for confirmed_id in sorted(
                        {
                            confirmed_id
                            for confirmed_id, confirmed in self.tracks.tracks.items()
                            if confirmed.confirmed
                        }
                        - previously_confirmed
                    )
                    if confirmed_id in self.tracks.tracks
                ]
            self._log_object_localized(
                detection,
                localization,
                track_id,
                observed_radius,
                obstacle_radius,
                position_confidence,
                now,
            )
            for confirmed_track in newly_confirmed:
                self._log_track_confirmed(confirmed_track, now)
            if track is not None:
                self.navigator.observe_track(track)
            localized_count += 1

        with self.state_lock:
            confirmed_count = self.tracks.confirmed_count(self._now_seconds())
        current_status = self.get_nav_status()
        if (
            current_status["state"] in ("planning", "requested", "accepted", "succeeded")
            and current_status["track_id"] is not None
        ):
            self._publish_projection_debug(
                image_msg, debug_image, projected_cloud, debug_point_groups
            )
            return

        if localized_count:
            self._set_status(
                "tracking",
                f"Localized {localized_count} detection(s); "
                f"{confirmed_count} confirmed object(s).",
            )
        else:
            self._set_status(
                "localization_unavailable",
                "Objects detected, but localization was unavailable or outside range.",
            )
        self._publish_projection_debug(
            image_msg, debug_image, projected_cloud, debug_point_groups
        )

    def _detection_snapshot(self, cv_image, detection):
        height, width = cv_image.shape[:2]
        x1 = max(0, min(width - 1, detection.x1))
        y1 = max(0, min(height - 1, detection.y1))
        x2 = max(0, min(width, detection.x2))
        y2 = max(0, min(height, detection.y2))
        if x2 <= x1 or y2 <= y1:
            return None

        crop = cv_image[y1:y2, x1:x2]
        if crop.size == 0:
            return None

        max_width = 180
        if crop.shape[1] > max_width:
            scale = max_width / float(crop.shape[1])
            crop = cv2.resize(
                crop,
                (max_width, max(1, int(round(crop.shape[0] * scale)))),
                interpolation=cv2.INTER_AREA,
            )

        ok, buffer = cv2.imencode(
            ".jpg", crop, [int(cv2.IMWRITE_JPEG_QUALITY), 78]
        )
        if not ok:
            return None
        encoded = base64.b64encode(buffer).decode("ascii")
        return f"data:image/jpeg;base64,{encoded}"

    def _draw_status_overlay(self, cv_image, message):
        cv2.putText(
            cv_image,
            message[:120],
            (24, 48),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 220),
            2,
        )

    def _draw_detection(self, cv_image, detection):
        label = f"{detection.class_name}: {detection.confidence:.2f}"
        cv2.rectangle(
            cv_image,
            (detection.x1, detection.y1),
            (detection.x2, detection.y2),
            (0, 180, 80),
            3,
        )
        cv2.putText(
            cv_image,
            label,
            (detection.x1, max(24, detection.y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 180, 80),
            2,
        )

    def _publish_detection_image(self, image_msg, cv_image):
        detection_msg = self.bridge.cv2_to_imgmsg(cv_image, encoding="bgr8")
        detection_msg.header = image_msg.header
        self.image_pub.publish(detection_msg)

    def _publish_projection_debug(
        self, image_msg, debug_image, projected_cloud, debug_point_groups
    ):
        if debug_image is not None:
            debug_msg = self.bridge.cv2_to_imgmsg(debug_image, encoding="bgr8")
            debug_msg.header = image_msg.header
            self.projection_debug_pub.publish(debug_msg)

        if projected_cloud is None:
            frame_id = self.params["lidar_frame"]
            stamp = image_msg.header.stamp
            points = []
        elif debug_point_groups:
            frame_id, stamp, points = self._map_stabilized_debug_points(
                projected_cloud, debug_point_groups
            )
        else:
            frame_id = projected_cloud["frame_id"]
            stamp = projected_cloud["stamp"]
            points = []

        header = Header()
        header.frame_id = frame_id
        header.stamp = stamp
        cloud = point_cloud2.create_cloud_xyz32(header, points)
        self.projected_points_pub.publish(cloud)

    def _map_stabilized_debug_points(self, projected_cloud, debug_point_groups):
        points = np.vstack(debug_point_groups).astype(np.float32)
        stamp = projected_cloud["stamp"]
        source_frame = projected_cloud["frame_id"]

        try:
            transform = self.localizer._lookup_transform(
                self.params["map_frame"], source_frame, stamp
            )
            points = self.localizer._transform_points(points, transform)
            frame_id = self.params["map_frame"]
        except Exception as exc:
            self.get_logger().debug(f"Projection debug map transform unavailable: {exc}")
            frame_id = source_frame

        return (
            frame_id,
            stamp,
            [(float(x), float(y), float(z)) for x, y, z in points],
        )

    def publish_track_markers(self):
        marker_array = MarkerArray()
        now_msg = self.get_clock().now().to_msg()
        delete_marker = Marker()
        delete_marker.action = Marker.DELETEALL
        marker_array.markers.append(delete_marker)

        with self.state_lock:
            tracks = self.tracks.confirmed_tracks(self._now_seconds())

        for track in tracks:
            marker_array.markers.append(self._make_sphere_marker(track, now_msg))
            marker_array.markers.append(self._make_text_marker(track, now_msg))

        self.marker_pub.publish(marker_array)

    def publish_object_obstacles(self):
        with self.state_lock:
            tracks = self.tracks.confirmed_tracks(self._now_seconds())

        points = []
        for track in tracks:
            points.extend(
                footprint_points(
                    track,
                    self.params["default_object_radius_m"],
                    self.params["obstacle_point_spacing_m"],
                    self.params["obstacle_point_min_z_m"],
                    self.params["obstacle_point_max_z_m"],
                    self.params["obstacle_point_z_spacing_m"],
                )
            )

        header = Header()
        header.frame_id = self.params["map_frame"]
        header.stamp = self.get_clock().now().to_msg()
        cloud = point_cloud2.create_cloud_xyz32(header, points)
        self.object_obstacle_pub.publish(cloud)

    def _make_sphere_marker(self, track, stamp):
        marker = Marker()
        marker.header.frame_id = self.params["map_frame"]
        marker.header.stamp = stamp
        marker.ns = "detected_object_surfaces"
        marker.id = track["track_id"] * 2
        marker.type = Marker.SPHERE
        marker.action = Marker.ADD
        marker.pose.position.x = track["x"]
        marker.pose.position.y = track["y"]
        marker.pose.position.z = 0.15
        diameter = 2.0 * track.get(
            "obstacle_radius", self.params["surface_obstacle_radius_m"]
        )
        marker.scale.x = diameter
        marker.scale.y = diameter
        marker.scale.z = 0.25
        marker.color.a = 0.9
        marker.color.r = 0.05
        marker.color.g = 0.65
        marker.color.b = 0.30
        return marker

    def _make_text_marker(self, track, stamp):
        marker = Marker()
        marker.header.frame_id = self.params["map_frame"]
        marker.header.stamp = stamp
        marker.ns = "object_track_labels"
        marker.id = track["track_id"] * 2 + 1
        marker.type = Marker.TEXT_VIEW_FACING
        marker.action = Marker.ADD
        marker.text = f"{track['class_name']} #{track['track_id']}"
        marker.pose.position.x = track["x"]
        marker.pose.position.y = track["y"]
        marker.pose.position.z = 0.45
        marker.scale.z = 0.22
        marker.color.a = 1.0
        marker.color.r = 1.0
        marker.color.g = 1.0
        marker.color.b = 1.0
        return marker

    def get_track_classes(self):
        with self.state_lock:
            return self.tracks.classes(self._now_seconds())

    def get_locations(self, class_name):
        with self.state_lock:
            return self.tracks.locations(class_name, self._now_seconds())

    def get_nav_status(self):
        with self.state_lock:
            return self.nav_status.as_dict()

    def clear_tracks(self):
        now = self._now_seconds()
        with self.state_lock:
            track_count = len(self.tracks.tracks)
            confirmed_count = sum(
                1 for track in self.tracks.tracks.values() if track.confirmed
            )
            self.tracks.clear()
            self.nav_status = NavigationStatus(
                state="idle", message="Tracks cleared.", track_id=None
            )
        self.navigator.clear_plans()
        self._log_event(
            "tracks_cleared",
            {
                "track_count": track_count,
                "confirmed_count": confirmed_count,
                "source": "api",
            },
            t=now,
        )

        marker = Marker()
        marker.action = Marker.DELETEALL
        marker_array = MarkerArray()
        marker_array.markers.append(marker)
        self.marker_pub.publish(marker_array)

    def navigate_to_track(self, track_id, source="api"):
        now = self._now_seconds()
        with self.state_lock:
            track, error = self.tracks.get_confirmed_track(track_id, now)
        if error:
            self._set_status("error", error, track_id)
            return False, error

        self._log_event(
            "navigation_requested",
            {
                "track_id": track["track_id"],
                "class": track["class_name"],
                "x": track["x"],
                "y": track["y"],
                "source": source,
            },
            t=now,
        )
        return self.navigator.navigate_to_track(track)

    def _set_status(self, state, message, track_id=None):
        with self.state_lock:
            previous_status = self.nav_status.as_dict()
            status = NavigationStatus(state=state, message=message, track_id=track_id)
            self.nav_status = status
        if (
            state in ("succeeded", "error")
            and track_id is not None
            and previous_status != status.as_dict()
        ):
            self._log_event(
                "navigation_result",
                {
                    "track_id": track_id,
                    "status": state,
                    "message": message,
                },
            )

    def _log_object_localized(
        self,
        detection,
        localization,
        track_id,
        observed_radius,
        obstacle_radius,
        position_confidence,
        now,
    ):
        self._log_event(
            "object_localized",
            {
                "track_id": track_id,
                "class": detection.class_name,
                "x": localization.point.point.x,
                "y": localization.point.point.y,
                "confidence": detection.confidence,
                "position_confidence": position_confidence,
                "source": localization.cluster.source,
                "observed_radius_m": observed_radius,
                "obstacle_radius_m": obstacle_radius,
            },
            t=now,
        )

    def _log_track_confirmed(self, track, now):
        self._log_event(
            "track_confirmed",
            {
                "track_id": track["track_id"],
                "class": track["class_name"],
                "x": track["x"],
                "y": track["y"],
                "detections": track["detections"],
                "position_confidence": track["position_confidence"],
            },
            t=now,
        )

    def _record_trial_start(self):
        self.event_log.record(
            "trial_start",
            self.run_manifest.trial_start_fields(),
            t=0.0,
        )

    def _log_event(self, event, fields=None, t=None):
        if t is None:
            t = self._now_seconds()
        return self.event_log.record(event, fields or {}, t=t)

    def _now_seconds(self):
        return self.get_clock().now().nanoseconds / 1e9

    def destroy_node(self):
        if self.web_server is not None:
            self.web_server.shutdown()
        self.event_log.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = ObjectDetectionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
