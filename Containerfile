FROM docker.io/library/ros:humble-ros-base-jammy

SHELL ["/bin/bash", "-c"]
ENV DEBIAN_FRONTEND=noninteractive
ENV ROS_DISTRO=humble
ENV OPENHRI_WS=/workspace/openhri-office/dev_ws
ENV DISPLAY=:1
ENV VNC_GEOMETRY=1600x900
ENV VNC_DEPTH=24
ENV LIBGL_ALWAYS_SOFTWARE=1
ENV MESA_GL_VERSION_OVERRIDE=3.3
ENV QT_X11_NO_MITSHM=1
ENV OPENHRI_YOLOX_MODEL=yolox-x
ARG OPENHRI_DOWNLOAD_YOLOX_CHECKPOINT=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    dbus-x11 \
    git \
    mesa-utils \
    novnc \
    python3-colcon-common-extensions \
    python3-numpy \
    python3-opencv \
    python3-pip \
    python3-pytest \
    python3-rosdep \
    supervisor \
    websockify \
    wget \
    x11vnc \
    xfce4 \
    xfce4-terminal \
    xvfb \
    zsh \
    ros-humble-controller-manager \
    ros-humble-gz-ros2-control \
    ros-humble-ign-ros2-control \
    ros-humble-mecanum-drive-controller \
    ros-humble-nav2-bringup \
    ros-humble-nav2-common \
    ros-humble-robot-localization \
    ros-humble-ros-gz \
    ros-humble-ros-gz-bridge \
    ros-humble-ros-gz-sim \
    ros-humble-ros2-control \
    ros-humble-ros2-controllers \
    ros-humble-rviz2 \
    ros-humble-slam-toolbox \
    ros-humble-tf2-geometry-msgs \
    ros-humble-xacro \
  && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu \
    torch \
    torchvision \
  && python3 -m pip install --no-cache-dir \
    "numpy<2" \
    loguru \
    ninja \
    pycocotools \
    tabulate \
    thop \
    tqdm \
  && python3 -m pip install --no-cache-dir --no-deps \
    git+https://github.com/Megvii-BaseDetection/YOLOX.git@0.3.0

WORKDIR /workspace/openhri-office
COPY README.md ./README.md
COPY docs ./docs
COPY dev_ws ./dev_ws
COPY container/start-desktop.sh /usr/local/bin/start-desktop.sh
COPY container/start-openhri.sh /usr/local/bin/start-openhri.sh
COPY container/start-object-detector.sh /usr/local/bin/start-object-detector.sh
COPY container/download-yolox-checkpoint.sh /usr/local/bin/download-yolox-checkpoint.sh
COPY container/openhri-container-env.sh /etc/profile.d/openhri-container-env.sh
COPY container/supervisord.conf /etc/supervisor/conf.d/openhri.conf

RUN mkdir -p /root/Desktop
COPY container/openhri-office.desktop /root/Desktop/OpenHRI-Office.desktop
COPY container/openhri-object-ui.desktop /root/Desktop/OpenHRI-Object-UI.desktop

RUN chmod +x /usr/local/bin/start-desktop.sh \
    /usr/local/bin/start-openhri.sh \
    /usr/local/bin/start-object-detector.sh \
    /usr/local/bin/download-yolox-checkpoint.sh \
    /etc/profile.d/openhri-container-env.sh \
    /root/Desktop/OpenHRI-Office.desktop \
    /root/Desktop/OpenHRI-Object-UI.desktop

RUN grep -qxF 'source /etc/profile.d/openhri-container-env.sh' /root/.bashrc \
    || echo 'source /etc/profile.d/openhri-container-env.sh' >> /root/.bashrc \
  && echo 'source /etc/profile.d/openhri-container-env.sh' > /root/.zshrc

RUN if [[ "${OPENHRI_DOWNLOAD_YOLOX_CHECKPOINT}" == "1" ]]; then \
      /usr/local/bin/download-yolox-checkpoint.sh; \
    else \
      echo "Skipping YOLOX checkpoint download."; \
    fi

RUN bash -lc 'rosdep init 2>/dev/null || true \
  && rosdep update \
  && source /opt/ros/humble/setup.bash \
  && cd "${OPENHRI_WS}" \
  && rosdep install --from-paths src --ignore-src -r -y \
  && colcon build --symlink-install'

EXPOSE 6080 5900 8080
CMD ["/usr/local/bin/start-desktop.sh"]
