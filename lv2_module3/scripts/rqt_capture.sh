#!/bin/bash
# usage: rqt_capture.sh <topic> <out.png>
# rqt_image_view를 해당 토픽으로 띄워 창 영역(제목 표시줄 포함)을 캡처하고 닫는다.
topic=$1; out=$2
source /opt/ros/lyrical/setup.bash
/opt/ros/lyrical/lib/rqt_image_view/rqt_image_view "$topic" > /dev/null 2>&1 < /dev/null &
pid=$!
geo=""
for _ in $(seq 1 40); do
  sleep 0.5
  geo=$(xwininfo -root -tree | grep '"rqt_image_view__ImageView - rqt": ("mutter-x11-frames"' | head -1 \
        | grep -oE '[0-9]+x[0-9]+\+[0-9]+\+[0-9]+ +\+[0-9]+\+[0-9]+' | head -1)
  [ -n "$geo" ] && break
done
sleep 4   # 이미지가 그려질 시간
python3 - "$geo" "$out" <<'EOF'
import re, sys
from PIL import ImageGrab
w, h, _, _, x, y = map(int, re.findall(r'\d+', sys.argv[1]))
ImageGrab.grab(bbox=(x, y, x + w, y + h), xdisplay=None).save(sys.argv[2])
print('captured', sys.argv[2], w, h, x, y)
EOF
kill -INT $pid 2>/dev/null; sleep 1; kill -9 $pid 2>/dev/null
wait $pid 2>/dev/null
exit 0
