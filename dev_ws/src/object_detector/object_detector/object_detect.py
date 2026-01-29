import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from visualization_msgs.msg import Marker, MarkerArray
from geometry_msgs.msg import PointStamped
from cv_bridge import CvBridge
import cv2
import numpy as np
import torch
import tf2_ros
from tf2_geometry_msgs import do_transform_point
from yolox.exp import get_exp
from yolox.utils import postprocess

class ObjectDetectionNode(Node):
    def __init__(self):
        super().__init__('object_detection_node')
        self.bridge = CvBridge()

        # Subscribers
        self.image_sub = self.create_subscription(
            Image, '/camera/image_raw', self.image_callback, 10)
        
        # Publishers
        self.marker_pub = self.create_publisher(MarkerArray, '/detected_objects_markers', 10)
        self.image_pub = self.create_publisher(Image, '/camera/image_detections', 10)

        # TF setup
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        # Model Loading
        exp = get_exp(None, "yolox-m")
        self.model = exp.get_model()
        self.model.eval()

        ckpt = torch.load("/home/thedevmanek/office_bot/dev_ws/src/object_detector/resource/yolox_m.pth", map_location="cpu")
        self.model.load_state_dict(ckpt["model"])
        
        if hasattr(self.model, "head") and hasattr(self.model.head, "decode_in_inference"):
            self.model.head.decode_in_inference = True

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)
        self.get_logger().info(f"YOLOX-M active on {self.device}. Publishing to /camera/image_detections")

        self.classes = [line.strip() for line in open("/home/thedevmanek/office_bot/dev_ws/src/object_detector/resource/coco.names", "r").readlines()]
        self.test_size = exp.test_size 

    def preprocess(self, img, input_size):
        h, w = img.shape[:2]
        r = min(input_size[0] / h, input_size[1] / w)
        resized_img = cv2.resize(img, (int(w * r), int(h * r)), interpolation=cv2.INTER_LINEAR).astype(np.uint8)
        padded_img = np.full((input_size[0], input_size[1], 3), 114, dtype=np.uint8)
        padded_img[:int(h * r), :int(w * r)] = resized_img
        padded_img = padded_img.transpose(2, 0, 1)
        padded_img = np.ascontiguousarray(padded_img, dtype=np.float32)
        return padded_img, r

    def image_callback(self, msg):
        # Convert ROS Image to OpenCV
        cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        h, w = cv_image.shape[:2]

        # Inference
        img, ratio = self.preprocess(cv_image, self.test_size)
        tensor_img = torch.from_numpy(img).unsqueeze(0).to(self.device)

        with torch.no_grad():
            outputs = self.model(tensor_img)
            outputs = postprocess(outputs, len(self.classes), 0.5, 0.45, class_agnostic=True)

        marker_array = MarkerArray()
        id_counter = 0

        if outputs[0] is not None:
            output = outputs[0].cpu().numpy()
            bboxes = output[:, 0:4] / ratio
            scores = output[:, 4] * output[:, 5]
            cls_ids = output[:, 6]

            for i in range(len(bboxes)):
                x1, y1, x2, y2 = bboxes[i].astype(int)
                conf = scores[i]
                class_id = int(cls_ids[i])
                
                # Draw on the image
                label = f"{self.classes[class_id]}: {conf:.2f}"
                cv2.rectangle(cv_image, (x1, y1), (x2, y2), (0, 255, 0), 3)
                cv2.putText(cv_image, label, (x1, max(0, y1 - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

                # 3D Logic (Simplified marker placement)
                pt = PointStamped()
                pt.header.stamp = msg.header.stamp
                pt.header.frame_id = msg.header.frame_id
                pt.point.x = 2.0 
                pt.point.y = -((x1 + x2) / 2.0 / w - 0.5) * 2.0
                pt.point.z = -((y1 + y2) / 2.0 / h - 0.5) * 1.5

                try:
                    transform = self.tf_buffer.lookup_transform('map', pt.header.frame_id, rclpy.time.Time())
                    map_point = do_transform_point(pt, transform)
                    
                    marker = Marker()
                    marker.header.frame_id = 'map'
                    marker.header.stamp = self.get_clock().now().to_msg()
                    marker.type = Marker.TEXT_VIEW_FACING
                    marker.text = self.classes[class_id]
                    marker.id = id_counter
                    marker.pose.position = map_point.point
                    marker.scale.z = 0.2
                    marker.color.a = 1.0
                    marker.color.r = 1.0
                    marker.lifetime = rclpy.duration.Duration(seconds=0.1).to_msg()
                    marker_array.markers.append(marker)
                    id_counter += 1
                except:
                    continue

        # --- PUBLISH THE OUTPUT IMAGE ---
        # Convert back to ROS Image message
        detection_msg = self.bridge.cv2_to_imgmsg(cv_image, encoding="bgr8")
        detection_msg.header = msg.header  # Keep original timestamp and frame_id
        self.image_pub.publish(detection_msg)

        # Publish Markers
        self.marker_pub.publish(marker_array)

def main(args=None):
    rclpy.init(args=args)
    node = ObjectDetectionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    main()