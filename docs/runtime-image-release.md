# Runtime Image Release

The OpenHRI `office_bot` image is a runtime base. It contains ROS 2 Humble, Gazebo/Ignition, RViz, Nav2, SLAM Toolbox, YOLOX, noVNC, startup scripts, bootstrap tooling, and the YOLOX checkpoint.

It does not contain the project workspace. At runtime, `compose.yaml` mounts this repository read-only at:

```text
/workspace/openhri-office
```

ROS build artifacts are stored in named Podman volumes for:

```text
/workspace/openhri-office/dev_ws/build
/workspace/openhri-office/dev_ws/install
/workspace/openhri-office/dev_ws/log
```

## Published Image

The default published runtime image is:

```text
ghcr.io/thedevmanek/openhri-office:latest-preview
```

The image name still uses the original package path for compatibility with the published runtime. Historical or versioned tags are not published by this workflow.

## Publishing

GitHub Actions publishes the multi-architecture runtime image to GitHub Container Registry.

The workflow publishes `latest-preview` only after changes are merged to `main`
and the merge commit changes one of these runtime-image inputs:

- `Containerfile`
- `container/**`
- `.github/workflows/publish-runtime-image.yml`

Changes to `compose.yaml` do not trigger the image publish workflow because the
compose file is a local runtime wrapper, not part of the built image.

## Local Runtime Build

Use this when changing runtime-image inputs:

```bash
make start-local
```

Use this when changing mounted workspace source under `dev_ws/`:

```bash
make bootstrap
```
