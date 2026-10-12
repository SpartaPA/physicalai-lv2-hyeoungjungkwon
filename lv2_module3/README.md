# 모듈 3 — HSV 설정값에 따른 Mask·검출 결과 변화 검증

보고서: [report.md](report.md)

## 코드 출처

| 항목 | 내용 |
|---|---|
| 원본 | 팀 프로젝트 [Lv2_Monglian_Assignment](https://github.com/Lv2-Monglian-Assignment/Lv2_Monglian_Assignment) `lv2_module5/ros2_ws/src/target_detector` (커밋 `cc96e83`, 2026-10-08). 이 중 인지 부분을 직접 작성·담당했다 |
| 이 폴더 | 원본의 HSV 검출 단계(HSV 변환 → inRange → open·close → Contour → 면적 필터 → 목표 선택)만 `vision_basic` 패키지로 재구성했다. 검출 알고리즘과 기준 설정값은 원본과 같다 |
| 바꾼 점 | ① Mask·Overlay·검출 결과를 ROS 2 토픽으로 발행한다(원본은 OpenCV 로컬 창·파일 저장만 했다) ② 탈락 후보와 탈락 사유를 결과 메시지에 남긴다 ③ `ros2 param set`으로 바꾼 값을 검증한 뒤 다음 프레임부터 적용한다 |
| 제외한 것 | 깊이 기반 크기 검증, 여러 물체 번호 유지, 축소 검출, 모터 제어(이번 과제 범위 밖) |

### 패키지 구조

```
vision_basic/
├── config/vision.yaml          # 기준 설정값 (파라미터 이름 = 코드의 파라미터 이름)
├── launch/vision.launch.py     # vision_node + 입력(camera | image | none)
├── vision_basic/
│   ├── domain/                 # 설정·결과 모델 (ROS·OpenCV 의존 없음)
│   │   ├── config.py           #   MaskConfig · CandidateConfig · SelectionConfig + 유효성 검사
│   │   └── model.py            #   Candidate · Rejection · Target · FrameResult
│   ├── pipeline/               # 영상 처리 (OpenCV만, ROS 의존 없음 → 단위 시험 가능)
│   │   ├── mask.py             #   [실험 1 단계] to_hsv · build_mask (inRange → open → close)
│   │   ├── candidates.py       #   [실험 2 단계] extract_candidates · filter_candidates (min_area_px)
│   │   ├── selection.py        #   select_target (largest | priority)
│   │   ├── detector.py         #   한 프레임 처리 묶음 Detector.process()
│   │   └── overlay.py          #   검출 결과 그림 (후보·탈락·목표·적용값 표시)
│   ├── ros/                    # ROS 연결부: 파라미터↔설정, 결과→메시지, QoS
│   ├── nodes/vision_node.py    # 노드 조립 (구독 → Detector → 4개 토픽 발행)
│   └── tools/                  # 실험 보조: 고정 이미지 발행, 토픽 묶음 저장
└── test/test_pipeline.py       # 합성 영상 단위 시험 + ament lint (flake8 · pep257 · mypy · xmllint)
```

의존 방향은 `nodes → ros → pipeline → domain` 한 방향이다. 실험에서 바꾸는 값이 어느 단계에서 쓰이는지 파일 단위로 나뉜다.

## 실행 환경

| 항목 | 값 |
|---|---|
| OS | Ubuntu 24.04 (PC) |
| ROS 2 | Lyrical (`/opt/ros/lyrical`) |
| Python · OpenCV · NumPy | 3.12.3 · 4.6.0 · 1.26.4 |
| 카메라 | Intel RealSense D435, 컬러 640×480 rgb8 30 Hz |
| 입력 | 실험 1·2: D435에서 토픽으로 받아 저장한 한 프레임 `results/input/camera_scene_raw.png`를 고정 입력으로 반복 발행. 목표 없음: D435 실시간 |
| 통신 | `ROS_DOMAIN_ID=31`, `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST` (호출하는 셸에서 설정. `scripts/*.sh`도 이 환경을 그대로 쓴다) |

## 빌드

```bash
mkdir -p ~/m3_ws/src && ln -s ~/Git/physicalai-lv2-hyeoungjungkwon/lv2_module3/vision_basic ~/m3_ws/src/
cd ~/m3_ws && source /opt/ros/lyrical/setup.bash
colcon build --symlink-install --packages-select vision_basic && source install/setup.bash
colcon test --packages-select vision_basic && colcon test-result --verbose   # 단위 시험 + lint
```

## 실행

모터 제어 노드는 실행하지 않는다. 입력은 셋 중 하나를 고른다.

```bash
# (1) 실시간 카메라
ros2 launch vision_basic vision.launch.py source:=camera
# (2) 고정 이미지 반복 발행 (A·B 비교에서 같은 입력 보장)
ros2 launch vision_basic vision.launch.py source:=image image_path:=<png 경로>
# (3) rosbag: 노드만 띄우고 같은 구간을 재생
ros2 launch vision_basic vision.launch.py source:=none
ros2 bag play <bag 폴더> --start-offset <초> --playback-duration <초> --topics /camera/camera/color/image_raw
```

### 발행 토픽

| 자료 | 토픽 | 타입 | 내용 |
|---|---|---|---|
| Raw Image | `/camera/camera/color/image_raw` | `sensor_msgs/msg/Image` | 입력 (카메라 드라이버 · bag · image_file_publisher) |
| Mask | `/vision/mask` | `sensor_msgs/msg/Image` mono8 | inRange + open·close 결과. **면적 필터 전** 단계 |
| 검출 Overlay | `/vision/overlay` | `sensor_msgs/msg/Image` bgr8 | 통과 후보(주황)·탈락 후보(회색)·목표(초록 박스, 빨강 중심)·적용 설정 |
| 검출 수치 | `/vision/target` | `geometry_msgs/msg/PointStamped` | x = ex, y = ey (영상 중심 기준 −1~1, 오른쪽·아래 +), z = 면적비. 미검출이면 0, 0, 0 |
| 검출 상세 | `/vision/detections` | `std_msgs/msg/String` (JSON) | 후보·탈락 사유·mask_pixels·적용 설정·config_rev |

모든 출력은 입력 영상의 `header`(stamp·frame_id)를 그대로 쓴다. 같은 stamp끼리 같은 프레임이다.

### 수신 확인

```bash
ros2 topic list -t
ros2 topic info /vision/mask --verbose
rqt_image_view            # /camera/camera/color/image_raw, /vision/mask, /vision/overlay 각각 선택
ros2 topic echo /vision/target --once
ros2 topic echo /vision/detections --once --field data
```

## 설정값 변경과 적용 확인

파라미터는 노드 시작 때 `config/vision.yaml`에서 읽는다. 실행 중 바꾸려면 아래처럼 한다.

```bash
ros2 param set /vision_node hsv_lower "[102, 60, 40]"     # 실험 1 예: S 하한
ros2 param set /vision_node min_area_px 600.0             # 실험 2 예: 최소 면적
ros2 param get /vision_node min_area_px
```

- 값을 검증한 뒤 다음 프레임부터 적용한다. 범위를 벗어난 값(예: H 하한 > 상한)은 거부하고 기존 값을 유지한다.
- 적용되면 `/vision/detections`의 `config_rev`가 1 늘고 `config`에 새 값이 찍힌다. Overlay 셋째 줄에도 적용값이 표시된다.
- 다른 방법: yaml을 복사해 한 값만 바꾸고 `params_file:=<yaml>`로 노드를 다시 시작한다.

## 증거 저장

`topic_snapshot`이 Raw·Mask·Overlay·검출 결과 토픽을 **구독해서** 같은 stamp 묶음을 저장한다. OpenCV 로컬 창은 쓰지 않는다.

```bash
ros2 run vision_basic topic_snapshot --ros-args -p out_dir:=results/exp1_mask/A -p label:=exp1_A
```

저장되는 파일은 `<label>_raw.png`, `_mask.png`, `_overlay.png`, `_detections.json`, `_target.txt`, `_topics.json`이다. `_topics.json`에는 토픽별 타입·발행 노드·QoS가 들어간다. 설정 변경 직후 프레임을 피하려고 앞의 `skip`(기본 3)개 묶음은 건너뛴다.

## A/B 재현

```bash
export ROS_DOMAIN_ID=31 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
ros2 launch vision_basic vision.launch.py source:=image image_path:=results/input/camera_scene_raw.png rate_hz:=5.0
# 다른 터미널 (lv2_module3 에서)
scripts/run_ab.sh results/exp1_mask exp1 hsv_lower "[102, 120, 40]" "[95, 120, 40]"
scripts/run_ab.sh results/exp2_filter exp2 min_area_px 100.0 4000.0
```

`run_ab.sh`는 A값 적용 → 묶음 저장·rqt 화면 캡처 → B값 적용 → 저장·캡처 → A값 복원 순서로 진행한다. 명령과 응답은 `<폴더>/commands.log`에 남는다.

## 결과 파일 위치

| 위치 | 내용 |
|---|---|
| `results/input/` | 실험 입력 프레임 (D435 토픽 수신 원본·Mask·Overlay·JSON·토픽 정보) |
| `results/topics/` | `ros2 topic list -t` · `topic info --verbose` · `topic hz` · `interface show` · 기준 설정 `topic echo`·`param dump` 출력 (고정 입력 `topic_*`, 실시간 카메라 `camera_topic_*`) |
| `results/exp1_mask/{A,B}/` | 실험 1 A·B 묶음: 토픽 수신 `*_raw/_mask/_overlay.png`, rqt_image_view 화면 `*_rqt_*.png`, `*_detections.json`, `*_target.txt`, `*_echo_target.txt`, `*_topics.json`. 명령 기록 `commands.log` |
| `results/exp2_filter/{A,B}/` | 실험 2 A·B 묶음 (구성 같음) |
| `results/no_target/` | 목표 없음 입력 확인: 연속 3묶음, rqt 화면, `/vision/target` 수신값, 수신 주기, 노드 실행 로그 |
