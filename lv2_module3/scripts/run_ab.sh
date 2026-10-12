#!/bin/bash
# A/B 한 쌍 실행: 파라미터를 A로 맞춰 묶음 저장 -> B로 바꿔 저장 -> A로 되돌림.
# usage: run_ab.sh <실험 폴더> <라벨 접두사> <파라미터> <A값> <B값>
#   예) run_ab.sh results/exp1_mask exp1 hsv_lower "[102, 120, 40]" "[95, 120, 40]"
# 전제: vision_node가 실행 중이고 ROS_DOMAIN_ID 등 환경이 같다 (호출하는 셸에서 설정). 결과: <폴더>/{A,B}/ 와 <폴더>/commands.log
set -u
dir=$1; label=$2; param=$3; a=$4; b=$5
here=$(cd "$(dirname "$0")" && pwd)
export PYTHONUNBUFFERED=1
log=$dir/commands.log
mkdir -p "$dir/A" "$dir/B"
run() { echo "\$ $*" | tee -a "$log"; "$@" 2>&1 | tee -a "$log"; }

echo "# $(date -Iseconds) $label: $param A=$a B=$b (ROS_DOMAIN_ID=$ROS_DOMAIN_ID)" >> "$log"
for side in A B; do
  val=$a; [ $side = B ] && val=$b
  run ros2 param set /vision_node "$param" "$val"
  run ros2 param get /vision_node "$param"
  run timeout 30 ros2 run vision_basic topic_snapshot --ros-args \
      -p out_dir:="$dir/$side" -p label:="${label}_$side" -p skip:=3
  for t in /camera/camera/color/image_raw /vision/mask /vision/overlay; do
    "$here/rqt_capture.sh" "$t" "$dir/$side/${label}_${side}_rqt_$(basename "$t").png" | tee -a "$log"
  done
  { echo "\$ ros2 topic echo /vision/target --once"; timeout 15 ros2 topic echo /vision/target --once; } \
      > "$dir/$side/${label}_${side}_echo_target.txt" 2>&1
done
run ros2 param set /vision_node "$param" "$a"   # 기준값으로 복원
