#include "vesc_driver/vesc_interface.hpp"
#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/twist.hpp>
#include <sensor_msgs/msg/joint_state.hpp>
#include <nav_msgs/msg/odometry.hpp>
#include <tf2/LinearMath/Quaternion.h>
#include <tf2_geometry_msgs/tf2_geometry_msgs.hpp>
#include <cmath>

namespace vesc_driver {

/**
 * @brief ROS 2 VESC Driver Node for Differential Drive
 * 
 * Subscribes to /cmd_vel and converts to left/right wheel RPM
 * Publishes JointState using VESC ERPM feedback
 * Supports dual VESC configuration over CAN bus
 */
class VescDriverNode : public rclcpp::Node {
public:
  VescDriverNode() : Node("vesc_driver_node") {
    // Declare parameters
    declare_parameter("serial_port", "/dev/ttyACM0");
    declare_parameter("baudrate", 115200);
    declare_parameter("wheel_radius", 0.0875);  // meters (hoverboard wheel ~175mm diameter)
    declare_parameter("wheel_separation", 0.52);  // meters
    declare_parameter("pole_pairs", 15);  // Hoverboard motors typically 15 pole pairs
    declare_parameter("left_vesc_can_id", 0);  // VESC ID 0 (connected via USB)
    declare_parameter("right_vesc_can_id", 47);  // VESC ID 1 (connected via CAN)
    declare_parameter("invert_left_motor", false);
    declare_parameter("invert_right_motor", false);
    declare_parameter("max_rpm", 3000);  // Maximum ERPM (safe limit)
    declare_parameter("control_rate", 50.0);  // Hz
    declare_parameter("telemetry_rate", 10.0);  // Hz
    declare_parameter("publish_odom", true);
    declare_parameter("odom_frame_id", "odom");
    declare_parameter("base_frame_id", "base_link");

    // Get parameters
    serial_port_ = get_parameter("serial_port").as_string();
    baudrate_ = get_parameter("baudrate").as_int();
    wheel_radius_ = get_parameter("wheel_radius").as_double();
    wheel_separation_ = get_parameter("wheel_separation").as_double();
    pole_pairs_ = get_parameter("pole_pairs").as_int();
    left_can_id_ = get_parameter("left_vesc_can_id").as_int();
    right_can_id_ = get_parameter("right_vesc_can_id").as_int();
    invert_left_motor_ = get_parameter("invert_left_motor").as_bool();
    invert_right_motor_ = get_parameter("invert_right_motor").as_bool();
    max_rpm_ = get_parameter("max_rpm").as_int();
    control_rate_ = get_parameter("control_rate").as_double();
    telemetry_rate_ = get_parameter("telemetry_rate").as_double();
    publish_odom_ = get_parameter("publish_odom").as_bool();
    odom_frame_id_ = get_parameter("odom_frame_id").as_string();
    base_frame_id_ = get_parameter("base_frame_id").as_string();

    // Initialize VESC interface
    vesc_ = std::make_unique<VescInterface>(get_logger());
    
    // Connect to VESC
    if (!vesc_->connect(serial_port_, baudrate_)) {
      RCLCPP_ERROR(get_logger(), "Failed to connect to VESC");
      rclcpp::shutdown();
      return;
    }

    // Subscribers
    cmd_vel_sub_ = create_subscription<geometry_msgs::msg::Twist>(
      "/cmd_vel", 10,
      std::bind(&VescDriverNode::cmdVelCallback, this, std::placeholders::_1));

    // Publishers
    joint_state_pub_ = create_publisher<sensor_msgs::msg::JointState>("joint_states", 10);
    
    if (publish_odom_) {
      odom_pub_ = create_publisher<nav_msgs::msg::Odometry>("odom", 10);
    }

    // Timers
    control_timer_ = create_wall_timer(
      std::chrono::duration<double>(1.0 / control_rate_),
      std::bind(&VescDriverNode::controlLoop, this));

    telemetry_timer_ = create_wall_timer(
      std::chrono::duration<double>(1.0 / telemetry_rate_),
      std::bind(&VescDriverNode::telemetryLoop, this));

    RCLCPP_INFO(get_logger(), "VESC Driver Node started");
    RCLCPP_INFO(get_logger(), "  Wheel radius: %.4f m", wheel_radius_);
    RCLCPP_INFO(get_logger(), "  Wheel separation: %.4f m", wheel_separation_);
    RCLCPP_INFO(get_logger(), "  Pole pairs: %d", pole_pairs_);
    RCLCPP_INFO(get_logger(), "  Left VESC CAN ID: %d%s", left_can_id_, invert_left_motor_ ? " (INVERTED)" : "");
    RCLCPP_INFO(get_logger(), "  Right VESC CAN ID: %d%s", right_can_id_, invert_right_motor_ ? " (INVERTED)" : "");
  }

  ~VescDriverNode() {
    // Stop motors on shutdown
    setMotorRPM(0, 0);
  }

private:
  void cmdVelCallback(const geometry_msgs::msg::Twist::SharedPtr msg) {
    std::lock_guard<std::mutex> lock(cmd_vel_mutex_);
    last_cmd_vel_ = *msg;
    last_cmd_vel_time_ = now();
  }

  void controlLoop() {
    geometry_msgs::msg::Twist cmd_vel;
    {
      std::lock_guard<std::mutex> lock(cmd_vel_mutex_);
      cmd_vel = last_cmd_vel_;
      
      // Safety: zero velocity if no recent command (500ms timeout)
      auto dt = (now() - last_cmd_vel_time_).seconds();
      if (dt > 0.5) {
        cmd_vel.linear.x = 0.0;
        cmd_vel.angular.z = 0.0;
      }
    }

    // Differential drive kinematics: convert Twist to wheel velocities
    // v_left = v - (w * L / 2)
    // v_right = v + (w * L / 2)
    double v = cmd_vel.linear.x;
    double w = cmd_vel.angular.z;
    
    double v_left = v - (w * wheel_separation_ / 2.0);
    double v_right = v + (w * wheel_separation_ / 2.0);

    // Convert linear velocity to wheel angular velocity (rad/s)
    double omega_left = v_left / wheel_radius_;
    double omega_right = v_right / wheel_radius_;

    // Convert rad/s to RPM
    double rpm_left = omega_left * 60.0 / (2.0 * M_PI);
    double rpm_right = omega_right * 60.0 / (2.0 * M_PI);

    // Convert RPM to ERPM (Electrical RPM = RPM × pole_pairs)
    int32_t erpm_left = static_cast<int32_t>(rpm_left * pole_pairs_);
    int32_t erpm_right = static_cast<int32_t>(rpm_right * pole_pairs_);

    // Apply motor inversions if configured
    if (invert_left_motor_) erpm_left = -erpm_left;
    if (invert_right_motor_) erpm_right = -erpm_right;

    // Clamp to max RPM
    erpm_left = std::clamp(erpm_left, -max_rpm_, max_rpm_);
    erpm_right = std::clamp(erpm_right, -max_rpm_, max_rpm_);

    // Debug logging
    if (v != 0.0 || w != 0.0) {
      RCLCPP_INFO_THROTTLE(get_logger(), *get_clock(), 500,
        "cmd_vel: v=%.3f, w=%.3f -> ERPM: L=%d, R=%d", v, w, erpm_left, erpm_right);
    }

    // Send commands
    setMotorRPM(erpm_left, erpm_right);

    // Process any VESC responses
    vesc_->processResponse(5);
  }

  void telemetryLoop() {
    // Request local VESC telemetry first, then wait for its fast response
    if (left_can_id_ == 0) {
      vesc_->requestTelemetry();
    } else {
      vesc_->requestTelemetryCAN(left_can_id_);
    }
    // Local USB response arrives in ~2-5ms
    vesc_->processResponse(15);

    // Request CAN VESC telemetry separately — CAN round-trip takes 20-50ms
    if (right_can_id_ != left_can_id_) {
      vesc_->requestTelemetryCAN(right_can_id_);
      // Wait long enough for: USB→VESC0→CAN→VESC47→CAN→VESC0→USB
      vesc_->processResponse(60);
    }

    // Drain any remaining buffered data from either VESC
    vesc_->processResponse(5);

    // Publish joint states
    publishJointState();
    
    // Publish odometry if enabled
    if (publish_odom_) {
      publishOdometry();
    }
  }

  void setMotorRPM(int32_t left_erpm, int32_t right_erpm) {
    // Send to left motor (VESC ID 0 via USB or CAN)
    if (left_can_id_ == 0) {
      vesc_->setRPM(left_erpm);
    } else {
      vesc_->setRPMCAN(left_can_id_, left_erpm);
    }

    // Send to right motor (VESC ID 1 via CAN)
    if (right_can_id_ != left_can_id_) {
      vesc_->setRPMCAN(right_can_id_, right_erpm);
    }
  }

  void publishJointState() {
    auto left_state = vesc_->getLeftState(left_can_id_);
    auto right_state = vesc_->getRightState(right_can_id_);

    // Convert ERPM to wheel angular velocity (rad/s)
    double left_rpm = static_cast<double>(left_state.rpm) / pole_pairs_;
    double right_rpm = static_cast<double>(right_state.rpm) / pole_pairs_;
    
    double left_omega = left_rpm * 2.0 * M_PI / 60.0;
    double right_omega = right_rpm * 2.0 * M_PI / 60.0;

    sensor_msgs::msg::JointState joint_state;
    joint_state.header.stamp = now();
    joint_state.name = {"left_wheel_joint", "right_wheel_joint"};
    
    // Position (use tachometer-based position)
    double left_position = static_cast<double>(left_state.tachometer) / (pole_pairs_ * 6.0);  // 6 hall counts per revolution
    double right_position = static_cast<double>(right_state.tachometer) / (pole_pairs_ * 6.0);
    
    joint_state.position = {left_position, right_position};
    joint_state.velocity = {left_omega, right_omega};
    joint_state.effort = {left_state.avg_motor_current, right_state.avg_motor_current};

    joint_state_pub_->publish(joint_state);
  }

  void publishOdometry() {
    auto left_state = vesc_->getLeftState(left_can_id_);
    auto right_state = vesc_->getRightState(right_can_id_);

    // Convert ERPM to wheel angular velocities (rad/s)
    double left_rpm = static_cast<double>(left_state.rpm) / pole_pairs_;
    double right_rpm = static_cast<double>(right_state.rpm) / pole_pairs_;
    
    double left_omega = left_rpm * 2.0 * M_PI / 60.0;
    double right_omega = right_rpm * 2.0 * M_PI / 60.0;
    
    // Convert to linear velocities
    double v_left = left_omega * wheel_radius_;
    double v_right = right_omega * wheel_radius_;
    
    // Differential drive kinematics: compute robot velocity
    double v = (v_right + v_left) / 2.0;
    double w = (v_right - v_left) / wheel_separation_;

    // Create odometry message
    nav_msgs::msg::Odometry odom;
    odom.header.stamp = now();
    odom.header.frame_id = odom_frame_id_;
    odom.child_frame_id = base_frame_id_;

    // Integrate position using differential drive kinematics
    static double x = 0.0, y = 0.0, theta = 0.0;
    static rclcpp::Time last_time = now();
    
    auto current_time = now();
    double dt = (current_time - last_time).seconds();
    last_time = current_time;
    
    if (dt > 0 && dt < 1.0) {  // Sanity check on dt
      double delta_theta = w * dt;
      double delta_s = v * dt;
      
      // Update pose
      x += delta_s * cos(theta + delta_theta / 2.0);
      y += delta_s * sin(theta + delta_theta / 2.0);
      theta += delta_theta;
      
      // Normalize theta to [-pi, pi]
      while (theta > M_PI) theta -= 2.0 * M_PI;
      while (theta < -M_PI) theta += 2.0 * M_PI;
    }

    odom.pose.pose.position.x = x;
    odom.pose.pose.position.y = y;
    odom.pose.pose.position.z = 0.0;

    tf2::Quaternion q;
    q.setRPY(0, 0, theta);
    odom.pose.pose.orientation = tf2::toMsg(q);

    odom.twist.twist.linear.x = v;
    odom.twist.twist.linear.y = 0.0;
    odom.twist.twist.linear.z = 0.0;
    odom.twist.twist.angular.x = 0.0;
    odom.twist.twist.angular.y = 0.0;
    odom.twist.twist.angular.z = w;

    odom_pub_->publish(odom);
  }

  // Parameters
  std::string serial_port_;
  int baudrate_;
  double wheel_radius_;
  double wheel_separation_;
  int pole_pairs_;
  int left_can_id_;
  int right_can_id_;
  bool invert_left_motor_;
  bool invert_right_motor_;
  int max_rpm_;
  double control_rate_;
  double telemetry_rate_;
  bool publish_odom_;
  std::string odom_frame_id_;
  std::string base_frame_id_;

  // VESC interface
  std::unique_ptr<VescInterface> vesc_;

  // ROS interfaces
  rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr cmd_vel_sub_;
  rclcpp::Publisher<sensor_msgs::msg::JointState>::SharedPtr joint_state_pub_;
  rclcpp::Publisher<nav_msgs::msg::Odometry>::SharedPtr odom_pub_;
  rclcpp::TimerBase::SharedPtr control_timer_;
  rclcpp::TimerBase::SharedPtr telemetry_timer_;

  // State
  geometry_msgs::msg::Twist last_cmd_vel_;
  rclcpp::Time last_cmd_vel_time_{0, 0, RCL_ROS_TIME};
  std::mutex cmd_vel_mutex_;
};

} // namespace vesc_driver

int main(int argc, char** argv) {
  rclcpp::init(argc, argv);
  auto node = std::make_shared<vesc_driver::VescDriverNode>();
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}
