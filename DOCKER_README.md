# Docker Setup for ROS Mower Project

## Prerequisites

1. **Docker installed and running** in your WSL environment
   - Use the provided `start-docker.sh` script to start Docker daemon
   - Or follow Docker Desktop WSL integration setup

## Quick Start

### 1. Start Docker (if needed)
```bash
./start-docker.sh
```

### 2. Build the Docker image
```bash
./docker-helper.sh build
```

### 3. Run the robot stack
```bash
./docker-helper.sh run
```

## Available Commands

Use the `docker-helper.sh` script for easy Docker operations:

- `./docker-helper.sh build` - Build the Docker image
- `./docker-helper.sh run` - Run the robot stack
- `./docker-helper.sh dev` - Start development container with shell access
- `./docker-helper.sh rviz` - Start RViz for visualization
- `./docker-helper.sh shell` - Open shell in running container
- `./docker-helper.sh logs` - Show container logs
- `./docker-helper.sh stop` - Stop all containers
- `./docker-helper.sh clean` - Clean up containers and images
- `./docker-helper.sh status` - Show Docker status

## Manual Docker Commands

### Using docker-compose (recommended)
```bash
# Run the robot stack
docker-compose up rosmower

# Run in development mode
docker-compose --profile dev run dev

# Run RViz
docker-compose --profile gui up rviz

# Stop all services
docker-compose down
```

### Using docker run directly
```bash
# Run robot stack
docker run --privileged --network host \
  -v /dev:/dev -v /run/udev:/run/udev:ro \
  -e ROS_DOMAIN_ID=0 \
  rosmower:latest

# Interactive development
docker run -it --privileged --network host \
  -v .:/ws_dev -v /dev:/dev \
  rosmower:latest bash
```

## Built Packages

The Docker image includes:
- **rosmower**: Main robot control package
- **sllidar_ros2**: LIDAR driver
- **serial**: Serial communication library
- All necessary ROS 2 dependencies

## Notes

- The image runs as root for hardware access simplicity
- Device access is configured for `/dev/ttyACM0` and `/dev/ttyUSB0`
- Network mode is set to `host` for ROS 2 communication
- ROS_DOMAIN_ID is set to 0 by default

## Hardware Requirements

- USB/Serial devices for motor controllers and sensors
- LIDAR device (if using)
- Sufficient permissions for device access

## Troubleshooting

1. **Docker daemon not running**: Run `./start-docker.sh`
2. **Permission denied on devices**: Container runs with `--privileged` flag
3. **Build fails**: Check that problematic packages have `COLCON_IGNORE` files
4. **Cannot connect to ROS nodes**: Ensure `network_mode: host` is set