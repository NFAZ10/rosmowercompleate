#!/bin/bash
# Quick start script for ROS Mower Web Server (without systemd)

cd /mnt/nova_ssd/rosmowercompleate

PORT="${ROSMOWER_WEB_PORT:-80}"
case "$PORT" in
    ''|*[!0-9]*)
        echo "Invalid ROSMOWER_WEB_PORT: $PORT" >&2
        exit 1
        ;;
esac

PORT_SUFFIX=""
if [ "$PORT" -ne 80 ]; then
    PORT_SUFFIX=":$PORT"
fi

echo "========================================"
echo "Starting ROS Mower Web Server"
echo "========================================"
echo ""
echo "Installing dependencies if needed..."
pip3 install -q flask flask-cors 2>/dev/null || true

echo ""
echo "Starting web server on port ${PORT}..."
echo "Access the control panel at:"
echo "  http://localhost${PORT_SUFFIX}"
echo "  http://$(hostname -I | awk '{print $1}')${PORT_SUFFIX}"
echo ""
echo "Press Ctrl+C to stop"
echo "========================================"
echo ""

if [ "$PORT" -lt 1024 ] && [ "$(id -u)" -ne 0 ]; then
    echo "Port ${PORT} requires elevated privileges. Re-running with sudo..."
    exec sudo env ROSMOWER_WEB_PORT="$PORT" python3 web_server.py
fi

exec env ROSMOWER_WEB_PORT="$PORT" python3 web_server.py
