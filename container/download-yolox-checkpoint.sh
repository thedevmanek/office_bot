#!/usr/bin/env bash
set -euo pipefail

OPENHRI_WS="${OPENHRI_WS:-/workspace/openhri-office/dev_ws}"
CHECKPOINT_DIR="${OPENHRI_CHECKPOINT_DIR:-/opt/openhri/checkpoints}"
MODEL_NAME="${OPENHRI_YOLOX_MODEL:-yolox-x}"

case "${MODEL_NAME}" in
  yolox-x)
    CHECKPOINT="${OPENHRI_YOLOX_CHECKPOINT_PATH:-${CHECKPOINT_DIR}/yolox_x.pth}"
    URL="${OPENHRI_YOLOX_CHECKPOINT_URL:-https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1.1rc0/yolox_x.pth}"
    EXPECTED_SHAPE="(80, 12, 3, 3)"
    ;;
  yolox-m)
    CHECKPOINT="${OPENHRI_YOLOX_CHECKPOINT_PATH:-${CHECKPOINT_DIR}/yolox_m.pth}"
    URL="${OPENHRI_YOLOX_CHECKPOINT_URL:-https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1.1rc0/yolox_m.pth}"
    EXPECTED_SHAPE="(48, 12, 3, 3)"
    ;;
  *)
    echo "Unsupported OPENHRI_YOLOX_MODEL=${MODEL_NAME}. Use yolox-x or yolox-m." >&2
    exit 2
    ;;
esac

checkpoint_shape() {
  local path="$1"
  python3 - "$path" <<'PY'
import sys
from pathlib import Path

import torch

path = Path(sys.argv[1])
if not path.exists():
    raise SystemExit(2)

ckpt = torch.load(str(path), map_location="cpu")
shape = tuple(ckpt["model"]["backbone.backbone.stem.conv.conv.weight"].shape)
print(shape)
PY
}

mkdir -p "$(dirname "${CHECKPOINT}")"

if [[ -f "${CHECKPOINT}" ]]; then
  shape="$(checkpoint_shape "${CHECKPOINT}" || true)"
  if [[ "${shape}" == "${EXPECTED_SHAPE}" ]]; then
    echo "${MODEL_NAME} checkpoint already valid: ${CHECKPOINT}"
    exit 0
  fi
  echo "Replacing incompatible checkpoint at ${CHECKPOINT}; found shape: ${shape:-unknown}" >&2
  rm -f "${CHECKPOINT}"
fi

curl -L --fail --show-error --output "${CHECKPOINT}" "${URL}"

shape="$(checkpoint_shape "${CHECKPOINT}")"
if [[ "${shape}" != "${EXPECTED_SHAPE}" ]]; then
  echo "Downloaded checkpoint has shape ${shape}, expected ${EXPECTED_SHAPE}" >&2
  exit 1
fi

ls -lh "${CHECKPOINT}"
