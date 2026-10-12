"""
HSV 검출 노드: Raw Image를 받아 Mask·Overlay·검출 결과를 토픽으로 발행한다.

  구독  ~/image (기본 /camera/camera/color/image_raw)  sensor_msgs/Image  rgb8 | bgr8
  발행  /vision/mask        sensor_msgs/Image  mono8  (inRange + open·close 결과, 면적 필터 전)
        /vision/overlay     sensor_msgs/Image  bgr8   (후보·탈락·선택 목표·적용값 표시)
        /vision/target      geometry_msgs/PointStamped  (ex, ey, 면적비 / 미검출 0,0,0)
        /vision/detections  std_msgs/String  JSON (후보·탈락 사유·적용 설정·config_rev)

모든 출력은 입력 영상의 header(stamp·frame_id)를 그대로 써서 같은 프레임끼리 맞춰 볼 수 있다.
"""
import cv2
from cv_bridge import CvBridge
from geometry_msgs.msg import PointStamped
from rcl_interfaces.msg import SetParametersResult
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String

from vision_basic.domain.config import ConfigError
from vision_basic.pipeline.detector import Detector
from vision_basic.pipeline.mask import SUPPORTED_ENCODINGS
from vision_basic.pipeline.overlay import render_overlay
from vision_basic.ros import messages, params, qos


class VisionNode(Node):

    def __init__(self) -> None:
        super().__init__('vision_node')
        image_topic = self.declare_parameter('image_topic', '/camera/camera/color/image_raw').value
        params.declare_detection_params(self)
        self.detector = Detector(params.read_config(self))
        self.config_rev = 0               # 설정이 바뀔 때마다 +1 (결과 JSON에 남겨 적용 여부 확인)
        self.seq = 0
        self.bridge = CvBridge()
        self.add_on_set_parameters_callback(self._on_set_params)

        self.create_subscription(Image, image_topic, self._on_image, qos.SENSOR_IN)
        self.mask_pub = self.create_publisher(Image, '/vision/mask', qos.RESULT_OUT)
        self.overlay_pub = self.create_publisher(Image, '/vision/overlay', qos.RESULT_OUT)
        self.target_pub = self.create_publisher(PointStamped, '/vision/target', qos.RESULT_OUT)
        self.det_pub = self.create_publisher(String, '/vision/detections', qos.RESULT_OUT)
        self.get_logger().info(f'input={image_topic} config={self.detector.config.summary()}')

    def _on_set_params(self, changes) -> SetParametersResult:
        if not any(p.name in params.DETECTION_PARAMS for p in changes):
            return SetParametersResult(successful=True)
        try:
            cfg = params.config_with_changes(self, changes)
        except ConfigError as e:
            self.get_logger().warning(f'설정 변경 거부: {e}')
            return SetParametersResult(successful=False, reason=str(e))
        self.detector.reconfigure(cfg)
        self.config_rev += 1
        self.get_logger().info(f'설정 적용 rev={self.config_rev}: {cfg.summary()}')
        return SetParametersResult(successful=True)

    def _on_image(self, msg: Image) -> None:
        if msg.encoding not in SUPPORTED_ENCODINGS:
            self.get_logger().error(f'지원하지 않는 인코딩 {msg.encoding}', throttle_duration_sec=5.0)
            return
        image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
        cfg, rev = self.detector.config, self.config_rev
        res = self.detector.process(image, msg.encoding)
        self.seq += 1

        bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR) if msg.encoding == 'rgb8' else image
        mask_msg = self.bridge.cv2_to_imgmsg(res.mask, encoding='mono8', header=msg.header)
        overlay_msg = self.bridge.cv2_to_imgmsg(render_overlay(bgr, res, cfg), encoding='bgr8',
                                                header=msg.header)
        self.mask_pub.publish(mask_msg)
        self.overlay_pub.publish(overlay_msg)
        self.target_pub.publish(messages.target_msg(msg.header, res))
        self.det_pub.publish(
            messages.detection_msg(msg.header, self.seq, msg.encoding, res, cfg, rev))


def main() -> None:
    rclpy.init()
    node = VisionNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
