#!/bin/bash
set -e

# Source ROS 2 environment
source /opt/ros/${ROS_DISTRO}/setup.bash
source /ws/install/setup.bash

# Set default ROS_DOMAIN_ID if not set
export ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-0}

# Set up DDS settings if cyclonedx.xml exists
if [ -f "/ws/cyclonedx.xml" ]; then
    export CYCLONEDX_URI=file:///ws/cyclonedx.xml
fi

# Execute the command passed to docker run
exec "$@"