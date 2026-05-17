import math

import numpy as np

from object_detector.datatypes import ObjectTrack


class TrackManager:
    def __init__(
        self,
        cluster_radius_m,
        confirmed_association_radius_m,
        min_confirmations,
        track_timeout_s,
        freeze_confirmed_tracks=True,
        duplicate_track_merge_radius_m=None,
    ):
        self.cluster_radius_m = cluster_radius_m
        self.confirmed_association_radius_m = confirmed_association_radius_m
        self.min_confirmations = min_confirmations
        self.track_timeout_s = track_timeout_s
        self.freeze_confirmed_tracks = freeze_confirmed_tracks
        self.duplicate_track_merge_radius_m = (
            duplicate_track_merge_radius_m
            if duplicate_track_merge_radius_m is not None
            else confirmed_association_radius_m
        )
        self.tracks = {}
        self.next_track_id = 1

    def update_track(
        self,
        class_name,
        map_point,
        confidence,
        object_radius,
        position_confidence,
        now,
        snapshot=None,
    ):
        x = map_point.point.x
        y = map_point.point.y
        position_confidence = max(0.0, min(1.0, position_confidence))
        self.prune_stale(now)

        best_id = None
        best_distance = None
        for track_id, track in self.tracks.items():
            if track.class_name != class_name:
                continue
            distance = math.hypot(track.x - x, track.y - y)
            radius = (
                self.confirmed_association_radius_m
                if track.confirmed
                else self.cluster_radius_m
            )
            if distance <= radius and (
                best_distance is None or distance < best_distance
            ):
                best_id = track_id
                best_distance = distance

        if best_id is None:
            track_id = self._create_track(
                class_name,
                x,
                y,
                confidence,
                object_radius,
                position_confidence,
                now,
                snapshot,
            )
            return self._merge_nearby_duplicates(track_id)

        track_id = self._merge_track(
            best_id, x, y, confidence, object_radius, position_confidence, now, snapshot
        )
        return self._merge_nearby_duplicates(track_id)

    def confirmed_count(self, now):
        self.prune_stale(now)
        return sum(1 for track in self.tracks.values() if track.confirmed)

    def confirmed_tracks(self, now):
        self.prune_stale(now)
        return [track.as_dict() for track in self.tracks.values() if track.confirmed]

    def classes(self, now):
        self.prune_stale(now)
        return sorted(
            {track.class_name for track in self.tracks.values() if track.confirmed}
        )

    def locations(self, class_name, now):
        self.prune_stale(now)
        tracks = [
            track.as_dict()
            for track in self.tracks.values()
            if track.confirmed and (not class_name or track.class_name == class_name)
        ]
        return sorted(tracks, key=lambda track: (track["class_name"], track["track_id"]))

    def get_confirmed_track(self, track_id, now):
        self.prune_stale(now)
        track = self.tracks.get(track_id)
        if track is None:
            return None, f"Track {track_id} was not found."
        if not track.confirmed:
            return None, f"Track {track_id} is not confirmed yet."
        return track.as_dict(), None

    def clear(self):
        self.tracks.clear()
        self.next_track_id = 1

    def prune_stale(self, now):
        if self.track_timeout_s <= 0.0:
            return []

        expired_track_ids = [
            track_id
            for track_id, track in self.tracks.items()
            if not track.confirmed and now - track.last_seen > self.track_timeout_s
        ]
        for track_id in expired_track_ids:
            self.tracks.pop(track_id, None)
        return expired_track_ids

    def _create_track(
        self,
        class_name,
        x,
        y,
        confidence,
        object_radius,
        position_confidence,
        now,
        snapshot,
    ):
        track_id = self.next_track_id
        self.next_track_id += 1
        confirmation_score = position_confidence
        confirmed = confirmation_score >= self._confirmation_threshold()
        self.tracks[track_id] = ObjectTrack(
            track_id=track_id,
            class_name=class_name,
            x=x,
            y=y,
            obstacle_radius=object_radius,
            confidence=confidence,
            position_confidence=position_confidence,
            confirmation_score=confirmation_score,
            detections=1,
            confirmed=confirmed,
            confirmed_at=now if confirmed else None,
            last_seen=now,
            snapshot=snapshot,
        )
        return track_id

    def _merge_track(
        self,
        track_id,
        x,
        y,
        confidence,
        object_radius,
        position_confidence,
        now,
        snapshot,
    ):
        track = self.tracks[track_id]
        previous_confidence = track.position_confidence
        alpha = 0.15 + 0.45 * position_confidence
        if track.confirmed:
            alpha *= 0.5
        if (
            not self.freeze_confirmed_tracks
            and position_confidence >= previous_confidence
        ) or not track.confirmed:
            track.x = (1.0 - alpha) * track.x + alpha * x
            track.y = (1.0 - alpha) * track.y + alpha * y

        confirmation_score = track.confirmation_score + position_confidence
        if not track.confirmed and confirmation_score >= self._confirmation_threshold():
            track.confirmed = True
            track.confirmed_at = now

        track.confidence = max(track.confidence, confidence)
        track.position_confidence = max(previous_confidence, position_confidence)
        track.confirmation_score = confirmation_score
        track.obstacle_radius = max(track.obstacle_radius, object_radius)
        if snapshot:
            track.snapshot = snapshot
        track.detections += 1
        track.last_seen = now
        return track_id

    def _merge_nearby_duplicates(self, track_id):
        track = self.tracks.get(track_id)
        if track is None:
            return track_id

        for other_id, other in list(self.tracks.items()):
            if other_id == track_id or other.class_name != track.class_name:
                continue

            distance = math.hypot(track.x - other.x, track.y - other.y)
            merge_radius = (
                self.duplicate_track_merge_radius_m
                if track.confirmed or other.confirmed
                else self.cluster_radius_m
            )
            if distance > merge_radius:
                continue

            keep_id, remove_id = self._duplicate_keeper(track_id, other_id)
            self._absorb_track(keep_id, remove_id)
            track_id = keep_id
            track = self.tracks[track_id]

        return track_id

    def _duplicate_keeper(self, first_id, second_id):
        first = self.tracks[first_id]
        second = self.tracks[second_id]
        if first.confirmed != second.confirmed:
            return (first_id, second_id) if first.confirmed else (second_id, first_id)
        if first.confirmed_at != second.confirmed_at:
            first_time = first.confirmed_at if first.confirmed_at is not None else math.inf
            second_time = second.confirmed_at if second.confirmed_at is not None else math.inf
            return (first_id, second_id) if first_time <= second_time else (second_id, first_id)
        return (first_id, second_id) if first_id <= second_id else (second_id, first_id)

    def _absorb_track(self, keep_id, remove_id):
        keep = self.tracks[keep_id]
        remove = self.tracks.pop(remove_id)
        keep_detections = keep.detections
        remove_detections = remove.detections
        total_detections = keep_detections + remove_detections

        if not keep.confirmed or not self.freeze_confirmed_tracks:
            keep.x = (
                keep.x * keep_detections + remove.x * remove_detections
            ) / total_detections
            keep.y = (
                keep.y * keep_detections + remove.y * remove_detections
            ) / total_detections

        keep.confidence = max(keep.confidence, remove.confidence)
        keep.position_confidence = max(
            keep.position_confidence, remove.position_confidence
        )
        keep.confirmation_score += remove.confirmation_score
        keep.obstacle_radius = max(keep.obstacle_radius, remove.obstacle_radius)
        keep.detections = total_detections
        keep.last_seen = max(keep.last_seen, remove.last_seen)
        if remove.snapshot and (
            keep.snapshot is None or remove.last_seen >= keep.last_seen
        ):
            keep.snapshot = remove.snapshot
        if not keep.confirmed and keep.confirmation_score >= self._confirmation_threshold():
            keep.confirmed = True
            keep.confirmed_at = keep.last_seen

    def _confirmation_threshold(self):
        if self.min_confirmations <= 1:
            return 0.0
        return float(self.min_confirmations)


def footprint_points(
    track,
    default_object_radius_m,
    obstacle_point_spacing_m,
    obstacle_point_min_z_m,
    obstacle_point_max_z_m,
    obstacle_point_z_spacing_m,
):
    radius = track.get("obstacle_radius", default_object_radius_m)
    spacing = max(0.05, obstacle_point_spacing_m)
    min_z = max(0.0, obstacle_point_min_z_m)
    max_z = max(min_z, obstacle_point_max_z_m)
    z_spacing = max(0.05, obstacle_point_z_spacing_m)
    points = []
    x_values = np.arange(-radius, radius + spacing, spacing)
    y_values = np.arange(-radius, radius + spacing, spacing)
    z_values = np.arange(min_z, max_z + z_spacing, z_spacing)
    for dx in x_values:
        for dy in y_values:
            if dx * dx + dy * dy <= radius * radius:
                for z in z_values:
                    points.append(
                        (
                            float(track["x"] + dx),
                            float(track["y"] + dy),
                            float(z),
                        )
                    )
    return points
