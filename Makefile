IMAGE ?= ghcr.io/thedevmanek/openhri-office:latest-preview
CONTAINER ?= openhri-office
CONTAINERFILE ?= Containerfile
NOVNC_URL ?= http://localhost:6080/vnc.html?autoconnect=1&resize=remote
OBJECT_UI_URL ?= http://localhost:8080
DETECTOR_PARAMS ?= /workspace/openhri-office/dev_ws/src/object_detector/config/object_detector.yaml
DETECTOR_LOG ?= /tmp/openhri-object-detector.log
DETECTOR_PARAM_ARGS ?= --params-file "$(DETECTOR_PARAMS)"
DETECTOR_ROS_ARGS ?=
TRIAL ?=
RECIPE ?=
RUNS_DIR ?= runs
TRIAL_PACKAGE ?=
EVALUATION_OUTPUT ?=
TEST_PACKAGES ?= office_bot_model office_bot_controller_handlers object_detector
TMUX_SESSION ?= openhri
SESSION_TRIAL ?= $(if $(TRIAL),$(TRIAL),bottle-demo)
PYTHON ?= python3
PYTHON_NO_BYTECODE := PYTHONDONTWRITEBYTECODE=1 $(PYTHON)

UNAME_S := $(shell uname -s 2>/dev/null || echo unknown)
UNAME_M := $(shell uname -m 2>/dev/null || echo unknown)

ifeq ($(OPENHRI_PLATFORM),)
  ifeq ($(UNAME_S)-$(UNAME_M),Darwin-arm64)
    OPENHRI_PLATFORM := linux/arm64
  else ifeq ($(UNAME_M),aarch64)
    OPENHRI_PLATFORM := linux/arm64
  else ifeq ($(UNAME_M),arm64)
    OPENHRI_PLATFORM := linux/arm64
  else
    OPENHRI_PLATFORM := linux/amd64
  endif
endif

export OPENHRI_IMAGE := $(IMAGE)
export OPENHRI_CONTAINER_NAME := $(CONTAINER)
export OPENHRI_PLATFORM

.PHONY: help doctor repo-check helper-test build up start start-cached start-local bootstrap test workflow-session workflow-attach workflow-stop stop down restart restart-local ps logs shell sim sim-stop trial trial-plan trial-pack trial-evaluate trial-list detector detector-bg detector-logs detector-stop checkpoint urls clean clean-volumes

help:
	@printf '%s\n' 'OpenHRI workflow:'
	@printf '%s\n' ''
	@printf '%s\n' 'First run:'
	@printf '  %-22s %s\n' 'make doctor' 'Check Podman, platform, ports, and disk space'
	@printf '  %-22s %s\n' 'make repo-check' 'Check docs, links, recipes, and helper scripts'
	@printf '  %-22s %s\n' 'make start' 'Pull runtime, mount source, and bootstrap workspace'
	@printf '  %-22s %s\n' 'make sim' 'Launch Gazebo, RViz, SLAM, Nav2, and the robot'
	@printf '  %-22s %s\n' 'make detector' 'Start object detection and stream logs'
	@printf '  %-22s %s\n' 'make trial' 'Run one repeatable recipe: TRIAL=bottle-demo'
	@printf '  %-22s %s\n' 'make trial-evaluate' 'Summarize events.jsonl into runs/<trial>/evaluation.json'
	@printf '  %-22s %s\n' 'make workflow-session' 'Recreate a scrollable 2x2 tmux workspace'
	@printf '  %-22s %s\n' 'make test' 'Run package tests inside the container'
	@printf '%s\n' ''
	@printf '%s\n' 'Browser URLs:'
	@printf '  %-22s %s\n' 'noVNC' 'http://localhost:6080/vnc.html?autoconnect=1&resize=remote'
	@printf '  %-22s %s\n' 'Object UI' 'http://localhost:8080/ (after make detector)'
	@printf '%s\n' ''
	@printf '%s\n' 'Commands:'
	@printf '  %-22s %s\n' 'make doctor' 'Run read-only preflight checks'
	@printf '  %-22s %s\n' 'make repo-check' 'Run no-Podman repo checks'
	@printf '  %-22s %s\n' 'make helper-test' 'Run no-Podman tests for helper scripts'
	@printf '  %-22s %s\n' 'make start' 'Pull runtime, mount source, and bootstrap workspace'
	@printf '  %-22s %s\n' 'make start-cached' 'Run the cached image without pulling'
	@printf '  %-22s %s\n' 'make start-local' 'Build runtime image locally and run it'
	@printf '  %-22s %s\n' 'make bootstrap' 'Build the mounted ROS workspace'
	@printf '  %-22s %s\n' 'make test' 'Rebuild and run colcon tests in the container'
	@printf '  %-22s %s\n' 'make sim' 'Launch the office simulation in the container'
	@printf '  %-22s %s\n' 'make sim-stop' 'Stop simulation launch, Gazebo, RViz, and Nav2 processes'
	@printf '  %-22s %s\n' 'make trial' 'Prepare runs/<trial>/ and start detector from a recipe'
	@printf '  %-22s %s\n' 'make trial-plan' 'Validate a recipe and write run files without starting detector'
	@printf '  %-22s %s\n' 'make trial-pack' 'Package runs/<trial>/ as a reproducibility zip'
	@printf '  %-22s %s\n' 'make trial-evaluate' 'Evaluate run events and write evaluation.json'
	@printf '  %-22s %s\n' 'make trial-list' 'List checked-in trial recipes'
	@printf '  %-22s %s\n' 'make workflow-session' 'Recreate a 2x2 tmux split grid for logs and outputs'
	@printf '  %-22s %s\n' 'make workflow-attach' 'Attach to the existing tmux workflow session'
	@printf '  %-22s %s\n' 'make workflow-stop' 'Stop simulation, detector, and tmux workflow session'
	@printf '  %-22s %s\n' 'make detector' 'Start/restart detection and stream logs'
	@printf '  %-22s %s\n' 'make detector-bg' 'Start/restart detection without following logs'
	@printf '  %-22s %s\n' 'make detector-logs' 'Follow existing detector logs'
	@printf '  %-22s %s\n' 'make detector-stop' 'Stop the detector process'
	@printf '  %-22s %s\n' 'DETECTOR_ROS_ARGS' 'Extra ROS params for run IDs, trial IDs, and manifest fields'
	@printf '  %-22s %s\n' 'RECIPE' 'Recipe path override for make trial, e.g. runs/foo/recipe.yaml'
	@printf '  %-22s %s\n' 'make shell' 'Open a ROS-ready container shell'
	@printf '  %-22s %s\n' 'make urls' 'Print browser URLs'
	@printf '  %-22s %s\n' 'make restart' 'Pull and recreate the runtime container'
	@printf '  %-22s %s\n' 'make restart-local' 'Build runtime image locally and recreate the container'
	@printf '  %-22s %s\n' 'make down' 'Stop and remove the runtime container'
	@printf '  %-22s %s\n' 'make clean-volumes' 'Remove cached build/install/log volumes'

doctor:
	scripts/doctor.sh

repo-check: helper-test
	$(PYTHON_NO_BYTECODE) scripts/repo_check.py

helper-test:
	$(PYTHON_NO_BYTECODE) scripts/test_trial_evaluator.py

build:
	podman build --platform=$(OPENHRI_PLATFORM) --tag $(IMAGE) --file $(CONTAINERFILE) .

up: start-cached

start: doctor
	podman pull --platform=$(OPENHRI_PLATFORM) $(IMAGE)
	podman compose up -d
	$(MAKE) bootstrap
	$(MAKE) urls

start-cached: doctor
	podman compose up -d
	$(MAKE) bootstrap
	$(MAKE) urls

start-local: doctor build
	podman compose up -d
	$(MAKE) bootstrap
	$(MAKE) urls

bootstrap:
	podman exec $(CONTAINER) bash -lc 'openhri-bootstrap-workspace'

test: bootstrap
	podman exec $(CONTAINER) bash -lc 'source /etc/profile.d/openhri-container-env.sh; cd "$$OPENHRI_WS"; colcon test --packages-select $(TEST_PACKAGES); colcon test-result --verbose'

workflow-session: bootstrap
	$(PYTHON_NO_BYTECODE) scripts/workflow_session.py --trial "$(SESSION_TRIAL)" --recipe "$(RECIPE)" --runs-dir "$(RUNS_DIR)" --session "$(TMUX_SESSION)" --container "$(CONTAINER)" --image "$(IMAGE)" --platform "$(OPENHRI_PLATFORM)" --detector-params "$(DETECTOR_PARAMS)"

workflow-attach:
	tmux attach-session -t "$(TMUX_SESSION)"

workflow-stop:
	-$(MAKE) sim-stop
	-$(MAKE) detector-stop
	-tmux kill-session -t "$(TMUX_SESSION)"

stop:
	podman compose stop

down:
	podman compose down

restart:
	$(MAKE) doctor
	podman pull --platform=$(OPENHRI_PLATFORM) $(IMAGE)
	podman compose up -d --force-recreate
	$(MAKE) bootstrap
	$(MAKE) urls

restart-local:
	$(MAKE) doctor
	$(MAKE) build
	podman compose up -d --force-recreate
	$(MAKE) bootstrap
	$(MAKE) urls

ps:
	podman compose ps

logs:
	podman logs -f $(CONTAINER)

shell:
	podman exec -it $(CONTAINER) bash

sim:
	podman exec -it $(CONTAINER) bash -ic 'ros2 launch office_bot_model launch_sdf_into_gazebo.launch.py'

sim-stop:
	podman exec $(CONTAINER) bash -lc 'pkill -f "ros2 launch office_bot_model launch_sdf_into_gazebo.launch.py" || true; pkill -f "launch_sdf_into_gazebo.launch.py" || true; pkill -f "ign gazebo" || true; pkill -f "gz sim" || true; pkill -f rviz2 || true'
	@printf 'Simulation processes stopped.\n'

trial:
	$(PYTHON_NO_BYTECODE) scripts/trial_runner.py --trial "$(TRIAL)" --recipe "$(RECIPE)" --runs-dir "$(RUNS_DIR)" --container "$(CONTAINER)" --image "$(IMAGE)" --platform "$(OPENHRI_PLATFORM)" --detector-params "$(DETECTOR_PARAMS)"

trial-plan:
	$(PYTHON_NO_BYTECODE) scripts/trial_runner.py --no-start --trial "$(TRIAL)" --recipe "$(RECIPE)" --runs-dir "$(RUNS_DIR)" --container "$(CONTAINER)" --image "$(IMAGE)" --platform "$(OPENHRI_PLATFORM)" --detector-params "$(DETECTOR_PARAMS)"

trial-pack:
	$(PYTHON_NO_BYTECODE) scripts/trial_packager.py --trial "$(TRIAL)" --recipe "$(RECIPE)" --runs-dir "$(RUNS_DIR)" --output "$(TRIAL_PACKAGE)"

trial-evaluate:
	$(PYTHON_NO_BYTECODE) scripts/trial_evaluator.py --trial "$(TRIAL)" --recipe "$(RECIPE)" --runs-dir "$(RUNS_DIR)" --output "$(EVALUATION_OUTPUT)"

trial-list:
	@find recipes/trials -maxdepth 1 -name '*.yaml' -exec basename {} .yaml \; | sort

detector: detector-bg
	@printf 'Streaming detector logs. Press Ctrl-C to stop following; the detector keeps running.\n'
	@printf 'Stop detector: make detector-stop\n'
	$(MAKE) detector-logs

detector-bg:
	podman exec $(CONTAINER) bash -lc 'pkill -f "[/]object_detector/detect" || true'
	podman exec $(CONTAINER) bash -lc ': >"$(DETECTOR_LOG)"'
	podman exec -d -e OPENHRI_IMAGE="$(IMAGE)" -e OPENHRI_PLATFORM="$(OPENHRI_PLATFORM)" -e OPENHRI_DETECTOR_PARAMS="$(DETECTOR_PARAMS)" -e OPENHRI_DETECTOR_PARAM_ARGS="$(DETECTOR_PARAM_ARGS)" -e OPENHRI_REPO_ROOT="/workspace/openhri-office" $(CONTAINER) bash -lc 'source /etc/profile.d/openhri-container-env.sh; export PYTHONUNBUFFERED=1 RCUTILS_LOGGING_BUFFERED_STREAM=0; exec ros2 run object_detector detect --ros-args $(DETECTOR_PARAM_ARGS) $(DETECTOR_ROS_ARGS) >>"$(DETECTOR_LOG)" 2>&1'
	@printf 'Object detector started in the background.\n'
	@printf 'Object UI: %s\n' '$(OBJECT_UI_URL)'
	@printf 'Ad hoc detector logs use dev_ws/log/ by default; recipe trials use runs/<trial_id>/.\n'
	@printf 'Logs:      make detector-logs\n'

detector-logs:
	podman exec -it $(CONTAINER) bash -lc 'if [ ! -f "$(DETECTOR_LOG)" ]; then printf "No detector log found at %s. Run make detector first.\n" "$(DETECTOR_LOG)"; exit 1; fi; tail -n +1 -F "$(DETECTOR_LOG)"'

detector-stop:
	podman exec $(CONTAINER) bash -lc 'pkill -f "[/]object_detector/detect" || true'
	@printf 'Object detector stopped.\n'

checkpoint:
	podman exec -it $(CONTAINER) bash -ic 'download-yolox-checkpoint.sh'

urls:
	@printf 'noVNC:     %s\n' '$(NOVNC_URL)'
	@printf 'Object UI: %s (after make detector)\n' '$(OBJECT_UI_URL)'

clean:
	podman compose down --remove-orphans

clean-volumes:
	podman compose down --volumes --remove-orphans
