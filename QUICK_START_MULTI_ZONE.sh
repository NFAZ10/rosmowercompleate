#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
#  MULTI-ZONE ROUTE MANAGEMENT - QUICK START SCRIPT
# ═══════════════════════════════════════════════════════════════════════════
#
#  This script provides quick access to all multi-zone system commands
#
# ═══════════════════════════════════════════════════════════════════════════

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${CYAN}"
    echo "═══════════════════════════════════════════════════════════════════════════"
    echo "  $1"
    echo "═══════════════════════════════════════════════════════════════════════════"
    echo -e "${NC}"
}

print_section() {
    echo -e "${BLUE}━━━ $1 ━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_info() {
    echo -e "${CYAN}ℹ${NC} $1"
}

print_command() {
    echo -e "${YELLOW}$${NC} $1"
}

show_menu() {
    print_header "MULTI-ZONE ROUTE MANAGEMENT - QUICK START"
    
    echo "Choose an option:"
    echo ""
    echo "  ${GREEN}BUILD & DEPLOY${NC}"
    echo "    1) Build multi-zone system (compile messages & nodes)"
    echo "    2) Setup storage directories"
    echo "    3) Verify installation (34 checks)"
    echo "    4) Full deploy (build + setup + verify)"
    echo ""
    echo "  ${CYAN}LAUNCH & RUN${NC}"
    echo "    5) Launch route management system"
    echo "    6) Start web server"
    echo "    7) Launch in Docker"
    echo "    8) Full startup (launch all components)"
    echo ""
    echo "  ${YELLOW}TESTING & VALIDATION${NC}"
    echo "    9) Run comprehensive tests"
    echo "   10) Check system status"
    echo "   11) View ROS2 topics/services"
    echo "   12) Monitor route recording"
    echo ""
    echo "  ${BLUE}DOCUMENTATION${NC}"
    echo "   13) Show quick start guide"
    echo "   14) Show deployment card"
    echo "   15) Show file manifest"
    echo "   16) Open all documentation"
    echo ""
    echo "  ${RED}UTILITIES${NC}"
    echo "   17) View route files"
    echo "   18) View zone files"
    echo "   19) View logs"
    echo "   20) Clean build files"
    echo ""
    echo "    0) Exit"
    echo ""
    read -p "Enter choice [0-20]: " choice
    
    case $choice in
        1) build_system ;;
        2) setup_storage ;;
        3) verify_installation ;;
        4) full_deploy ;;
        5) launch_system ;;
        6) start_web_server ;;
        7) launch_docker ;;
        8) full_startup ;;
        9) run_tests ;;
        10) check_status ;;
        11) view_ros_interfaces ;;
        12) monitor_recording ;;
        13) show_quick_start ;;
        14) show_deployment_card ;;
        15) show_file_manifest ;;
        16) open_documentation ;;
        17) view_routes ;;
        18) view_zones ;;
        19) view_logs ;;
        20) clean_build ;;
        0) exit 0 ;;
        *) echo "Invalid option"; sleep 1; show_menu ;;
    esac
}

build_system() {
    print_section "Building Multi-Zone System"
    ./build-multi-zone.sh
    print_success "Build complete!"
    read -p "Press Enter to continue..."
    show_menu
}

setup_storage() {
    print_section "Setting Up Storage Directories"
    ./setup_multi_zone_storage.sh
    print_success "Storage setup complete!"
    read -p "Press Enter to continue..."
    show_menu
}

verify_installation() {
    print_section "Verifying Installation"
    ./verify-multi-zone.sh
    read -p "Press Enter to continue..."
    show_menu
}

full_deploy() {
    print_section "Full Deployment (Build + Setup + Verify)"
    ./build-multi-zone.sh
    ./setup_multi_zone_storage.sh
    ./verify-multi-zone.sh
    print_success "Full deployment complete!"
    print_info "Next: Launch system with option 5 or 8"
    read -p "Press Enter to continue..."
    show_menu
}

launch_system() {
    print_section "Launching Route Management System"
    print_info "Make sure to source ROS2 workspace first!"
    print_command "source install/setup.bash"
    print_command "ros2 launch rosmower zone_and_route_management.launch.py"
    echo ""
    read -p "Press Enter to launch (Ctrl+C to cancel)..."
    source install/setup.bash 2>/dev/null || true
    ros2 launch rosmower zone_and_route_management.launch.py
}

start_web_server() {
    print_section "Starting Web Server"
    print_command "./start-web-server.sh"
    print_info "Web UI will be available at: http://localhost:8080/routes"
    echo ""
    read -p "Press Enter to start (Ctrl+C to cancel)..."
    ./start-web-server.sh
}

launch_docker() {
    print_section "Launching in Docker"
    print_command "docker-compose up -d"
    print_command "docker exec -it rosmower bash"
    echo ""
    read -p "Press Enter to launch (Ctrl+C to cancel)..."
    docker-compose up -d
    echo ""
    print_success "Docker containers started"
    print_info "To enter container: docker exec -it rosmower bash"
    print_info "Inside container, run: ros2 launch rosmower zone_and_route_management.launch.py"
    read -p "Press Enter to continue..."
    show_menu
}

full_startup() {
    print_section "Full Startup (All Components)"
    print_info "This will launch ROS2 system and web server"
    echo ""
    print_info "Starting in background..."
    
    # Start in background (would need tmux or screen for real implementation)
    print_info "Option 1: Manual startup in separate terminals"
    echo "  Terminal 1: ros2 launch rosmower zone_and_route_management.launch.py"
    echo "  Terminal 2: ./start-web-server.sh"
    echo ""
    print_info "Option 2: Use Docker"
    echo "  docker-compose up -d"
    echo "  docker exec -it rosmower bash"
    echo "  ros2 launch rosmower zone_and_route_management.launch.py"
    
    read -p "Press Enter to continue..."
    show_menu
}

run_tests() {
    print_section "Running Comprehensive Tests"
    ./test_multi_zone_routes.sh
    read -p "Press Enter to continue..."
    show_menu
}

check_status() {
    print_section "System Status"
    
    echo "Checking ROS2 nodes..."
    ros2 node list 2>/dev/null | grep -E "(route_manager|route_planner|zone_manager)" || echo "  No nodes running"
    
    echo ""
    echo "Checking files..."
    [ -d "routes" ] && echo "  ✓ routes/ directory exists" || echo "  ✗ routes/ directory missing"
    [ -d "zones" ] && echo "  ✓ zones/ directory exists" || echo "  ✗ zones/ directory missing"
    
    echo ""
    echo "Route count: $(ls -1 routes/*.yaml 2>/dev/null | wc -l)"
    echo "Zone count: $(ls -1 zones/*.yaml 2>/dev/null | wc -l)"
    
    read -p "Press Enter to continue..."
    show_menu
}

view_ros_interfaces() {
    print_section "ROS2 Topics & Services"
    
    echo "Topics:"
    ros2 topic list 2>/dev/null | grep -E "(route|zone)" || echo "  ROS2 not running"
    
    echo ""
    echo "Services:"
    ros2 service list 2>/dev/null | grep -E "(route|zone)" || echo "  ROS2 not running"
    
    echo ""
    echo "Nodes:"
    ros2 node list 2>/dev/null | grep -E "(route|zone)" || echo "  ROS2 not running"
    
    read -p "Press Enter to continue..."
    show_menu
}

monitor_recording() {
    print_section "Monitoring Route Recording"
    print_command "ros2 topic echo /route/recording/status"
    echo ""
    read -p "Press Enter to monitor (Ctrl+C to stop)..."
    ros2 topic echo /route/recording/status
}

show_quick_start() {
    print_section "Quick Start Guide"
    cat 00-MULTI-ZONE-START-HERE.md | head -100
    echo ""
    print_info "Full guide: cat 00-MULTI-ZONE-START-HERE.md"
    read -p "Press Enter to continue..."
    show_menu
}

show_deployment_card() {
    print_section "Deployment Card"
    cat DEPLOY_MULTI_ZONE.txt
    read -p "Press Enter to continue..."
    show_menu
}

show_file_manifest() {
    print_section "File Manifest"
    cat MULTI_ZONE_FILES_LIST.txt | head -100
    echo ""
    print_info "Full manifest: cat MULTI_ZONE_FILES_LIST.txt"
    read -p "Press Enter to continue..."
    show_menu
}

open_documentation() {
    print_section "Documentation Files"
    
    echo "Available documentation:"
    echo "  1. 00-MULTI-ZONE-START-HERE.md       - Entry point"
    echo "  2. MULTI_ZONE_GUIDE.md               - System overview"
    echo "  3. ROUTE_RECORDING_GUIDE.md          - User tutorial"
    echo "  4. ROUTE_BEST_PRACTICES.md           - GPS tips"
    echo "  5. ZONE_GRAPH_EXPLAINED.md           - Graph theory"
    echo "  6. MULTI_ZONE_DEPLOYMENT.md          - Deployment"
    echo "  7. MULTI_ZONE_QUICK_REFERENCE.md     - Commands"
    echo "  8. MULTI_ZONE_SYSTEM_SUMMARY.md      - Technical"
    echo ""
    read -p "Enter number to view (0 to skip): " doc_choice
    
    case $doc_choice in
        1) less 00-MULTI-ZONE-START-HERE.md ;;
        2) less MULTI_ZONE_GUIDE.md ;;
        3) less ROUTE_RECORDING_GUIDE.md ;;
        4) less ROUTE_BEST_PRACTICES.md ;;
        5) less ZONE_GRAPH_EXPLAINED.md ;;
        6) less MULTI_ZONE_DEPLOYMENT.md ;;
        7) less MULTI_ZONE_QUICK_REFERENCE.md ;;
        8) less MULTI_ZONE_SYSTEM_SUMMARY.md ;;
        0) ;;
        *) echo "Invalid option" ;;
    esac
    
    show_menu
}

view_routes() {
    print_section "Route Files"
    echo "Routes in routes/ directory:"
    ls -lh routes/*.yaml 2>/dev/null || echo "No route files found"
    echo ""
    read -p "Enter route filename to view (or Enter to skip): " route_file
    if [ -n "$route_file" ]; then
        cat "routes/$route_file"
    fi
    read -p "Press Enter to continue..."
    show_menu
}

view_zones() {
    print_section "Zone Files"
    echo "Zones in zones/ directory:"
    ls -lh zones/*.yaml 2>/dev/null || echo "No zone files found"
    echo ""
    read -p "Enter zone filename to view (or Enter to skip): " zone_file
    if [ -n "$zone_file" ]; then
        cat "zones/$zone_file"
    fi
    read -p "Press Enter to continue..."
    show_menu
}

view_logs() {
    print_section "Viewing Logs"
    
    echo "Available log options:"
    echo "  1. ROS2 node logs (rosout)"
    echo "  2. Web server logs"
    echo "  3. Docker logs"
    echo ""
    read -p "Enter choice [1-3]: " log_choice
    
    case $log_choice in
        1) ros2 topic echo /rosout | grep -E "(route|zone)" ;;
        2) tail -f logs/web_server.log 2>/dev/null || echo "No web server log found" ;;
        3) docker logs rosmower --tail 50 ;;
        *) echo "Invalid option" ;;
    esac
    
    read -p "Press Enter to continue..."
    show_menu
}

clean_build() {
    print_section "Cleaning Build Files"
    print_info "This will remove build/, install/, and log/ directories"
    read -p "Are you sure? [y/N]: " confirm
    
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        rm -rf build/ install/ log/
        print_success "Build files cleaned"
        print_info "Run option 1 to rebuild"
    else
        print_info "Clean cancelled"
    fi
    
    read -p "Press Enter to continue..."
    show_menu
}

# Main execution
cd "$(dirname "$0")"
show_menu
