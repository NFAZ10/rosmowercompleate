#include "vesc_driver/vesc_interface.hpp"
#include <fcntl.h>
#include <termios.h>
#include <unistd.h>
#include <sys/select.h>
#include <cstring>
#include <errno.h>

namespace vesc_driver {

VescInterface::VescInterface(rclcpp::Logger logger)
  : logger_(logger) {}

VescInterface::~VescInterface() {
  disconnect();
}

bool VescInterface::connect(const std::string& port, int baudrate) {
  // Open serial port
  serial_fd_ = open(port.c_str(), O_RDWR | O_NOCTTY | O_NONBLOCK);
  if (serial_fd_ < 0) {
    RCLCPP_ERROR(logger_, "Failed to open serial port %s: %s", port.c_str(), strerror(errno));
    return false;
  }

  // Configure serial port
  struct termios tty;
  if (tcgetattr(serial_fd_, &tty) != 0) {
    RCLCPP_ERROR(logger_, "Failed to get serial attributes: %s", strerror(errno));
    close(serial_fd_);
    serial_fd_ = -1;
    return false;
  }

  // Set baud rate
  speed_t baud_const = B115200;
  if (baudrate == 9600) baud_const = B9600;
  else if (baudrate == 19200) baud_const = B19200;
  else if (baudrate == 38400) baud_const = B38400;
  else if (baudrate == 57600) baud_const = B57600;
  else if (baudrate == 115200) baud_const = B115200;

  cfsetospeed(&tty, baud_const);
  cfsetispeed(&tty, baud_const);

  // 8N1 mode
  tty.c_cflag &= ~PARENB;
  tty.c_cflag &= ~CSTOPB;
  tty.c_cflag &= ~CSIZE;
  tty.c_cflag |= CS8;
  tty.c_cflag &= ~CRTSCTS;
  tty.c_cflag |= CREAD | CLOCAL;

  // Raw mode
  tty.c_lflag &= ~ICANON;
  tty.c_lflag &= ~ECHO;
  tty.c_lflag &= ~ECHOE;
  tty.c_lflag &= ~ECHONL;
  tty.c_lflag &= ~ISIG;
  tty.c_iflag &= ~(IXON | IXOFF | IXANY);
  tty.c_iflag &= ~(IGNBRK | BRKINT | PARMRK | ISTRIP | INLCR | IGNCR | ICRNL);
  tty.c_oflag &= ~OPOST;
  tty.c_oflag &= ~ONLCR;

  // Non-blocking reads
  tty.c_cc[VTIME] = 0;
  tty.c_cc[VMIN] = 0;

  if (tcsetattr(serial_fd_, TCSANOW, &tty) != 0) {
    RCLCPP_ERROR(logger_, "Failed to set serial attributes: %s", strerror(errno));
    close(serial_fd_);
    serial_fd_ = -1;
    return false;
  }

  RCLCPP_INFO(logger_, "Connected to VESC on %s @ %d baud", port.c_str(), baudrate);
  return true;
}

void VescInterface::disconnect() {
  if (serial_fd_ >= 0) {
    close(serial_fd_);
    serial_fd_ = -1;
    RCLCPP_INFO(logger_, "Disconnected from VESC");
  }
}

bool VescInterface::setRPM(int32_t rpm) {
  auto packet = packet_handler_.createSetRPM(rpm);
  return writeSerial(packet);
}

bool VescInterface::setRPMCAN(uint8_t can_id, int32_t rpm) {
  std::vector<uint8_t> payload;
  payload.push_back(static_cast<uint8_t>(VescPacket::CommandId::COMM_SET_RPM));
  payload.push_back(static_cast<uint8_t>((rpm >> 24) & 0xFF));
  payload.push_back(static_cast<uint8_t>((rpm >> 16) & 0xFF));
  payload.push_back(static_cast<uint8_t>((rpm >> 8) & 0xFF));
  payload.push_back(static_cast<uint8_t>(rpm & 0xFF));
  
  auto packet = packet_handler_.createCANForward(can_id, payload);
  return writeSerial(packet);
}

bool VescInterface::setDuty(float duty_cycle) {
  auto packet = packet_handler_.createSetDuty(duty_cycle);
  return writeSerial(packet);
}

bool VescInterface::setCurrent(float current_amps) {
  auto packet = packet_handler_.createSetCurrent(current_amps);
  return writeSerial(packet);
}

bool VescInterface::requestTelemetry() {
  {
    std::lock_guard<std::mutex> lock(state_mutex_);
    pending_can_id_ = -1;  // Next COMM_GET_VALUES response is from local VESC
  }
  auto packet = packet_handler_.createGetValues();
  return writeSerial(packet);
}

bool VescInterface::requestTelemetryCAN(uint8_t can_id) {
  std::vector<uint8_t> payload;
  payload.push_back(static_cast<uint8_t>(VescPacket::CommandId::COMM_GET_VALUES));
  
  auto packet = packet_handler_.createCANForward(can_id, payload);
  bool ok = writeSerial(packet);
  if (ok) {
    std::lock_guard<std::mutex> lock(state_mutex_);
    pending_can_id_ = static_cast<int>(can_id);  // Route next COMM_GET_VALUES response to this CAN slot
  }
  return ok;
}

bool VescInterface::processResponse(int timeout_ms) {
  std::vector<uint8_t> data;
  if (!readSerial(data, timeout_ms)) {
    return false;
  }

  // Append to buffer
  rx_buffer_.insert(rx_buffer_.end(), data.begin(), data.end());

  // Look for complete packets
  while (rx_buffer_.size() >= 6) {
    // Find start byte
    size_t start_idx = 0;
    while (start_idx < rx_buffer_.size() && rx_buffer_[start_idx] != 2 && rx_buffer_[start_idx] != 3) {
      start_idx++;
    }

    if (start_idx > 0) {
      rx_buffer_.erase(rx_buffer_.begin(), rx_buffer_.begin() + start_idx);
    }

    if (rx_buffer_.size() < 6) break;

    // Parse length
    size_t payload_len = 0;
    size_t header_len = 0;
    
    if (rx_buffer_[0] == 2) {
      payload_len = rx_buffer_[1];
      header_len = 2;
    } else if (rx_buffer_[0] == 3) {
      if (rx_buffer_.size() < 3) break;
      payload_len = (static_cast<size_t>(rx_buffer_[1]) << 8) | rx_buffer_[2];
      header_len = 3;
    }

    size_t total_len = header_len + payload_len + 3;  // +3 for CRC and stop byte
    if (rx_buffer_.size() < total_len) break;

    // Extract packet
    std::vector<uint8_t> packet(rx_buffer_.begin() + header_len, rx_buffer_.begin() + header_len + payload_len);
    
    // Verify CRC
    uint16_t received_crc = (static_cast<uint16_t>(rx_buffer_[header_len + payload_len]) << 8) |
                            rx_buffer_[header_len + payload_len + 1];
    uint16_t calculated_crc = VescPacket::crc16(packet);

    if (received_crc == calculated_crc && rx_buffer_[total_len - 1] == 3) {
      processPacket(packet);
    }

    // Remove processed packet
    rx_buffer_.erase(rx_buffer_.begin(), rx_buffer_.begin() + total_len);
  }

  return true;
}

bool VescInterface::writeSerial(const std::vector<uint8_t>& data) {
  if (serial_fd_ < 0) {
    RCLCPP_ERROR(logger_, "Serial port not open");
    return false;
  }

  ssize_t written = write(serial_fd_, data.data(), data.size());
  if (written != static_cast<ssize_t>(data.size())) {
    RCLCPP_ERROR(logger_, "Failed to write complete packet: %s", strerror(errno));
    return false;
  }

  return true;
}

bool VescInterface::readSerial(std::vector<uint8_t>& data, int timeout_ms) {
  if (serial_fd_ < 0) {
    return false;
  }

  fd_set read_fds;
  FD_ZERO(&read_fds);
  FD_SET(serial_fd_, &read_fds);

  struct timeval timeout;
  timeout.tv_sec = timeout_ms / 1000;
  timeout.tv_usec = (timeout_ms % 1000) * 1000;

  int ret = select(serial_fd_ + 1, &read_fds, nullptr, nullptr, &timeout);
  if (ret <= 0) {
    return false;
  }

  uint8_t buffer[256];
  ssize_t bytes_read = read(serial_fd_, buffer, sizeof(buffer));
  if (bytes_read > 0) {
    data.assign(buffer, buffer + bytes_read);
    return true;
  }

  return false;
}

void VescInterface::processPacket(const std::vector<uint8_t>& packet) {
  if (packet.empty()) return;

  uint8_t cmd = packet[0];
  
  // Handle CAN forward responses
  if (cmd == static_cast<uint8_t>(VescPacket::CommandId::COMM_FORWARD_CAN)) {
    if (packet.size() < 3) return;
    
    uint8_t can_id = packet[1];
    uint8_t inner_cmd = packet[2];
    
    RCLCPP_DEBUG(logger_, "CAN packet from ID %d, inner_cmd=%d, size=%zu",
                 can_id, inner_cmd, packet.size());
    
    if (inner_cmd == static_cast<uint8_t>(VescPacket::CommandId::COMM_GET_VALUES)) {
      std::lock_guard<std::mutex> lock(state_mutex_);
      
      // Extract the inner packet (starting from the inner command ID)
      std::vector<uint8_t> inner_packet(packet.begin() + 2, packet.end());
      
      VescState can_state;
      bool ok = packet_handler_.parseGetValues(inner_packet,
                                      can_state.temp_fet, can_state.temp_motor,
                                      can_state.avg_motor_current, can_state.avg_input_current,
                                      can_state.duty_now, can_state.rpm,
                                      can_state.input_voltage,
                                      can_state.amp_hours, can_state.amp_hours_charged,
                                      can_state.watt_hours, can_state.watt_hours_charged,
                                      can_state.tachometer, can_state.tachometer_abs,
                                      can_state.fault_code);
      if (ok) {
        can_state.timestamp = rclcpp::Clock().now();
        can_states_[can_id] = can_state;
        RCLCPP_DEBUG(logger_, "CAN VESC %d: RPM=%d, current=%.2fA",
                     can_id, can_state.rpm, can_state.avg_motor_current);
      } else {
        RCLCPP_WARN_THROTTLE(logger_, *rclcpp::Clock::make_shared(), 5000,
                             "CAN VESC %d: GET_VALUES parse failed (packet too short: %zu bytes)",
                             can_id, inner_packet.size());
      }
    } else {
      RCLCPP_DEBUG(logger_, "CAN VESC %d: unhandled inner_cmd=%d", can_id, inner_cmd);
    }
  }
  // Handle local VESC responses
  else if (cmd == static_cast<uint8_t>(VescPacket::CommandId::COMM_GET_VALUES)) {
    std::lock_guard<std::mutex> lock(state_mutex_);

    // VESC firmware does NOT wrap CAN-forwarded responses in COMM_FORWARD_CAN;
    // they arrive as plain COMM_GET_VALUES. Route to the correct state slot.
    int pending_id = pending_can_id_;
    pending_can_id_ = -1;  // Consume the pending request

    if (pending_id > 0) {
      // This response came from a CAN-connected VESC — store it in can_states_
      VescState& can_state = can_states_[static_cast<uint8_t>(pending_id)];
      bool ok = packet_handler_.parseGetValues(packet,
                                      can_state.temp_fet, can_state.temp_motor,
                                      can_state.avg_motor_current, can_state.avg_input_current,
                                      can_state.duty_now, can_state.rpm,
                                      can_state.input_voltage,
                                      can_state.amp_hours, can_state.amp_hours_charged,
                                      can_state.watt_hours, can_state.watt_hours_charged,
                                      can_state.tachometer, can_state.tachometer_abs,
                                      can_state.fault_code);
      if (ok) {
        can_state.timestamp = rclcpp::Clock().now();
        RCLCPP_DEBUG(logger_, "CAN VESC %d (plain response): RPM=%d, current=%.2fA",
                     pending_id, can_state.rpm, can_state.avg_motor_current);
      } else {
        RCLCPP_WARN_THROTTLE(logger_, *rclcpp::Clock::make_shared(), 5000,
                             "CAN VESC %d: COMM_GET_VALUES parse failed (%zu bytes)",
                             pending_id, packet.size());
      }
    } else {
      // Local USB-connected VESC response
      packet_handler_.parseGetValues(packet,
                                      state_.temp_fet, state_.temp_motor,
                                      state_.avg_motor_current, state_.avg_input_current,
                                      state_.duty_now, state_.rpm,
                                      state_.input_voltage,
                                      state_.amp_hours, state_.amp_hours_charged,
                                      state_.watt_hours, state_.watt_hours_charged,
                                      state_.tachometer, state_.tachometer_abs,
                                      state_.fault_code);
      state_.timestamp = rclcpp::Clock().now();
    }
  }
}

} // namespace vesc_driver
