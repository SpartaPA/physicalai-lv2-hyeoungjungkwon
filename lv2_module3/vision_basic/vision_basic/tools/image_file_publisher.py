"""
고정 이미지 파일을 Raw Image 토픽으로 반복 발행한다 (A·B 비교의 동일 입력용).

  ros2 run vision_basic image_file_publisher --ros-args -p image_path:=<png> -p rate_hz:=5.0

파일은 BGR로 읽고, encoding 파라미터(rgb8 기본, D435 컬러 토픽과 같음)에 맞춰 변환해 보낸다.
stamp는 발행 시각이고 픽셀은 매번 같다. 입력 동일성은 결과 JSON의 seq·stamp와 파일 경로로 기록한다.
"""
import cv2
from cv_bridge import CvBridge
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import Image

from vision_basic.ros import qos


class ImageFilePublisher(Node):

    def __init__(self) -> None:
        super().__init__('image_file_publisher')
        path = self.declare_parameter('image_path', '').value
        topic = self.declare_parameter('topic', '/camera/camera/color/image_raw').value
        self.encoding = self.declare_parameter('encoding', 'rgb8').value
        self.frame_id = self.declare_parameter('frame_id', 'camera_color_optical_frame').value
        rate = float(self.declare_parameter('rate_hz', 5.0).value)
        if self.encoding not in ('rgb8', 'bgr8'):
            raise ValueError(f'encoding은 rgb8 또는 bgr8: {self.encoding}')
        bgr = cv2.imread(path, cv2.IMREAD_COLOR)
        if bgr is None:
            raise FileNotFoundError(f'이미지를 읽을 수 없습니다: {path!r}')
        img = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB) if self.encoding == 'rgb8' else bgr
        self.msg = CvBridge().cv2_to_imgmsg(img, encoding=self.encoding)
        self.msg.header.frame_id = self.frame_id
        self.pub = self.create_publisher(Image, topic, qos.RESULT_OUT)
        self.create_timer(1.0 / rate, self._tick)
        self.get_logger().info(
            f'{path} ({img.shape[1]}x{img.shape[0]} {self.encoding}) -> {topic} @ {rate} Hz')

    def _tick(self) -> None:
        self.msg.header.stamp = self.get_clock().now().to_msg()
        self.pub.publish(self.msg)


def main() -> None:
    rclpy.init()
    node = ImageFilePublisher()
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
