import math
from dataclasses import dataclass

import cv2
import numpy as np

from object_detector.datatypes import ClusterSummary, LocalizedDetection


@dataclass
class LocalizationConfig:
    scan_window_deg: float
    bbox_sector_padding_deg: float
    range_cluster_jump_m: float
    min_lidar_points_per_object: int
    max_detection_range_m: float
    reliable_detection_range_m: float
    min_position_confidence: float
    use_projected_pointcloud: bool
    sofa_min_observed_radius_m: float
    chair_max_observed_radius_m: float
    default_object_radius_m: float
    obstacle_radius_padding_m: float
    max_object_radius_m: float
    projected_foreground_depth_margin_m: float
    max_sensor_time_delta_s: float
    line_of_sight_clearance_m: float
    camera_horizontal_fov: float
    camera_forward_axis: str
    ray_projection_depth_m: float
    lidar_bearing_offset_rad: float
    lidar_frame: str
    map_frame: str


class ObjectLocalizer:
    def __init__(self, config, tf_buffer, logger=None):
        self.config = config
        self.tf_buffer = tf_buffer
        self.logger = logger
        self.camera_info = None
        self.latest_scan = None
        self.latest_pointcloud = None

    def set_camera_info(self, msg):
        self.camera_info = msg

    def set_scan(self, msg):
        self.latest_scan = msg

    def set_pointcloud(self, msg):
        self.latest_pointcloud = msg

    def localize_detection(self, image_msg, projected_cloud, detection, width, height):
        from geometry_msgs.msg import PointStamped
        from tf2_geometry_msgs import do_transform_point

        if self.camera_info is None:
            return None

        center_u = (detection.x1 + detection.x2) / 2.0
        center_v = (detection.y1 + detection.y2) / 2.0
        cluster = self.select_projected_cloud_cluster(
            projected_cloud, detection, center_u, center_v
        )
        if cluster is None:
            cluster = self._select_scan_cluster(
                image_msg, detection, center_u, center_v, width, height
            )
        if cluster is None:
            return None
        if (
            self.config.max_detection_range_m > 0.0
            and cluster.range > self.config.max_detection_range_m
        ):
            return None

        lidar_point = PointStamped()
        lidar_point.header.frame_id = cluster.frame_id
        lidar_point.header.stamp = cluster.stamp
        lidar_point.point.x = cluster.x
        lidar_point.point.y = cluster.y
        lidar_point.point.z = 0.0

        try:
            transform = self._lookup_transform(
                self.config.map_frame, cluster.frame_id, cluster.stamp
            )
            return LocalizedDetection(
                point=do_transform_point(lidar_point, transform),
                cluster=cluster,
            )
        except Exception as exc:
            self._debug(f"Map transform unavailable: {exc}")
            return None

    def project_latest_cloud_to_image(self, image_msg, image_width, image_height):
        import sensor_msgs_py.point_cloud2 as point_cloud2

        if (
            not self.config.use_projected_pointcloud
            or self.latest_pointcloud is None
            or self.camera_info is None
        ):
            return None

        if not message_stamps_within(
            self.latest_pointcloud.header.stamp,
            image_msg.header.stamp,
            self.config.max_sensor_time_delta_s,
        ):
            self._debug("Skipping stale point cloud for current camera frame.")
            return None

        camera_frame = image_msg.header.frame_id or self.camera_info.header.frame_id
        cloud_frame = self.latest_pointcloud.header.frame_id or self.config.lidar_frame
        if not camera_frame or not cloud_frame:
            return None

        try:
            transform = self._lookup_transform(
                camera_frame, cloud_frame, self.latest_pointcloud.header.stamp
            )
            raw_points = point_cloud2.read_points(
                self.latest_pointcloud,
                field_names=("x", "y", "z"),
                skip_nans=True,
            )
            points = self._points_to_array(raw_points)
        except Exception as exc:
            self._debug(f"Point cloud projection unavailable: {exc}")
            return None

        points = finite_xyz_points(points)
        if points.size == 0:
            return None

        points_camera = self._transform_points(points, transform)
        fx, fy, cx, cy = self._camera_intrinsics_for_image(image_width, image_height)
        pixels, depths = self.camera_points_to_pixels(points_camera, fx, fy, cx, cy)

        valid = (
            np.isfinite(pixels[:, 0])
            & np.isfinite(pixels[:, 1])
            & np.isfinite(depths)
            & (depths > 0.05)
            & (pixels[:, 0] >= 0.0)
            & (pixels[:, 0] < image_width)
            & (pixels[:, 1] >= 0.0)
            & (pixels[:, 1] < image_height)
        )
        if not np.any(valid):
            return None

        cloud_points = points[valid]
        return {
            "frame_id": cloud_frame,
            "stamp": self.latest_pointcloud.header.stamp,
            "pixels": pixels[valid],
            "points": cloud_points,
            "ranges": np.hypot(cloud_points[:, 0], cloud_points[:, 1]),
            "angles": np.arctan2(cloud_points[:, 1], cloud_points[:, 0]),
        }

    def projected_indices_in_bbox(self, projected_cloud, detection):
        if projected_cloud is None:
            return np.array([], dtype=int)

        pixels = projected_cloud["pixels"]
        in_box = (
            (pixels[:, 0] >= detection.x1)
            & (pixels[:, 0] <= detection.x2)
            & (pixels[:, 1] >= detection.y1)
            & (pixels[:, 1] <= detection.y2)
        )
        return np.flatnonzero(in_box)

    def draw_projection_debug(
        self, debug_image, projected_cloud, selected_indices, detection
    ):
        cv2.rectangle(
            debug_image,
            (detection.x1, detection.y1),
            (detection.x2, detection.y2),
            (220, 120, 20),
            2,
        )
        label = f"{detection.class_name}: {len(selected_indices)} foreground pts"
        cv2.putText(
            debug_image,
            label,
            (detection.x1, min(debug_image.shape[0] - 8, detection.y2 + 24)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (220, 120, 20),
            2,
        )
        if projected_cloud is None or not len(selected_indices):
            return

        stride = max(1, int(math.ceil(len(selected_indices) / 500.0)))
        pixels = projected_cloud["pixels"][selected_indices[::stride]]
        for u, v in pixels:
            cv2.circle(
                debug_image, (int(round(u)), int(round(v))), 2, (0, 255, 255), -1
            )

    def foreground_projected_indices(self, projected_cloud, detection):
        if projected_cloud is None:
            return np.array([], dtype=int)

        center_u = (detection.x1 + detection.x2) / 2.0
        center_v = (detection.y1 + detection.y2) / 2.0
        _, indices = self._select_projected_cloud_cluster_with_indices(
            projected_cloud, detection, center_u, center_v
        )
        return indices

    def select_projected_cloud_cluster(
        self, projected_cloud, detection, center_u, center_v
    ):
        summary, _ = self._select_projected_cloud_cluster_with_indices(
            projected_cloud, detection, center_u, center_v
        )
        return summary

    def _select_projected_cloud_cluster_with_indices(
        self, projected_cloud, detection, center_u, center_v
    ):
        if projected_cloud is None:
            return None, np.array([], dtype=int)

        selected_indices = self.projected_indices_in_bbox(projected_cloud, detection)
        if len(selected_indices) < self.config.min_lidar_points_per_object:
            return None, np.array([], dtype=int)

        selected_indices = self.foreground_depth_indices(
            selected_indices, projected_cloud["ranges"]
        )
        if len(selected_indices) < self.config.min_lidar_points_per_object:
            return None, np.array([], dtype=int)

        clusters = self.range_clusters_by_range(
            selected_indices, projected_cloud["ranges"]
        )
        best_cluster = None
        best_indices = np.array([], dtype=int)
        bbox_width = max(1.0, float(detection.x2 - detection.x1))
        bbox_height = max(1.0, float(detection.y2 - detection.y1))

        for cluster_indices in clusters:
            if len(cluster_indices) < self.config.min_lidar_points_per_object:
                continue

            summary = self._projected_cluster_summary(projected_cloud, cluster_indices)
            summary.observed_radius = self.cluster_observed_radius(summary)
            if not self.cluster_matches_class(detection.class_name, summary):
                continue

            mean_pixel = np.mean(projected_cloud["pixels"][cluster_indices], axis=0)
            center_error = math.hypot(
                (float(mean_pixel[0]) - center_u) / bbox_width,
                (float(mean_pixel[1]) - center_v) / bbox_height,
            )
            if center_error > 1.2:
                continue

            best_cluster = summary
            best_indices = np.array(cluster_indices, dtype=int)
            break

        return best_cluster, best_indices

    def foreground_depth_indices(self, indices, ranges):
        margin = self.config.projected_foreground_depth_margin_m
        indices = np.array(indices, dtype=int)
        if margin <= 0.0 or len(indices) == 0:
            return indices

        selected_ranges = ranges[indices]
        finite = np.isfinite(selected_ranges)
        if not np.any(finite):
            return np.array([], dtype=int)

        finite_indices = indices[finite]
        finite_ranges = selected_ranges[finite]
        nearest_range = float(np.min(finite_ranges))
        return finite_indices[finite_ranges <= nearest_range + margin]

    def range_clusters_by_range(self, indices, ranges):
        ordered = sorted(indices, key=lambda index: ranges[index])
        clusters = []
        current = [ordered[0]]
        previous_range = ranges[ordered[0]]

        for index in ordered[1:]:
            current_range = ranges[index]
            if abs(current_range - previous_range) > self.config.range_cluster_jump_m:
                clusters.append(current)
                current = [index]
            else:
                current.append(index)
            previous_range = current_range

        clusters.append(current)
        return clusters

    def object_radius(self, class_name, cluster):
        class_min, class_max = self._class_radius_bounds(class_name)
        observed_radius = self.cluster_observed_radius(cluster)
        radius = max(class_min, observed_radius, self.config.default_object_radius_m)
        return min(class_max, self.config.max_object_radius_m, radius)

    def cluster_observed_radius(self, cluster):
        cluster_width = 2.0 * cluster.range * math.sin(
            max(0.0, cluster.angular_width) / 2.0
        )
        return cluster_width / 2.0 + self.config.obstacle_radius_padding_m

    def cluster_matches_class(self, class_name, cluster):
        normalized = class_name.lower()
        observed_radius = cluster.observed_radius

        if normalized in ("sofa", "couch"):
            return observed_radius >= self.config.sofa_min_observed_radius_m
        if normalized == "chair":
            return observed_radius <= self.config.chair_max_observed_radius_m
        return True

    def position_confidence(self, detection_confidence, cluster):
        if self.config.max_detection_range_m <= self.config.reliable_detection_range_m:
            range_confidence = 1.0
        elif cluster.range <= self.config.reliable_detection_range_m:
            range_confidence = 1.0
        else:
            span = (
                self.config.max_detection_range_m
                - self.config.reliable_detection_range_m
            )
            range_ratio = (cluster.range - self.config.reliable_detection_range_m) / span
            range_confidence = 1.0 - max(0.0, min(1.0, range_ratio))

        min_confidence = max(0.0, min(1.0, self.config.min_position_confidence))
        range_confidence = max(min_confidence, range_confidence)
        points_needed = max(1.0, self.config.min_lidar_points_per_object * 2.0)
        points_confidence = min(1.0, cluster.points / points_needed)
        detector_confidence = max(0.0, min(1.0, detection_confidence))

        geometry_confidence = 0.75 * range_confidence + 0.25 * points_confidence
        return min(1.0, geometry_confidence * (0.5 + 0.5 * detector_confidence))

    def camera_points_to_pixels(self, points_camera, fx, fy, cx, cy):
        if self.config.camera_forward_axis == "z":
            image_x = points_camera[:, 0]
            image_y = points_camera[:, 1]
            depth = points_camera[:, 2]
        elif self.config.camera_forward_axis == "-z":
            image_x = points_camera[:, 0]
            image_y = points_camera[:, 1]
            depth = -points_camera[:, 2]
        elif self.config.camera_forward_axis == "-y":
            image_x = points_camera[:, 0]
            image_y = -points_camera[:, 2]
            depth = -points_camera[:, 1]
        else:
            image_x = points_camera[:, 0]
            image_y = -points_camera[:, 2]
            depth = points_camera[:, 1]

        with np.errstate(divide="ignore", invalid="ignore"):
            u = fx * (image_x / depth) + cx
            v = fy * (image_y / depth) + cy
        return np.column_stack((u, v)), depth

    def _select_scan_cluster(
        self, image_msg, detection, center_u, center_v, image_width, image_height
    ):
        if self.latest_scan is None:
            return None

        if not message_stamps_within(
            self.latest_scan.header.stamp,
            image_msg.header.stamp,
            self.config.max_sensor_time_delta_s,
        ):
            self._debug("Skipping stale lidar scan for current camera frame.")
            return None

        scan_frame = self.latest_scan.header.frame_id or self.config.lidar_frame
        left_bearing = self._camera_pixel_to_lidar_bearing(
            image_msg.header.frame_id,
            image_msg.header.stamp,
            scan_frame,
            detection.x1,
            center_v,
            image_width,
            image_height,
        )
        right_bearing = self._camera_pixel_to_lidar_bearing(
            image_msg.header.frame_id,
            image_msg.header.stamp,
            scan_frame,
            detection.x2,
            center_v,
            image_width,
            image_height,
        )
        center_bearing = self._camera_pixel_to_lidar_bearing(
            image_msg.header.frame_id,
            image_msg.header.stamp,
            scan_frame,
            center_u,
            center_v,
            image_width,
            image_height,
        )
        if left_bearing is None or right_bearing is None or center_bearing is None:
            return None

        return self._select_lidar_cluster(
            self.latest_scan, detection.class_name, left_bearing, right_bearing,
            center_bearing
        )

    def _camera_pixel_to_lidar_bearing(
        self, camera_frame, image_stamp, scan_frame, u, v, image_width, image_height
    ):
        from geometry_msgs.msg import PointStamped
        from tf2_geometry_msgs import do_transform_point

        fx, fy, cx, cy = self._camera_intrinsics_for_image(image_width, image_height)
        if fx == 0.0 or fy == 0.0:
            return None

        ray_x, ray_y, ray_z = self._camera_ray(u, v, fx, fy, cx, cy)
        ray_end = PointStamped()
        ray_end.header.frame_id = camera_frame or self.camera_info.header.frame_id
        ray_end.header.stamp = image_stamp
        ray_end.point.x = ray_x
        ray_end.point.y = ray_y
        ray_end.point.z = ray_z

        ray_origin = PointStamped()
        ray_origin.header = ray_end.header
        ray_origin.point.x = 0.0
        ray_origin.point.y = 0.0
        ray_origin.point.z = 0.0

        try:
            transform = self._lookup_transform(scan_frame, ray_end.header.frame_id,
                                               image_stamp)
            origin_lidar = do_transform_point(ray_origin, transform)
            end_lidar = do_transform_point(ray_end, transform)
        except Exception as exc:
            self._debug(f"Camera-to-lidar transform unavailable: {exc}")
            return None

        dx = end_lidar.point.x - origin_lidar.point.x
        dy = end_lidar.point.y - origin_lidar.point.y
        if math.hypot(dx, dy) < 1e-6:
            return None
        return normalize_angle(math.atan2(dy, dx) + self.config.lidar_bearing_offset_rad)

    def _camera_ray(self, u, v, fx, fy, cx, cy):
        x = ((u - cx) / fx) * self.config.ray_projection_depth_m
        y = ((v - cy) / fy) * self.config.ray_projection_depth_m
        depth = self.config.ray_projection_depth_m

        if self.config.camera_forward_axis == "z":
            return x, y, depth
        if self.config.camera_forward_axis == "-z":
            return x, y, -depth
        if self.config.camera_forward_axis == "-y":
            return x, -depth, -y

        return x, depth, -y

    def _camera_intrinsics_for_image(self, image_width, image_height):
        fx = self.camera_info.k[0]
        fy = self.camera_info.k[4]
        cx = self.camera_info.k[2]
        cy = self.camera_info.k[5]

        info_width = self.camera_info.width or image_width
        info_height = self.camera_info.height or image_height
        if info_width > 0 and info_height > 0:
            sx = image_width / float(info_width)
            sy = image_height / float(info_height)
            fx *= sx
            fy *= sy
            cx *= sx
            cy *= sy

        center_is_plausible = (
            0.2 * image_width <= cx <= 0.8 * image_width
            and 0.2 * image_height <= cy <= 0.8 * image_height
        )
        if fx <= 0.0 or fy <= 0.0 or not center_is_plausible:
            fx = image_width / (
                2.0 * math.tan(self.config.camera_horizontal_fov / 2.0)
            )
            fy = fx
            cx = image_width / 2.0
            cy = image_height / 2.0

        return fx, fy, cx, cy

    def _lookup_transform(self, target_frame, source_frame, stamp):
        import rclpy

        try:
            return self.tf_buffer.lookup_transform(target_frame, source_frame, stamp)
        except Exception:
            return self.tf_buffer.lookup_transform(
                target_frame, source_frame, rclpy.time.Time()
            )

    def track_has_line_of_sight(self, track):
        from geometry_msgs.msg import PointStamped
        from tf2_geometry_msgs import do_transform_point

        if self.latest_scan is None:
            return False

        scan_frame = self.latest_scan.header.frame_id or self.config.lidar_frame
        target = PointStamped()
        target.header.frame_id = self.config.map_frame
        target.header.stamp = self.latest_scan.header.stamp
        target.point.x = float(track["x"])
        target.point.y = float(track["y"])
        target.point.z = 0.0

        try:
            transform = self._lookup_transform(
                scan_frame, self.config.map_frame, self.latest_scan.header.stamp
            )
            target_scan = do_transform_point(target, transform)
        except Exception as exc:
            self._debug(f"Object visibility transform unavailable: {exc}")
            return False

        target_range = math.hypot(target_scan.point.x, target_scan.point.y)
        target_bearing = math.atan2(target_scan.point.y, target_scan.point.x)
        half_width = math.radians(max(1.0, self.config.scan_window_deg))
        return scan_path_is_clear(
            self.latest_scan,
            target_bearing,
            target_range,
            half_width,
            self.config.line_of_sight_clearance_m,
        )

    def _transform_points(self, points, transform):
        rotation = quaternion_to_rotation_matrix(transform.transform.rotation)
        translation = np.array(
            [
                transform.transform.translation.x,
                transform.transform.translation.y,
                transform.transform.translation.z,
            ],
            dtype=np.float32,
        )
        return points @ rotation.T + translation

    def _points_to_array(self, raw_points):
        if hasattr(raw_points, "dtype") and raw_points.dtype.names:
            return np.column_stack(
                (raw_points["x"], raw_points["y"], raw_points["z"])
            ).astype(np.float32)

        return np.array(
            [(point[0], point[1], point[2]) for point in raw_points],
            dtype=np.float32,
        )

    def _projected_cluster_summary(self, projected_cloud, indices):
        points = projected_cloud["points"][indices]
        ranges = projected_cloud["ranges"][indices]
        angles = projected_cloud["angles"][indices]
        x = float(np.median(points[:, 0]))
        y = float(np.median(points[:, 1]))
        return ClusterSummary(
            x=x,
            y=y,
            range=float(np.median(ranges)),
            bearing=math.atan2(y, x),
            angular_width=angular_span(angles),
            points=len(indices),
            frame_id=projected_cloud["frame_id"],
            stamp=projected_cloud["stamp"],
            source="pointcloud",
        )

    def _select_lidar_cluster(
        self, scan, class_name, left_bearing, right_bearing, center_bearing
    ):
        padding = math.radians(self.config.bbox_sector_padding_deg)
        half_width = abs(normalize_angle(right_bearing - left_bearing)) / 2.0
        hits = self._scan_hits_near_bearing(scan, center_bearing, half_width + padding)
        if len(hits) < self.config.min_lidar_points_per_object:
            return None

        clusters = range_clusters(hits, self.config.range_cluster_jump_m)
        if not clusters:
            return None

        best_cluster = None
        best_score = None
        for cluster in clusters:
            if len(cluster) < self.config.min_lidar_points_per_object:
                continue

            summary = cluster_summary(cluster)
            summary.frame_id = scan.header.frame_id or self.config.lidar_frame
            summary.stamp = scan.header.stamp
            summary.source = "scan"
            summary.observed_radius = self.cluster_observed_radius(summary)
            if not self.cluster_matches_class(class_name, summary):
                continue

            center_error = abs(normalize_angle(summary.bearing - center_bearing))
            score = (
                summary.angular_width * 12.0
                + len(cluster) * 0.04
                - center_error * 2.0
            )
            if best_score is None or score > best_score:
                best_score = score
                best_cluster = summary

        return best_cluster

    def _scan_hits_near_bearing(self, scan, center_bearing, half_width):
        hits = []
        for index, range_m in enumerate(scan.ranges):
            if not math.isfinite(range_m):
                continue
            if range_m < scan.range_min or range_m > scan.range_max:
                continue

            angle = normalize_angle(scan.angle_min + index * scan.angle_increment)
            if abs(normalize_angle(angle - center_bearing)) > half_width:
                continue

            hits.append(
                {
                    "index": index,
                    "angle": angle,
                    "range": range_m,
                    "x": range_m * math.cos(angle),
                    "y": range_m * math.sin(angle),
                }
            )
        return hits

    def _class_radius_bounds(self, class_name):
        normalized = class_name.lower()
        if normalized in ("chair", "bench"):
            return 0.60, 0.90
        if normalized in ("couch", "sofa"):
            return 0.85, 1.3
        if normalized in ("dining table", "table"):
            return 0.75, 1.25
        if normalized in ("person",):
            return 0.35, 0.65
        if normalized in ("potted plant", "vase"):
            return 0.35, 0.7
        if normalized in ("tv", "laptop", "keyboard", "mouse", "remote"):
            return 0.3, 0.6
        if normalized in ("refrigerator", "microwave", "oven", "sink"):
            return 0.6, 1.0
        return self.config.default_object_radius_m, self.config.max_object_radius_m

    def _debug(self, message):
        if self.logger is not None:
            self.logger.debug(message)


def normalize_angle(angle):
    return math.atan2(math.sin(angle), math.cos(angle))


def stamp_seconds(stamp):
    if stamp is None:
        return None
    if hasattr(stamp, "nanoseconds"):
        return stamp.nanoseconds / 1e9
    if not hasattr(stamp, "sec") or not hasattr(stamp, "nanosec"):
        return None
    return float(stamp.sec) + float(stamp.nanosec) * 1e-9


def message_stamps_within(first_stamp, second_stamp, max_delta_s):
    if max_delta_s <= 0.0:
        return True

    first_time = stamp_seconds(first_stamp)
    second_time = stamp_seconds(second_stamp)
    if first_time is None or second_time is None:
        return True
    if first_time == 0.0 or second_time == 0.0:
        return True
    return abs(first_time - second_time) <= max_delta_s


def scan_path_is_clear(scan, target_bearing, target_range, half_width, clearance_m):
    if scan is None or target_range <= 0.0:
        return False

    blocking_range = target_range - max(0.0, clearance_m)
    saw_relevant_ray = False
    for index, range_m in enumerate(scan.ranges):
        if not math.isfinite(range_m):
            continue
        if range_m < scan.range_min or range_m > scan.range_max:
            continue

        angle = normalize_angle(scan.angle_min + index * scan.angle_increment)
        if abs(normalize_angle(angle - target_bearing)) > half_width:
            continue

        saw_relevant_ray = True
        if range_m < blocking_range:
            return False

    return saw_relevant_ray


def angular_span(angles):
    if len(angles) < 2:
        return 0.0
    unwrapped = np.unwrap(np.array(angles, dtype=float))
    return float(np.max(unwrapped) - np.min(unwrapped))


def range_clusters(hits, range_cluster_jump_m):
    clusters = []
    current = [hits[0]]
    for previous, hit in zip(hits, hits[1:]):
        index_gap = hit["index"] - previous["index"]
        range_gap = abs(hit["range"] - previous["range"])
        if index_gap > 1 or range_gap > range_cluster_jump_m:
            clusters.append(current)
            current = [hit]
        else:
            current.append(hit)
    clusters.append(current)
    return clusters


def cluster_summary(cluster):
    x = float(np.mean([hit["x"] for hit in cluster]))
    y = float(np.mean([hit["y"] for hit in cluster]))
    bearings = [hit["angle"] for hit in cluster]
    ranges = [hit["range"] for hit in cluster]
    return ClusterSummary(
        x=x,
        y=y,
        range=float(np.mean(ranges)),
        bearing=math.atan2(y, x),
        angular_width=angular_span(bearings),
        points=len(cluster),
        frame_id="",
        stamp=None,
        source="",
    )


def quaternion_to_rotation_matrix(quaternion):
    x = quaternion.x
    y = quaternion.y
    z = quaternion.z
    w = quaternion.w
    norm = math.sqrt(x * x + y * y + z * z + w * w)
    if norm == 0.0:
        return np.identity(3, dtype=np.float32)

    x /= norm
    y /= norm
    z /= norm
    w /= norm
    return np.array(
        [
            [
                1.0 - 2.0 * (y * y + z * z),
                2.0 * (x * y - z * w),
                2.0 * (x * z + y * w),
            ],
            [
                2.0 * (x * y + z * w),
                1.0 - 2.0 * (x * x + z * z),
                2.0 * (y * z - x * w),
            ],
            [
                2.0 * (x * z - y * w),
                2.0 * (y * z + x * w),
                1.0 - 2.0 * (x * x + y * y),
            ],
        ],
        dtype=np.float32,
    )


def finite_xyz_points(points):
    if points.size == 0:
        return points.reshape((0, 3))
    finite = np.isfinite(points).all(axis=1)
    return points[finite]
