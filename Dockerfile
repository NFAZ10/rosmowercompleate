# Multi-stage Docker build for ROS 2 rosmower workspace
FROM osrf/ros:humble-desktop-full-jammy AS base

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV ROS_DISTRO=humble
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-colcon-common-extensions \
    python3-rosdep \
    python3-vcstool \
    git \
    wget \
    curl \
    build-essential \
    cmake \
    libeigen3-dev \
    libgeographic-dev \
    python3-matplotlib \
    python3-serial \
    python3-yaml \
    python3-requests \
    python3-scipy \
    python3-numpy \
    udev \
    && rm -rf /var/lib/apt/lists/*

# Install additional ROS 2 packages that might be needed
RUN apt-get update && apt-get install -y \
    ros-${ROS_DISTRO}-joint-state-publisher \
    ros-${ROS_DISTRO}-joint-state-publisher-gui \
    ros-${ROS_DISTRO}-robot-state-publisher \
    ros-${ROS_DISTRO}-xacro \
    ros-${ROS_DISTRO}-tf2-tools \
    ros-${ROS_DISTRO}-robot-localization \
    ros-${ROS_DISTRO}-twist-mux \
    ros-${ROS_DISTRO}-rosbridge-server \
    ros-${ROS_DISTRO}-mavros \
    ros-${ROS_DISTRO}-mavros-extras \
    ros-${ROS_DISTRO}-mavros-msgs \
    ros-${ROS_DISTRO}-geographic-msgs \
    ros-${ROS_DISTRO}-sensor-msgs \
    ros-${ROS_DISTRO}-nav-msgs \
    ros-${ROS_DISTRO}-geometry-msgs \
    ros-${ROS_DISTRO}-std-msgs \
    ros-${ROS_DISTRO}-std-srvs \
    && rm -rf /var/lib/apt/lists/*

# Install GeographicLib datasets for MAVROS
RUN wget https://raw.githubusercontent.com/mavlink/mavros/master/mavros/scripts/install_geographiclib_datasets.sh
RUN bash ./install_geographiclib_datasets.sh && rm ./install_geographiclib_datasets.sh

# Create workspace
WORKDIR /ws

# Copy source code (excluding build artifacts)
COPY src/ src/
COPY cyclonedds.xml ./
COPY sources.yaml ./

# Initialize rosdep and install dependencies
RUN rosdep init || true
RUN rosdep update
RUN rosdep install --from-paths src --ignore-src -r -y

# Build the workspace
RUN . /opt/ros/${ROS_DISTRO}/setup.sh && \
    colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release

# Setup environment
RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> ~/.bashrc
RUN echo "source /ws/install/setup.bash" >> ~/.bashrc

# Create entrypoint script
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Runtime stage
FROM base AS runtime

# Set up user to avoid running as root
ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd -g ${GROUP_ID} ros && \
    useradd -u ${USER_ID} -g ${GROUP_ID} -m -s /bin/bash ros && \
    usermod -aG dialout ros

# Copy built workspace
COPY --from=base /ws /ws
COPY --from=base /entrypoint.sh /entrypoint.sh

# Change ownership to ros user
RUN chown -R ros:ros /ws

USER ros
WORKDIR /ws

# Set up environment for ros user
RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> ~/.bashrc
RUN echo "source /ws/install/setup.bash" >> ~/.bashrc
RUN echo "export ROS_DOMAIN_ID=0" >> ~/.bashrc

ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]