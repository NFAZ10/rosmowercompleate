#!/bin/bash
set -e

# Remove old ROS source lines from .bashrc and add correct ones
sed -i '/source.*ros.*setup.bash/d' /root/.bashrc
sed -i '/export ROS_DOMAIN_ID/d' /root/.bashrc
sed -i '/export RMW_IMPLEMENTATION/d' /root/.bashrc
sed -i '/export ZENOH_ROUTER_CONFIG_URI/d' /root/.bashrc
sed -i '/export CYCLONEDDS_URI/d' /root/.bashrc

# Add correct ROS environment to .bashrc
cat >> /root/.bashrc << EOF
source /opt/ros/\${ROS_DISTRO}/setup.bash
if [ -d "/ws_dev/install" ]; then
    source /ws_dev/install/setup.bash
elif [ -d "/ws/install" ]; then
    source /ws/install/setup.bash
fi
export ROS_DOMAIN_ID=\${ROS_DOMAIN_ID:-0}
export RMW_IMPLEMENTATION=\${RMW_IMPLEMENTATION:-rmw_fastrtps_cpp}
EOF

# Source ROS 2 environment for this shell
source /opt/ros/${ROS_DISTRO}/setup.bash

# Check which workspace to source (dev or production)
if [ -d "/ws_dev/install" ]; then
    source /ws_dev/install/setup.bash
elif [ -d "/ws/install" ]; then
    source /ws/install/setup.bash
fi

# Set default ROS_DOMAIN_ID if not set
export ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-0}

# Set RMW implementation (default to rmw_fastrtps_cpp, override with env var)
export RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION:-rmw_fastrtps_cpp}

# Execute the command passed to docker run
exec "$@"
