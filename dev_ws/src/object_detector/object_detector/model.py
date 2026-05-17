from pathlib import Path

import cv2
import numpy as np

from object_detector.datatypes import DetectionBox


def package_resource_path(package_name, relative_path, override=""):
    from ament_index_python.packages import get_package_share_directory

    if override:
        return Path(override).expanduser()

    candidates = []
    try:
        candidates.append(Path(get_package_share_directory(package_name)) / relative_path)
    except Exception:
        pass

    candidates.append(Path(__file__).resolve().parents[1] / relative_path)
    for path in candidates:
        if path.exists():
            return path
    return candidates[0] if candidates else Path(relative_path)


def clamp_bbox(bbox, width, height):
    x1, y1, x2, y2 = bbox
    return (
        max(0, min(width - 1, int(x1))),
        max(0, min(height - 1, int(y1))),
        max(0, min(width - 1, int(x2))),
        max(0, min(height - 1, int(y2))),
    )


def bbox_area_ratio(x1, y1, x2, y2, width, height):
    return max(0, x2 - x1) * max(0, y2 - y1) / float(width * height)


class ObjectDetectorModel:
    def __init__(
        self,
        ckpt_path,
        class_names_path,
        confidence_threshold,
        min_bbox_area_ratio,
        model_name="yolox-m",
        logger=None,
    ):
        self.ckpt_path = package_resource_path(
            "object_detector", "resource/yolox_m.pth", ckpt_path
        )
        self.class_names_path = package_resource_path(
            "object_detector", "resource/coco.names", class_names_path
        )
        self.confidence_threshold = confidence_threshold
        self.min_bbox_area_ratio = min_bbox_area_ratio
        self.model_name = model_name
        self.logger = logger
        self.classes = []
        self.test_size = (640, 640)
        self.device = "cpu"
        self.model = None
        self.ready = False
        self.status_message = "Waiting for detections."

    def load(self):
        import torch
        from yolox.exp import get_exp

        self.classes = self._load_classes()

        if not self.ckpt_path.exists():
            self.status_message = f"YOLO checkpoint not found: {self.ckpt_path}"
            self._log("error", self.status_message)
            return False

        exp = get_exp(None, self.model_name)
        self.model = exp.get_model()
        self.model.eval()

        ckpt = torch.load(str(self.ckpt_path), map_location="cpu")
        self.model.load_state_dict(ckpt["model"])

        if hasattr(self.model, "head") and hasattr(self.model.head, "decode_in_inference"):
            self.model.head.decode_in_inference = True

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)
        self.test_size = exp.test_size
        self.ready = True
        if self.device == "cuda":
            gpu_name = torch.cuda.get_device_name(0)
            self.status_message = f"YOLOX-M active on CUDA: {gpu_name}."
        else:
            self.status_message = "YOLOX-M active on CPU."
        self._log("info", self.status_message)
        return True

    def detect(self, cv_image):
        import torch
        from yolox.utils import postprocess

        img, ratio = self.preprocess(cv_image, self.test_size)
        tensor_img = torch.from_numpy(img).unsqueeze(0).to(self.device)

        with torch.no_grad():
            outputs = self.model(tensor_img)
            outputs = postprocess(
                outputs,
                len(self.classes),
                self.confidence_threshold,
                0.45,
                class_agnostic=True,
            )

        if not outputs or outputs[0] is None:
            return []

        return self._detections_from_output(cv_image, outputs[0].cpu().numpy(), ratio)

    def preprocess(self, img, input_size):
        h, w = img.shape[:2]
        ratio = min(input_size[0] / h, input_size[1] / w)
        resized_img = cv2.resize(
            img, (int(w * ratio), int(h * ratio)), interpolation=cv2.INTER_LINEAR
        ).astype(np.uint8)
        padded_img = np.full((input_size[0], input_size[1], 3), 114, dtype=np.uint8)
        padded_img[: int(h * ratio), : int(w * ratio)] = resized_img
        padded_img = padded_img.transpose(2, 0, 1)
        return np.ascontiguousarray(padded_img, dtype=np.float32), ratio

    def _detections_from_output(self, cv_image, output, ratio):
        height, width = cv_image.shape[:2]
        bboxes = output[:, 0:4] / ratio
        scores = output[:, 4] * output[:, 5]
        cls_ids = output[:, 6]
        detections = []

        for i, bbox in enumerate(bboxes):
            confidence = float(scores[i])
            if confidence < self.confidence_threshold:
                continue

            class_id = int(cls_ids[i])
            if class_id < 0 or class_id >= len(self.classes):
                continue

            x1, y1, x2, y2 = clamp_bbox(bbox.astype(int), width, height)
            if (
                bbox_area_ratio(x1, y1, x2, y2, width, height)
                < self.min_bbox_area_ratio
            ):
                continue

            detections.append(
                DetectionBox(
                    class_id=class_id,
                    class_name=self.classes[class_id],
                    confidence=confidence,
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                )
            )

        return detections

    def _load_classes(self):
        if not self.class_names_path.exists():
            self._log("warning", f"Class names file not found: {self.class_names_path}")
            return []

        return [
            line.strip()
            for line in self.class_names_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def _log(self, level, message):
        if self.logger is None:
            return
        getattr(self.logger, level)(message)
