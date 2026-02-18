#!/usr/bin/env bash
set -euo pipefail

DEV="${DEV:-/dev/rplidar}"
BAUD="${BAUD:-460800}"
FRAME="${FRAME:-laser_frame}"
MODE="${MODE:-Standard}"

for attempt in 1 2 3 4 5; do
  echo "Attempt $attempt..."
  stty -F "$DEV" sane || true
  stty -F "$DEV" "$BAUD" cs8 -cstopb -parenb -crtscts -ixon -ixoff || true

  if ros2 run sllidar_ros2 sllidar_node --ros-args \
      -p channel_type:=serial \
      -p serial_port:="$DEV" \
      -p serial_baudrate:="$BAUD" \
      -p frame_id:="$FRAME" \
      -p scan_mode:="$MODE"; then
    exit 0
  fi

  echo "Timed out; sleeping 1s..."
  sleep 1
done

echo "Failed after retries."
exit 1
EOF

