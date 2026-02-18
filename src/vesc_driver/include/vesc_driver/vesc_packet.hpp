#ifndef VESC_DRIVER_VESC_PACKET_HPP
#define VESC_DRIVER_VESC_PACKET_HPP

#include <cstddef>
#include <cstdint>
#include <vector>

namespace vesc_driver {

/**
 * @brief VESC Communication Protocol Packet Handler
 * Implements VESC serial protocol for encoding/decoding packets
 */
class VescPacket {
public:
  VescPacket();
  ~VescPacket() = default;

  // VESC Command IDs (COMM_PACKET_ID)
  enum class CommandId : uint8_t {
    COMM_FW_VERSION = 0,
    COMM_JUMP_TO_BOOTLOADER = 1,
    COMM_ERASE_NEW_APP = 2,
    COMM_WRITE_NEW_APP_DATA = 3,
    COMM_GET_VALUES = 4,
    COMM_SET_DUTY = 5,
    COMM_SET_CURRENT = 6,
    COMM_SET_CURRENT_BRAKE = 7,
    COMM_SET_RPM = 8,
    COMM_SET_POS = 9,
    COMM_SET_HANDBRAKE = 10,
    COMM_SET_DETECT = 11,
    COMM_SET_SERVO_POS = 12,
    COMM_SET_MCCONF = 13,
    COMM_GET_MCCONF = 14,
    COMM_GET_MCCONF_DEFAULT = 15,
    COMM_SET_APPCONF = 16,
    COMM_GET_APPCONF = 17,
    COMM_GET_APPCONF_DEFAULT = 18,
    COMM_SAMPLE_PRINT = 19,
    COMM_TERMINAL_CMD = 20,
    COMM_PRINT = 21,
    COMM_ROTOR_POSITION = 22,
    COMM_EXPERIMENT_SAMPLE = 23,
    COMM_DETECT_MOTOR_PARAM = 24,
    COMM_DETECT_MOTOR_R_L = 25,
    COMM_DETECT_MOTOR_FLUX_LINKAGE = 26,
    COMM_DETECT_ENCODER = 27,
    COMM_DETECT_HALL_FOC = 28,
    COMM_REBOOT = 29,
    COMM_ALIVE = 30,
    COMM_GET_DECODED_PPM = 31,
    COMM_GET_DECODED_ADC = 32,
    COMM_GET_DECODED_CHUK = 33,
    COMM_FORWARD_CAN = 34,
    COMM_SET_CHUCK_DATA = 35,
    COMM_CUSTOM_APP_DATA = 36,
    COMM_NRF_START_PAIRING = 37
  };

  /**
   * @brief Frame a payload for serial transmission
   * @param payload Payload bytes to frame
   * @return Complete framed packet with start bytes, length, CRC
   */
  std::vector<uint8_t> frame(const std::vector<uint8_t>& payload);

  /**
   * @brief Create SET_RPM command packet
   * @param rpm RPM value to set (ERPM)
   * @return Framed packet ready for transmission
   */
  std::vector<uint8_t> createSetRPM(int32_t rpm);

  /**
   * @brief Create SET_DUTY command packet
   * @param duty_cycle Duty cycle (-1.0 to 1.0)
   * @return Framed packet ready for transmission
   */
  std::vector<uint8_t> createSetDuty(float duty_cycle);

  /**
   * @brief Create SET_CURRENT command packet
   * @param current_amps Current in amps
   * @return Framed packet ready for transmission
   */
  std::vector<uint8_t> createSetCurrent(float current_amps);

  /**
   * @brief Create GET_VALUES request packet
   * @return Framed packet ready for transmission
   */
  std::vector<uint8_t> createGetValues();

  /**
   * @brief Create CAN forwarded command
   * @param can_id CAN ID of target VESC
   * @param payload Command payload to forward
   * @return Framed CAN forward packet
   */
  std::vector<uint8_t> createCANForward(uint8_t can_id, const std::vector<uint8_t>& payload);

  /**
   * @brief Parse GET_VALUES response
   * @param data Response payload
   * @param temp_fet Output: FET temperature (°C)
   * @param temp_motor Output: Motor temperature (°C)
   * @param avg_motor_current Output: Average motor current (A)
   * @param avg_input_current Output: Average input current (A)
   * @param duty_now Output: Current duty cycle
   * @param rpm Output: Current ERPM
   * @param input_voltage Output: Input voltage (V)
   * @param amp_hours Output: Amp hours used
   * @param amp_hours_charged Output: Amp hours charged
   * @param watt_hours Output: Watt hours used
   * @param watt_hours_charged Output: Watt hours charged
   * @param tachometer Output: Tachometer value (encoder counts)
   * @param tachometer_abs Output: Absolute tachometer
   * @param fault_code Output: Fault code
   * @return true if parsing successful
   */
  bool parseGetValues(const std::vector<uint8_t>& data,
                      float& temp_fet, float& temp_motor,
                      float& avg_motor_current, float& avg_input_current,
                      float& duty_now, int32_t& rpm,
                      float& input_voltage,
                      float& amp_hours, float& amp_hours_charged,
                      float& watt_hours, float& watt_hours_charged,
                      int32_t& tachometer, int32_t& tachometer_abs,
                      uint8_t& fault_code);

  /**
   * @brief Calculate CRC16 for VESC packet
   * @param data Data to calculate CRC for
   * @return CRC16 value
   */
  static uint16_t crc16(const std::vector<uint8_t>& data);

private:
  // Helper functions for data encoding/decoding
  void appendInt32(std::vector<uint8_t>& buffer, int32_t value);
  void appendInt16(std::vector<uint8_t>& buffer, int16_t value);
  void appendFloat(std::vector<uint8_t>& buffer, float value, float scale);
  int32_t extractInt32(const std::vector<uint8_t>& data, size_t& index);
  int16_t extractInt16(const std::vector<uint8_t>& data, size_t& index);
  float extractFloat(const std::vector<uint8_t>& data, size_t& index, float scale);     // reads int16
  float extractFloatInt32(const std::vector<uint8_t>& data, size_t& index, float scale); // reads int32
};

} // namespace vesc_driver

#endif // VESC_DRIVER_VESC_PACKET_HPP
