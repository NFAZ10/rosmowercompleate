#!/bin/bash

# ROS Mower Docker Helper Script
set -e

# Detect docker compose command (v2 `docker compose` or legacy `docker-compose`)
if docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
elif docker-compose version >/dev/null 2>&1; then
    COMPOSE_CMD="docker-compose"
else
    echo "Docker Compose not found. Install Docker Compose v2 (docker compose) or legacy docker-compose."
    exit 1
fi

# Ensure Docker daemon is running
if ! docker info >/dev/null 2>&1; then
    echo "Starting Docker daemon..."
    ./start-docker.sh
fi

case "$1" in
    "build")
        echo "Building ROS mower Docker image..."
        # Pass image type argument (slim or desktop, defaults to desktop)
        ./build-docker.sh "$2"
        ;;
    "build-slim")
        echo "Building slim ROS mower Docker image..."
        ./build-docker.sh slim
        ;;
    "build-desktop")
        echo "Building desktop ROS mower Docker image..."
        ./build-docker.sh desktop
        ;;
    "run")
        if [ "$2" == "-d" ] || [ "$2" == "--detached" ]; then
            echo "Running ROS mower robot in detached mode..."
            $COMPOSE_CMD up -d rosmower
            # Source workspace and run launch file in detached mode
            docker exec -d rosmower_robot bash -c "source /opt/ros/humble/setup.bash && source /ws/install/setup.bash && ros2 launch rosmower launch_robot.launch.py"
        else
            echo "Running ROS mower robot..."
            $COMPOSE_CMD run --rm --name rosmower_robot rosmower bash -c "source /opt/ros/humble/setup.bash && source /ws/install/setup.bash && ros2 launch rosmower launch_robot.launch.py"
        fi
        ;;
    "dev")
        # Generate unique container name using timestamp
        CONTAINER_NAME="rosmower_dev_$(date +%s)"
        if [ "$2" == "-d" ] || [ "$2" == "--detached" ]; then
            echo "Starting development container in detached mode..."
            echo "Container name: $CONTAINER_NAME"
            $COMPOSE_CMD --profile dev run -d --rm --name "$CONTAINER_NAME" dev bash
        else
            echo "Starting development container..."
            $COMPOSE_CMD --profile dev run --rm --name "$CONTAINER_NAME" dev bash
        fi
        ;;
    "rviz")
        if [ "$2" == "-d" ] || [ "$2" == "--detached" ]; then
            echo "Starting RViz visualization in detached mode..."
            $COMPOSE_CMD --profile gui run -d --rm --name rosmower_rviz2 dev rviz2 -d /ws_dev/rviz_configs/test2.rviz
        else
            echo "Starting RViz visualization..."
            $COMPOSE_CMD --profile gui run --rm --name rosmower_rviz2 dev rviz2 -d /ws_dev/rviz_configs/test2.rviz
        fi
        ;;
    "stat")
        echo "Running status.py in Docker container..."
        $COMPOSE_CMD --profile dev run --rm --name rosmower_status dev python3 /ws_dev/status.py --yaml /ws_dev/sources.yaml
        ;;
    "bridge")
        if [ "$2" == "-d" ] || [ "$2" == "--detached" ]; then
            echo "Starting rosbridge and mode_manager in Docker container (detached)..."
            $COMPOSE_CMD --profile dev run -d --rm --name rosmower_bridge dev bash -c "
                ros2 launch rosbridge_server rosbridge_websocket_launch.xml &
                sleep 3
                ros2 run rosmower mode_manager.py &
                tail -f /dev/null
            "
        else
            echo "Starting rosbridge and mode_manager in Docker container..."
            $COMPOSE_CMD --profile dev run --rm --name rosmower_bridge dev bash -c "
                ros2 launch rosbridge_server rosbridge_websocket_launch.xml &
                ros2 run rosmower mode_manager.py &
                wait
            "
        fi
        ;;
    "launch")
        if [ "$2" == "-d" ] || [ "$2" == "--detached" ]; then
            echo "Running rosbridge in Docker container (detached)..."
            $COMPOSE_CMD --profile dev run -d --rm --name rosmower_launch dev ros2 launch rosmower launch_robot.launch.py
        else
            echo "Running rosbridge in Docker container..."
            $COMPOSE_CMD --profile dev run --rm --name rosmower_launch dev ros2 launch rosmower launch_robot.launch.py
        fi
        ;;
    "launch-noarm")
        if [ "$2" == "-d" ] || [ "$2" == "--detached" ]; then
            echo "Launching robot stack WITHOUT arming motors (detached)..."
            $COMPOSE_CMD --profile dev run -d --rm --name rosmower_launch_noarm dev ros2 launch rosmower launch_robot.launch.py arm:=false
        else
            echo "Launching robot stack WITHOUT arming motors..."
            $COMPOSE_CMD --profile dev run --rm --name rosmower_launch_noarm dev ros2 launch rosmower launch_robot.launch.py arm:=false
        fi
        ;;
    "gps")
        if [ "$2" == "-d" ] || [ "$2" == "--detached" ]; then
            echo "Launching GPS RTK in Docker container (detached)..."
            $COMPOSE_CMD --profile dev run -d --rm --name rosmower_gps dev ros2 launch gps_rtk gps.launch.py
        else
            echo "Launching GPS RTK in Docker container..."
            $COMPOSE_CMD --profile dev run --rm --name rosmower_gps dev ros2 launch gps_rtk gps.launch.py
        fi
        ;;
    "rtk")
        if [ "$2" == "-d" ] || [ "$2" == "--detached" ]; then
            echo "Launching GPS with RTK enabled in Docker container (detached)..."
            $COMPOSE_CMD --profile dev run -d --rm --name rosmower_rtk dev ros2 launch gps_rtk gps.launch.py use_rtk:=true
        else
            echo "Launching GPS with RTK enabled in Docker container..."
            $COMPOSE_CMD --profile dev run --rm --name rosmower_rtk dev ros2 launch gps_rtk gps.launch.py use_rtk:=true
        fi
        ;;
    "rtk-alt")
        if [ "$2" == "-d" ] || [ "$2" == "--detached" ]; then
            echo "Launching GPS with RTK enabled (alternate server) in Docker container (detached)..."
            $COMPOSE_CMD --profile dev run -d --rm --name rosmower_rtk_alt dev ros2 launch gps_rtk gps.launch.py use_rtk:=true ntrip_profile:=alt
        else
            echo "Launching GPS with RTK enabled (alternate server) in Docker container..."
            $COMPOSE_CMD --profile dev run --rm --name rosmower_rtk_alt dev ros2 launch gps_rtk gps.launch.py use_rtk:=true ntrip_profile:=alt
        fi
        ;;
    "zenoh")
        if [ "$2" == "-d" ] || [ "$2" == "--detached" ]; then
            echo "Starting Zenoh router in Docker container (detached)..."
            $COMPOSE_CMD --profile zenoh run -d --rm --name rosmower_zenoh zenoh bash -c "export ZENOH_ROUTER_CONFIG_URI=/ws_dev/zenoh-router.json5 && ros2 run rmw_zenoh_cpp rmw_zenohd"
        else
            echo "Starting Zenoh router in Docker container..."
            $COMPOSE_CMD --profile zenoh run --rm --name rosmower_zenoh zenoh bash -c "export ZENOH_ROUTER_CONFIG_URI=/ws_dev/zenoh-router.json5 && ros2 run rmw_zenoh_cpp rmw_zenohd"
        fi
        ;;
    "recorder"|"zone-recorder")
        if [ "$2" == "-d" ] || [ "$2" == "--detached" ]; then
            echo "Launching Zone Recorder in main container (detached)..."
            docker exec -d rosmower_robot bash -c "source /opt/ros/humble/setup.bash && source /ws/install/setup.bash && ros2 launch rosmower zone_recorder.launch.py"
        else
            echo "Launching Zone Recorder in main container..."
            docker exec -it rosmower_robot bash -c "source /opt/ros/humble/setup.bash && source /ws/install/setup.bash && ros2 launch rosmower zone_recorder.launch.py"
        fi
        ;;
    "rqt")
        if [ "$2" == "-d" ] || [ "$2" == "--detached" ]; then
            echo "Launching RQt in Docker container (detached)..."
            $COMPOSE_CMD --profile gui run -d --rm --name rosmower_rqt dev rqt
        else
            echo "Launching RQt in Docker container..."
            $COMPOSE_CMD --profile gui run --rm --name rosmower_rqt dev rqt
        fi
        ;;
    "teleop")
        echo "Launching teleop keyboard controller in Docker container..."
        echo "Use arrow keys to control the robot (i/k for forward/back, j/l for left/right)"
        $COMPOSE_CMD --profile dev run --rm --name rosmower_teleop dev ros2 run teleop_twist_keyboard teleop_twist_keyboard
        ;;
    "shell")
        echo "Opening shell in running container..."
        docker exec -it rosmower_robot bash
        ;;
    "logs")
        echo "Showing container logs..."
        docker logs rosmower_robot
        ;;
    "stop")
        echo "Stopping all ROS mower containers..."
        docker stop $(docker ps -q --filter "name=rosmower") 2>/dev/null || echo "No running rosmower containers found"
        ;;
    "stop-all")
        echo "Stopping and removing all containers..."
        $COMPOSE_CMD down
        ;;
    "clean")
        echo "Cleaning up containers and images..."
        $COMPOSE_CMD down
        docker rmi rosmower:latest 2>/dev/null || true
        ;;
    "start")
        echo "Starting development container with Terminator terminal..."
        $COMPOSE_CMD --profile dev run --rm --name rosmower_terminator dev terminator
        ;;
    "status")
        echo "Docker status:"
        docker ps -a --filter "name=rosmower"
        echo ""
        echo "Images:"
        docker images | grep rosmower || echo "No rosmower images found"
        ;;
    *)
        echo "ROS Mower Docker Helper"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  build [TYPE]    - Build the Docker image (TYPE: slim or desktop, default: desktop)"
        echo "  build-slim      - Build slim image (ros-core, minimal ROS)"
        echo "  build-desktop   - Build desktop image (with GUI components)"
        echo "  run [-d|--detached] - Run the robot stack (optional: detached mode)"
        echo "  dev [-d|--detached] - Start development container (optional: detached mode)"
        echo "  rviz [-d|--detached] - Start RViz visualization (optional: detached mode)"
        echo "  stat    - Run status.py with sources.yaml in Docker container"
        echo "  bridge [-d|--detached] - Launch rosbridge websocket (optional: detached mode)"
        echo "  launch [-d|--detached] - Launch robot stack (optional: detached mode)"
        echo "  launch-noarm [-d|--detached] - Launch robot stack WITHOUT arming motors"
        echo "  gps [-d|--detached] - Launch GPS RTK (optional: detached mode)"
        echo "  rtk [-d|--detached] - Launch GPS with RTK enabled (default server)"
        echo "  rtk-alt [-d|--detached] - Launch GPS with RTK enabled (alternate server)"
        echo "  zenoh [-d|--detached] - Start Zenoh router (optional: detached mode)"
        echo "  recorder [-d|--detached] - Launch Zone Recorder for boundary recording (optional: detached)"
        echo "  rqt [-d|--detached] - Launch RQt GUI tools (optional: detached mode)"
        echo "  teleop  - Launch teleop keyboard controller"
        echo "  shell   - Open shell in running container"
        echo "  logs    - Show container logs"
        echo "  stop    - Stop all ROS mower containers (keeps containers)"
        echo "  stop-all - Stop and remove all containers"
        echo "  clean   - Clean up containers and images"
        echo "  status  - Show Docker status"
        echo ""
        echo "Examples:"
        echo "  $0 build           # Build desktop image (default)"
        echo "  $0 build slim      # Build slim image"
        echo "  $0 build-slim      # Build slim image"
        echo "  $0 build-desktop   # Build desktop image"
        echo "  $0 run             # Run the robot"
        echo "  $0 run -d          # Run the robot in detached mode"
        echo "  $0 dev             # Development mode"
        echo "  $0 dev -d          # Development mode in detached mode"
        ;;
esac