import math
from types import SimpleNamespace

import numpy as np

from object_detector.localization import (
    LocalizationConfig,
    ObjectLocalizer,
    angular_span,
    cluster_summary,
    finite_xyz_points,
    message_stamps_within,
    range_clusters,
    scan_path_is_clear,
)
from object_detector.model import bbox_area_ratio, clamp_bbox
from object_detector.datatypes import DetectionBox
from object_detector.navigation import (
    adaptive_stand_off,
    candidate_angle_offsets,
    candidate_radii,
    surface_approach_pose,
)
from object_detector.tracking import TrackManager, footprint_points


def _map_point(x, y):
    return SimpleNamespace(point=SimpleNamespace(x=x, y=y))


def _localizer():
    return ObjectLocalizer(
        LocalizationConfig(
            scan_window_deg=2.0,
            bbox_sector_padding_deg=4.0,
            range_cluster_jump_m=0.5,
            min_lidar_points_per_object=2,
            max_detection_range_m=8.0,
            reliable_detection_range_m=4.0,
            min_position_confidence=0.05,
            use_projected_pointcloud=True,
            sofa_min_observed_radius_m=0.35,
            chair_max_observed_radius_m=1.10,
            default_object_radius_m=0.5,
            obstacle_radius_padding_m=0.1,
            max_object_radius_m=1.2,
            projected_foreground_depth_margin_m=0.35,
            max_sensor_time_delta_s=0.25,
            line_of_sight_clearance_m=0.35,
            camera_horizontal_fov=1.04,
            camera_forward_axis="z",
            ray_projection_depth_m=10.0,
            lidar_bearing_offset_rad=0.0,
            lidar_frame="lidar_link",
            map_frame="map",
        ),
        tf_buffer=None,
    )


def test_bbox_helpers_clamp_and_filter_area():
    assert clamp_bbox((-5, 10, 120, 220), 100, 200) == (0, 10, 99, 199)
    assert bbox_area_ratio(0, 0, 10, 10, 100, 100) == 0.01
    assert bbox_area_ratio(10, 10, 5, 5, 100, 100) == 0.0


def test_range_clusters_split_on_index_or_range_jump():
    hits = [
        {"index": 0, "range": 1.0, "angle": 0.0, "x": 1.0, "y": 0.0},
        {"index": 1, "range": 1.1, "angle": 0.1, "x": 1.1, "y": 0.1},
        {"index": 3, "range": 1.1, "angle": 0.2, "x": 1.1, "y": 0.2},
        {"index": 4, "range": 2.0, "angle": 0.3, "x": 2.0, "y": 0.3},
    ]

    clusters = range_clusters(hits, range_cluster_jump_m=0.5)

    assert [len(cluster) for cluster in clusters] == [2, 1, 1]
    summary = cluster_summary(clusters[0])
    assert summary.points == 2
    assert summary.range == 1.05


def test_angular_span_handles_wrapped_angles():
    span = angular_span([math.radians(179), math.radians(-179)])

    assert math.isclose(span, math.radians(2), rel_tol=0.0, abs_tol=1e-6)


def test_finite_xyz_points_removes_nan_and_inf_before_transform():
    points = np.array(
        [
            [1.0, 2.0, 3.0],
            [math.inf, 2.0, 3.0],
            [1.0, math.nan, 3.0],
            [4.0, 5.0, 6.0],
        ],
        dtype=np.float32,
    )

    filtered = finite_xyz_points(points)

    assert filtered.tolist() == [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]


def test_message_stamps_within_rejects_stale_sensor_frame():
    image_stamp = SimpleNamespace(sec=10, nanosec=0)
    fresh_sensor_stamp = SimpleNamespace(sec=10, nanosec=200_000_000)
    stale_sensor_stamp = SimpleNamespace(sec=11, nanosec=0)

    assert message_stamps_within(fresh_sensor_stamp, image_stamp, 0.25)
    assert not message_stamps_within(stale_sensor_stamp, image_stamp, 0.25)


def test_scan_path_is_clear_rejects_wall_before_target():
    scan = SimpleNamespace(
        ranges=[5.0, 5.0, 2.0, 5.0, 5.0],
        angle_min=-0.2,
        angle_increment=0.1,
        range_min=0.1,
        range_max=10.0,
    )

    assert not scan_path_is_clear(
        scan, target_bearing=0.0, target_range=4.0, half_width=0.05, clearance_m=0.3
    )


def test_scan_path_is_clear_allows_ray_without_closer_hit():
    scan = SimpleNamespace(
        ranges=[5.0, 5.0, 4.1, 5.0, 5.0],
        angle_min=-0.2,
        angle_increment=0.1,
        range_min=0.1,
        range_max=10.0,
    )

    assert scan_path_is_clear(
        scan, target_bearing=0.0, target_range=4.0, half_width=0.05, clearance_m=0.3
    )


def test_foreground_projected_indices_ignore_wall_points_behind_object():
    projected_cloud = {
        "pixels": np.array(
            [
                [40.0, 40.0],
                [45.0, 42.0],
                [50.0, 40.0],
                [52.0, 42.0],
            ],
            dtype=np.float32,
        ),
        "points": np.array(
            [
                [2.0, 0.0, 0.2],
                [2.1, 0.1, 0.2],
                [5.0, 0.0, 0.2],
                [5.1, 0.1, 0.2],
            ],
            dtype=np.float32,
        ),
        "ranges": np.array([2.0, 2.1, 5.0, 5.1], dtype=np.float32),
        "angles": np.array([0.0, 0.05, 0.0, 0.02], dtype=np.float32),
        "frame_id": "lidar_link",
        "stamp": None,
    }
    detection = DetectionBox(0, "chair", 0.9, 30, 30, 60, 60)

    indices = _localizer().foreground_projected_indices(projected_cloud, detection)

    assert indices.tolist() == [0, 1]


def test_foreground_projected_indices_trim_nearby_wall_in_same_range_cluster():
    projected_cloud = {
        "pixels": np.array(
            [
                [40.0, 40.0],
                [45.0, 42.0],
                [50.0, 40.0],
                [52.0, 42.0],
            ],
            dtype=np.float32,
        ),
        "points": np.array(
            [
                [2.0, 0.0, 0.2],
                [2.1, 0.1, 0.2],
                [2.45, 0.0, 0.2],
                [2.5, 0.1, 0.2],
            ],
            dtype=np.float32,
        ),
        "ranges": np.array([2.0, 2.1, 2.45, 2.5], dtype=np.float32),
        "angles": np.array([0.0, 0.05, 0.0, 0.02], dtype=np.float32),
        "frame_id": "lidar_link",
        "stamp": None,
    }
    detection = DetectionBox(0, "chair", 0.9, 30, 30, 60, 60)

    indices = _localizer().foreground_projected_indices(projected_cloud, detection)

    assert indices.tolist() == [0, 1]


def test_track_manager_confirms_and_prunes_unconfirmed_tracks():
    tracks = TrackManager(
        cluster_radius_m=0.5,
        confirmed_association_radius_m=1.25,
        min_confirmations=2,
        track_timeout_s=5.0,
    )

    track_id = tracks.update_track("chair", _map_point(1.0, 2.0), 0.8, 0.6, 1.0, 0.0)
    assert tracks.confirmed_count(0.0) == 0

    same_track_id = tracks.update_track(
        "chair", _map_point(1.1, 2.0), 0.9, 0.7, 1.0, 1.0
    )
    assert same_track_id == track_id
    assert tracks.confirmed_count(1.0) == 1

    stale_id = tracks.update_track(
        "bottle", _map_point(4.0, 0.0), 0.8, 0.3, 0.5, 1.0
    )
    assert stale_id in tracks.tracks
    tracks.prune_stale(7.0)
    assert stale_id not in tracks.tracks


def test_confirmed_track_position_freezes_for_persistent_approach_anchor():
    tracks = TrackManager(
        cluster_radius_m=0.75,
        confirmed_association_radius_m=1.5,
        min_confirmations=2,
        track_timeout_s=5.0,
        freeze_confirmed_tracks=True,
    )

    track_id = tracks.update_track("chair", _map_point(1.0, 2.0), 0.8, 0.4, 1.0, 0.0)
    tracks.update_track("chair", _map_point(1.1, 2.0), 0.9, 0.4, 1.0, 1.0)
    locked_x = tracks.tracks[track_id].x
    locked_y = tracks.tracks[track_id].y

    tracks.update_track("chair", _map_point(1.6, 2.4), 0.95, 0.4, 1.0, 2.0)

    assert tracks.tracks[track_id].x == locked_x
    assert tracks.tracks[track_id].y == locked_y


def test_tracker_merges_duplicate_tracks_after_confirmation():
    tracks = TrackManager(
        cluster_radius_m=0.5,
        confirmed_association_radius_m=1.5,
        min_confirmations=2,
        track_timeout_s=5.0,
        freeze_confirmed_tracks=True,
        duplicate_track_merge_radius_m=1.5,
    )

    first_id = tracks.update_track("chair", _map_point(0.0, 0.0), 0.8, 0.4, 1.0, 0.0)
    second_id = tracks.update_track(
        "chair", _map_point(1.0, 0.0), 0.8, 0.4, 1.0, 0.2
    )
    assert second_id != first_id
    assert len(tracks.tracks) == 2

    merged_id = tracks.update_track(
        "chair", _map_point(0.1, 0.0), 0.9, 0.4, 1.0, 0.4
    )

    assert merged_id == first_id
    assert len(tracks.tracks) == 1
    assert tracks.confirmed_count(0.4) == 1


def test_footprint_points_fill_cylindrical_volume():
    track = {"x": 1.0, "y": 2.0, "obstacle_radius": 0.1}

    points = footprint_points(track, 0.5, 0.1, 0.0, 0.1, 0.1)

    assert (1.0, 2.0, 0.0) in points
    assert (1.0, 2.0, 0.1) in points
    assert all(math.hypot(x - 1.0, y - 2.0) <= 0.100001 for x, y, _ in points)


def test_goal_candidate_helpers_preserve_current_ordering():
    assert candidate_radii(0.7, 2.0) == [0.7, 1.45, 2.0]

    offsets = candidate_angle_offsets(90.0)

    assert offsets[:5] == [0.0, math.pi / 2.0, -math.pi / 2.0, math.pi, -math.pi]


def test_goal_candidate_offsets_can_be_limited_to_front_arc():
    offsets = candidate_angle_offsets(30.0, max_abs_angle_deg=75.0)

    assert offsets == [
        0.0,
        math.pi / 6.0,
        -math.pi / 6.0,
        math.pi / 3.0,
        -math.pi / 3.0,
        math.radians(75.0),
        -math.radians(75.0),
    ]


def test_surface_approach_pose_offsets_from_observed_surface():
    goal_x, goal_y, yaw = surface_approach_pose(
        surface_x=2.0,
        surface_y=0.0,
        approach_angle=0.0,
        stand_off_m=0.7,
    )

    assert math.isclose(goal_x, 1.3)
    assert math.isclose(goal_y, 0.0)
    assert math.isclose(yaw, 0.0)


def test_adaptive_stand_off_gets_closer_with_confidence_and_range():
    far_uncertain = adaptive_stand_off(
        distance_to_surface=5.0,
        confidence=0.2,
        far_stand_off_m=1.2,
        min_stand_off_m=0.65,
        close_stop_distance_m=0.55,
        max_distance_m=5.0,
    )
    close_confident = adaptive_stand_off(
        distance_to_surface=0.9,
        confidence=0.95,
        far_stand_off_m=1.2,
        min_stand_off_m=0.65,
        close_stop_distance_m=0.55,
        max_distance_m=5.0,
    )

    assert math.isclose(far_uncertain, 1.2)
    assert close_confident < far_uncertain
    assert close_confident >= 0.65
