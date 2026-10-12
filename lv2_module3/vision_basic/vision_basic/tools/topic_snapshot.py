"""
Raw·Mask·Overlay·검출 결과 토픽을 구독해 같은 stamp 묶음을 파일로 저장한다 (토픽 수신 증거).

  ros2 run vision_basic topic_snapshot --ros-args -p out_dir:=results/exp1 -p label:=exp1_A

저장 파일 (<label>_ 접두사):
  raw.png · mask.png · overlay.png   : 각 토픽에서 받은 이미지 (같은 header.stamp)
  detections.json · target.txt       : 같은 stamp의 검출 결과 메시지
  topics.json                        : 토픽 이름·타입·발행 노드·QoS, 수신 시각
skip 개 묶음을 건너뛴 뒤(설정 변경 직후 프레임 제외) count 개를 저장하고 종료한다.
"""
from datetime import datetime
import json
import os
from typing import Dict, Tuple

import cv2
from cv_bridge import CvBridge
from geometry_msgs.msg import PointStamped
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String

from vision_basic.ros import qos

Key = Tuple[int, int]
PARTS = ('raw', 'mask', 'overlay', 'detections', 'target')


class TopicSnapshot(Node):

    def __init__(self) -> None:
        super().__init__('topic_snapshot')
        dp = self.declare_parameter
        out_dir = dp('out_dir', 'results/snapshots').value
        self.out_dir = os.path.abspath(os.path.expanduser(out_dir))
        self.label = dp('label', 'snapshot').value
        self.count = int(dp('count', 1).value)
        self.skip = int(dp('skip', 3).value)
        self.topics = {
            'raw': dp('raw_topic', '/camera/camera/color/image_raw').value,
            'mask': dp('mask_topic', '/vision/mask').value,
            'overlay': dp('overlay_topic', '/vision/overlay').value,
            'detections': dp('detections_topic', '/vision/detections').value,
            'target': dp('target_topic', '/vision/target').value,
        }
        os.makedirs(self.out_dir, exist_ok=True)
        self.bridge = CvBridge()
        self.pending: Dict[Key, dict] = {}
        self.completed = 0
        self.saved = 0
        self.done = False
        for part in ('raw', 'mask', 'overlay'):
            self.create_subscription(Image, self.topics[part],
                                     lambda m, p=part: self._on_msg(p, m), qos.SENSOR_IN)
        self.create_subscription(String, self.topics['detections'],
                                 lambda m: self._on_msg('detections', m), qos.SENSOR_IN)
        self.create_subscription(PointStamped, self.topics['target'],
                                 lambda m: self._on_msg('target', m), qos.SENSOR_IN)
        self.get_logger().info(
            f'{self.label}: skip {self.skip}, save {self.count} -> {self.out_dir}')

    def _key(self, part: str, msg) -> Key:
        if part == 'detections':
            s = json.loads(msg.data)['stamp']
            return s['sec'], s['nanosec']
        return msg.header.stamp.sec, msg.header.stamp.nanosec

    def _on_msg(self, part: str, msg) -> None:
        if self.done:
            return
        key = self._key(part, msg)
        entry = self.pending.setdefault(key, {})
        entry[part] = msg
        if len(entry) < len(PARTS):
            if len(self.pending) > 60:    # 짝이 안 맞은 오래된 묶음 정리
                for k in sorted(self.pending)[:-30]:
                    del self.pending[k]
            return
        del self.pending[key]
        self.completed += 1
        if self.completed <= self.skip:
            return
        self.saved += 1
        self._save(entry, key)
        if self.saved >= self.count:
            self.done = True

    def _topic_info(self) -> dict:
        info = {}
        for part, topic in self.topics.items():
            pubs = self.get_publishers_info_by_topic(topic)
            info[part] = {
                'topic': topic,
                'types': sorted({p.topic_type for p in pubs}),
                'publishers': sorted({f'{p.node_namespace.rstrip("/")}/{p.node_name}'
                                      for p in pubs}),
                'reliability': sorted({p.qos_profile.reliability.name for p in pubs}),
            }
        return info

    def _save(self, entry: dict, key: Key) -> None:
        suffix = '' if self.count == 1 else f'_{self.saved:02d}'
        base = os.path.join(self.out_dir, f'{self.label}{suffix}')
        raw = entry['raw']
        img = self.bridge.imgmsg_to_cv2(raw, desired_encoding='bgr8')
        cv2.imwrite(base + '_raw.png', img)
        cv2.imwrite(base + '_mask.png', self.bridge.imgmsg_to_cv2(entry['mask'], 'mono8'))
        cv2.imwrite(base + '_overlay.png', self.bridge.imgmsg_to_cv2(entry['overlay'], 'bgr8'))
        det = json.loads(entry['detections'].data)
        with open(base + '_detections.json', 'w', encoding='utf-8') as f:
            json.dump(det, f, ensure_ascii=False, indent=2)
        p = entry['target'].point
        with open(base + '_target.txt', 'w', encoding='utf-8') as f:
            f.write(f'stamp {key[0]}.{key[1]:09d} frame_id {entry["target"].header.frame_id}\n'
                    f'x(ex) {p.x:.4f}  y(ey) {p.y:.4f}  z(area_ratio) {p.z:.5f}\n')
        meta = {
            'label': self.label,
            'received_at': datetime.now().isoformat(timespec='seconds'),
            'stamp': {'sec': key[0], 'nanosec': key[1]},
            'raw': {'width': raw.width, 'height': raw.height, 'encoding': raw.encoding,
                    'frame_id': raw.header.frame_id},
            'topics': self._topic_info(),
        }
        with open(base + '_topics.json', 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        self.get_logger().info(
            f'saved {base}_* stamp {key[0]}.{key[1]:09d} detected={det["detected"]} '
            f'passed={len(det["passed"])} rejected={len(det["rejected"])} config={det["config"]}')


def main() -> None:
    rclpy.init()
    node = TopicSnapshot()
    try:
        while rclpy.ok() and not node.done:
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
