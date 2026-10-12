"""
QoS 프로필.

입력: best-effort 구독은 reliable(bag 재생)·best-effort(카메라) 발행자 모두와 호환된다.
출력: reliable 발행은 reliable(rqt_image_view·ros2 topic echo 기본)·best-effort 구독자 모두와 호환된다.
"""
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy

SENSOR_IN = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                       history=HistoryPolicy.KEEP_LAST, depth=1)
RESULT_OUT = QoSProfile(reliability=ReliabilityPolicy.RELIABLE,
                        history=HistoryPolicy.KEEP_LAST, depth=1)
