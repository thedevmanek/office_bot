import time
import cv2
import torch
import numpy as np

from yolox.exp import get_exp
from yolox.utils import postprocess
from yolox.data.data_augment import ValTransform

# Configuration
CKPT_PATH = "/home/thedevmanek/office_bot/dev_ws/src/object_detector/resource/yolox_m.pth"
CAM_INDEX = 2

# Standard COCO Labels
COCO_CLASSES = (
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat", "traffic light",
    "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow",
    "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
    "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove", "skateboard", "surfboard",
    "tennis racket", "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
    "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse", "remote", "keyboard", 
    "cell phone", "microwave", "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase", 
    "scissors", "teddy bear", "hair drier", "toothbrush"
)

def main():
    exp = get_exp(exp_name="yolox-m")
    model = exp.get_model()
    model.eval()

    ckpt = torch.load(CKPT_PATH, map_location="cpu")
    model.load_state_dict(ckpt["model"])

    if hasattr(model, "head") and hasattr(model.head, "decode_in_inference"):
        model.head.decode_in_inference = True

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    
    preproc = ValTransform(legacy=False)

    # 1. 4K Camera Setup (3840 x 2160)
    cap = cv2.VideoCapture(CAM_INDEX, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 2160)
    
    if not cap.isOpened():
        raise RuntimeError(f"❌ Could not open camera index {CAM_INDEX}")

    test_size = exp.test_size 
    prev_time = time.time()

    while True:
        ret, frame = cap.read()
        if not ret: break

        # Manual Ratio Calculation for 4K
        img_h, img_w = frame.shape[:2]
        actual_ratio = min(test_size[0] / img_h, test_size[1] / img_w)

        img, _ = preproc(frame, None, test_size)
        img_tensor = torch.from_numpy(img).unsqueeze(0).float().to(device)

        with torch.no_grad():
            outputs = model(img_tensor)
            outputs = postprocess(outputs, exp.num_classes, 0.7, 0.45, class_agnostic=True)

        if outputs is not None and outputs[0] is not None:
            output = outputs[0].cpu()
            bboxes = (output[:, 0:4].clone()) / actual_ratio
            scores = output[:, 4] * output[:, 5]
            cls_ids = output[:, 6].int()

            for i in range(len(bboxes)):
                box = bboxes[i].numpy()
                if np.isnan(box).any() or np.isinf(box).any(): continue

                x1, y1, x2, y2 = box.astype(int)
                score = scores[i].item()
                cls_id = cls_ids[i].item()

                if score < 0.3: continue

                # Scale drawing thickness for 4K (Thicker lines, larger text)
                thickness = 4
                font_scale = 1.2
                color = (0, 255, 0)
                
                label_text = f"{COCO_CLASSES[cls_id]}: {score:.2f}"
                
                # Draw Box
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
                
                # Draw Label Background (for better visibility at high res)
                (t_w, t_h), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 2)
                cv2.rectangle(frame, (x1, y1 - t_h - 10), (x1 + t_w, y1), color, -1)
                cv2.putText(frame, label_text, (x1, y1 - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), 2)

        # FPS calculation
        curr_time = time.time()
        fps = 1.0 / (curr_time - prev_time)
        prev_time = curr_time
        cv2.putText(frame, f"FPS: {fps:.2f}", (50, 80), 
                    cv2.FONT_HERSHEY_SIMPLEX, 2.0, (255, 0, 0), 4)

        # Use WINDOW_NORMAL to allow resizing the 4K window to fit your monitor
        cv2.namedWindow("YOLOX 4K", cv2.WINDOW_NORMAL)
        cv2.imshow("YOLOX 4K", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()