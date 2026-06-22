# Visual Media Guide

Use real hardware photos and simulation screenshots as evidence, not decoration.
They should help visitors understand what exists in the OpenHRI `office_bot`
project, what is simulated, and what is still in bringup.

## Recommended Public Assets

- Hero image: one clean hardware photo showing the assembled robot or workbench,
  with no private location details, serial numbers, addresses, or unrelated
  personal items visible.
- Simulation strip: two or three screenshots from noVNC, Gazebo, RViz, and the
  object UI showing the same object-search workflow from different viewpoints.
- Demo video: one short MP4 showing a complete public workflow; keep the raw
  recording out of Git unless it is already small, trimmed, and metadata-clean.
  Strip audio unless narration is intentional and reviewed.
- Bringup image: one labeled hardware-detail photo for wiring, compute, sensor
  mount, or chassis status when the hardware docs mention that subsystem.

## Suggested Paths

Keep public-ready images under:

```text
docs/assets/media/
```

Use descriptive lowercase filenames:

```text
hardware-bench-v1.jpg
simulation-gazebo-office-v1.jpg
simulation-object-ui-v1.jpg
office-bot-object-hunt-demo.mp4
office-bot-object-hunt-demo-poster.jpg
```

Do not check in raw camera dumps. Crop, downscale, and remove metadata first.
For GitHub README use, keep each image under about 1 MB when possible.

## Simple Image Workflow

1. Choose the clearest hardware photo and two simulation screenshots.
2. Crop to focus on the robot, UI, or workflow result.
3. Remove EXIF/GPS metadata before committing public images.
4. Export JPEG for photos and PNG for UI screenshots.
5. Add the images to `docs/assets/media/`.
6. Reference them from `README.md` or the relevant public doc.

## What To Avoid

- Private rooms, addresses, screens, shipping labels, invoices, keys, faces, or
  other personal details.
- Photos that imply hardware is complete before the hardware readiness checklist
  has evidence.
- Simulation screenshots without a caption explaining what is being shown.
- Images that replace run artifacts. For reproducibility, use packaged run
  outputs as the source of truth.
