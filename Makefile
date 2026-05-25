IMAGE ?= openhri-office:0.1.0-preview
CONTAINER ?= openhri-office
NOVNC_URL ?= http://localhost:6080/vnc.html?autoconnect=1&resize=remote
OBJECT_UI_URL ?= http://localhost:8080
DETECTOR_PARAMS ?= /workspace/openhri-office/dev_ws/src/object_detector/config/object_detector.yaml
DETECTOR_LOG ?= /tmp/openhri-object-detector.log

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

.PHONY: help build up start stop down restart ps logs shell sim detector detector-bg detector-logs detector-stop checkpoint urls clean

help:
	@printf '%s\n' 'OpenHRI Office simulation workflow:'
	@printf '%s\n' ''
	@printf '%s\n' 'First run:'
	@printf '  %-18s %s\n' 'make start' 'Build/start the preview container'
	@printf '  %-18s %s\n' 'make sim' 'Launch Gazebo, RViz, SLAM, Nav2, and the robot'
	@printf '  %-18s %s\n' 'make detector' 'Start object detection and stream logs'
	@printf '%s\n' ''
	@printf '%s\n' 'Browser URLs:'
	@printf '  %-18s %s\n' 'noVNC' 'http://localhost:6080/vnc.html?autoconnect=1&resize=remote'
	@printf '  %-18s %s\n' 'Object UI' 'http://localhost:8080/'
	@printf '%s\n' ''
	@printf '%s\n' 'Commands:'
	@printf '  %-18s %s\n' 'make start' 'Build and run the browser preview'
	@printf '  %-18s %s\n' 'make sim' 'Launch the office simulation in the container'
	@printf '  %-18s %s\n' 'make detector' 'Start/restart detection and stream logs'
	@printf '  %-18s %s\n' 'make detector-bg' 'Start/restart detection without following logs'
	@printf '  %-18s %s\n' 'make detector-logs' 'Follow existing detector logs'
	@printf '  %-18s %s\n' 'make detector-stop' 'Stop the detector process'
	@printf '  %-18s %s\n' 'make shell' 'Open a ROS-ready container shell'
	@printf '  %-18s %s\n' 'make urls' 'Print browser URLs'
	@printf '  %-18s %s\n' 'make down' 'Stop and remove the preview container'

build:
	podman compose build

up:
	podman compose up --build

start:
	podman compose up --build -d
	$(MAKE) urls

stop:
	podman compose stop

down:
	podman compose down

restart:
	podman compose up --build -d --force-recreate
	$(MAKE) urls

ps:
	podman compose ps

logs:
	podman logs -f $(CONTAINER)

shell:
	podman exec -it $(CONTAINER) bash

sim:
	podman exec -it $(CONTAINER) bash -ic 'ros2 launch office_bot_model launch_sdf_into_gazebo.launch.py'

detector: detector-bg
	@printf 'Streaming detector logs. Press Ctrl-C to stop following; the detector keeps running.\n'
	@printf 'Stop detector: make detector-stop\n'
	$(MAKE) detector-logs

detector-bg:
	podman exec $(CONTAINER) bash -lc 'pkill -f "[/]object_detector/detect" || true'
	podman exec $(CONTAINER) bash -lc ': >"$(DETECTOR_LOG)"'
	podman exec -d $(CONTAINER) bash -lc 'source /etc/profile.d/openhri-container-env.sh; export PYTHONUNBUFFERED=1 RCUTILS_LOGGING_BUFFERED_STREAM=0; exec ros2 run object_detector detect --ros-args --params-file "$(DETECTOR_PARAMS)" >>"$(DETECTOR_LOG)" 2>&1'
	@printf 'Object detector started in the background.\n'
	@printf 'Object UI: %s\n' '$(OBJECT_UI_URL)'
	@printf 'Logs:      make detector-logs\n'

detector-logs:
	podman exec -it $(CONTAINER) bash -lc 'if [ ! -f "$(DETECTOR_LOG)" ]; then printf "No detector log found at %s. Run make detector first.\n" "$(DETECTOR_LOG)"; exit 1; fi; tail -n +1 -F "$(DETECTOR_LOG)"'

detector-stop:
	podman exec $(CONTAINER) bash -lc 'pkill -f "[/]object_detector/detect" || true'
	@printf 'Object detector stopped.\n'

checkpoint:
	podman exec -it $(CONTAINER) bash -ic 'download-yolox-checkpoint.sh && colcon build --packages-select object_detector --symlink-install && source install/setup.bash'

urls:
	@printf 'noVNC:     %s\n' '$(NOVNC_URL)'
	@printf 'Object UI: %s\n' '$(OBJECT_UI_URL)'

clean:
	podman compose down --remove-orphans
