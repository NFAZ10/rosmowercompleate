#ifndef VESC_DRIVER_VESC_INTERFACE_HPP
#define VESC_DRIVER_VESC_INTERFACE_HPP

#include "vesc_driver/vesc_packet.hpp"
#include <rclcpp/rclcpp.hpp>
#include <string>
#include <memory>
#include <mutex>
#include <map>

namespace vesc_driver {

/**
 * @brief VESC state telemetry
 */
struct VescState {
  float temp_fet{0.0f};
  float temp_motor{0.0f};
  float avg_motor_current{0.0f};
  float avg_input_current{0.0f};
  float duty_now{0.0f};
  int32_t rpm{0};
  float input_voltage{0.0f};
  float amp_hours{0.0f};
  float amp_hours_charged{0.0f};
  float watt_hours{0.0f};
  float watt_hours_charged{0.0f};
  int32_t tachometer{0};
  int32_t tachometer_abs{0};
  uint8_t fault_code{0};
  rclcpp::Time timestamp;
};

/**
 * @brief VESC Serial Interface
 * Handles serial communication with VESC motor controller
 */
class VescInterface {
public:
  VescInterface(rclcpp::Logger logger);
  ~VescInterface();

  /**
   * @brief Connect to VESC via serial port
   * @param port Serial port path (e.g., /dev/ttyACM0)
   * @param baudrate Baud rate (typically 115200)
   * @return true if connection successful
   */
  bool connect(const std::string& port, int baudrate = 115200);

  /**
   * @brief Disconnect from VESC
   */
  void disconnect();

  /**
   * @brief Check if connected
   */
  bool isConnected() const { return serial_fd_ >= 0; }

  /**
   * @brief Set RPM for local VESC (ID 0)
   * @param rpm ERPM value
   * @return true if command sent successfully
   */
  bool setRPM(int32_t rpm);

  /**
   * @brief Set RPM for remote VESC over CAN
   * @param can_id CAN ID of target VESC
   * @param rpm ERPM value
   * @return true if command sent successfully
   */
  bool setRPMCAN(uint8_t can_id, int32_t rpm);

  /**
   * @brief Set duty cycle
   * @param duty_cycle Duty cycle (-1.0 to 1.0)
   * @return true if command sent successfully
   */
  bool setDuty(float duty_cycle);

  /**
   * @brief Set current
   * @param current_amps Current in amps
   * @return true if command sent successfully
   */
  bool setCurrent(float current_amps);

  /**
   * @brief Request telemetry from local VESC
   * @return true if request sent successfully
   */
  bool requestTelemetry();

  /**
   * @brief Request telemetry from remote VESC over CAN
   * @param can_id CAN ID of target VESC
   * @return true if request sent successfully
   */
  bool requestTelemetryCAN(uint8_t can_id);

  /**
   * @brief Process incoming data and update state
   * Call this periodically to process serial responses
   * @param timeout_ms Timeout for reading (milliseconds)
   * @return true if data was processed
   */
  bool processResponse(int timeout_ms = 10);

  /**
   * @brief Get latest VESC state
   * @return Current VESC state
   */
  VescState getState() const {
    std::lock_guard<std::mutex> lock(state_mutex_);
    return state_;
  }

  /**
   * @brief Get left VESC state (CAN ID based)
   * @param can_id CAN ID of left VESC
   * @return Left VESC state
   */
  VescState getLeftState(uint8_t can_id) const {
    std::lock_guard<std::mutex> lock(state_mutex_);
    if (can_id == 0) return state_;
    auto it = can_states_.find(can_id);
    return (it != can_states_.end()) ? it->second : VescState();
  }

  /**
   * @brief Get right VESC state (CAN ID based)
   * @param can_id CAN ID of right VESC
   * @return Right VESC state
   */
  VescState getRightState(uint8_t can_id) const {
    std::lock_guard<std::mutex> lock(state_mutex_);
    if (can_id == 0) return state_;
    auto it = can_states_.find(can_id);
    return (it != can_states_.end()) ? it->second : VescState();
  }

private:
  rclcpp::Logger logger_;
  int serial_fd_{-1};
  VescPacket packet_handler_;
  VescState state_;  // State for USB-connected VESC (ID 0)
  std::map<uint8_t, VescState> can_states_;  // States for CAN-connected VESCs
  mutable std::mutex state_mutex_;

  std::vector<uint8_t> rx_buffer_;
  int pending_can_id_{-1};  // Tracks last CAN telemetry request (for response routing)

  bool writeSerial(const std::vector<uint8_t>& data);
  bool readSerial(std::vector<uint8_t>& data, int timeout_ms);
  void processPacket(const std::vector<uint8_t>& packet);
};

} // namespace vesc_driver

#endif // VESC_DRIVER_VESC_INTERFACE_HPP
