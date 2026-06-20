from object_detector.run_manifest import (
    RunManifestConfig,
    RunManifestWriter,
    parse_structured_text,
    run_manifest_config_from_params,
)


class RecordingLogger:
    def __init__(self):
        self.warnings = []

    def warning(self, message):
        self.warnings.append(message)


def test_run_manifest_config_defaults_to_log_manifest_dir():
    config = run_manifest_config_from_params({})

    assert config.enabled
    assert config.manifest_dir == "log/manifests"
    assert config.scenario == "object_search_approach"
    assert config.world == "office_world"
    assert config.recipe_path == ""
    assert config.run_dir == ""


def test_parse_structured_text_accepts_json_and_key_value_text():
    assert parse_structured_text('{"x": 1.25, "y": -0.5}') == {
        "x": 1.25,
        "y": -0.5,
    }
    assert parse_structured_text("x=1.0,y=-2.0,yaw=0") == {
        "x": 1.0,
        "y": -2.0,
        "yaw": 0,
    }
    assert parse_structured_text("") is None


def test_run_manifest_writer_writes_yaml_with_artifact_links(tmp_path):
    config = RunManifestConfig(
        manifest_dir=str(tmp_path / "manifests"),
        trial_id="trial-001",
        world="office_world",
        robot_start_pose="x=0.0,y=0.0,yaw=0.0",
        target_class="bottle",
        target_object_pose="x=2.4,y=-0.8,yaw=0.0",
        random_seed="42",
        recipe_path="/workspace/openhri-office/runs/trial-001/recipe.yaml",
        run_dir="/workspace/openhri-office/runs/trial-001",
    )
    event_log_path = tmp_path / "events.jsonl"
    env = {
        "OPENHRI_PLATFORM": "linux/arm64",
        "OPENHRI_IMAGE": "ghcr.io/example/openhri:preview",
        "OPENHRI_DETECTOR_PARAMS": "/workspace/dev_ws/config.yaml",
        "OPENHRI_DETECTOR_PARAM_ARGS": "--params-file base --params-file trial",
        "ROS_DISTRO": "humble",
        "ROS_VERSION": "2",
        "HOSTNAME": "container-id",
    }
    writer = RunManifestWriter(
        config,
        run_id="run-001",
        params={"confidence_threshold": 0.55, "min_confirmations": 2},
        event_log_path=event_log_path,
        env=env,
    )

    assert writer.write()

    assert writer.path == tmp_path / "manifests" / (
        "openhri_object_search_run-001_manifest.yaml"
    )
    text = writer.path.read_text(encoding="utf-8")
    assert 'run_id: "run-001"' in text
    assert 'trial_id: "trial-001"' in text
    assert 'image: "ghcr.io/example/openhri:preview"' in text
    assert 'event_log_path: "' in text
    assert 'trial_recipe_path: "/workspace/openhri-office/runs/trial-001/recipe.yaml"' in text
    assert 'run_dir: "/workspace/openhri-office/runs/trial-001"' in text
    assert 'detector_param_args: "--params-file base --params-file trial"' in text
    assert "confidence_threshold: 0.55" in text
    assert "random_seed: 42" in text

    trial_fields = writer.trial_start_fields()
    assert trial_fields["trial_id"] == "trial-001"
    assert trial_fields["target_class"] == "bottle"
    assert trial_fields["target_object_pose"] == {
        "x": 2.4,
        "y": -0.8,
        "yaw": 0.0,
    }
    assert (
        trial_fields["trial_recipe_path"]
        == "/workspace/openhri-office/runs/trial-001/recipe.yaml"
    )
    assert trial_fields["run_dir"] == "/workspace/openhri-office/runs/trial-001"
    assert trial_fields["run_manifest_path"] == str(writer.path)


def test_run_manifest_writer_can_be_disabled(tmp_path):
    config = RunManifestConfig(
        enabled=False,
        manifest_path=str(tmp_path / "manifest.yaml"),
    )
    writer = RunManifestWriter(config, run_id="run-001", params={})

    assert not writer.write()
    assert not (tmp_path / "manifest.yaml").exists()


def test_run_manifest_writer_disables_when_path_cannot_be_written(tmp_path):
    recording_logger = RecordingLogger()
    writer = RunManifestWriter(
        RunManifestConfig(manifest_path=str(tmp_path)),
        run_id="run-001",
        params={},
        logger=recording_logger,
    )

    assert not writer.write()
    assert not writer.enabled
    assert recording_logger.warnings
