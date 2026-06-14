# Runtime Image Release

The OpenHRI Office image is a runtime base. It contains ROS 2 Humble, Gazebo/Ignition, RViz, Nav2, SLAM Toolbox, YOLOX, noVNC, startup scripts, bootstrap tooling, and the YOLOX checkpoint.

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

The canonical image is:

```text
ghcr.io/thedevmanek/openhri-office:0.1.0-preview
```

The moving preview tag is:

```text
ghcr.io/thedevmanek/openhri-office:latest-preview
```

## Publishing

GitHub Actions publishes the multi-architecture runtime image to GitHub Container Registry.

The workflow publishes `latest-preview` on pushes to `main` when runtime-image inputs change:

- `Containerfile`
- `compose.yaml`
- `container/**`
- `.github/workflows/publish-runtime-image.yml`

The workflow also runs for tags matching `v*`. A tag such as:

```text
v0.1.0-preview
```

publishes:

```text
ghcr.io/thedevmanek/openhri-office:0.1.0-preview
```

You can also run the workflow manually with an `image_tag` input.

## Local Runtime Build

Use this when changing runtime-image inputs:

```bash
make start-local
```

Use this when changing mounted workspace source under `dev_ws/`:

```bash
make bootstrap
```
