#include "vesc_driver/vesc_packet.hpp"
#include <cstring>

namespace vesc_driver {

VescPacket::VescPacket() {}

std::vector<uint8_t> VescPacket::frame(const std::vector<uint8_t>& payload) {
  std::vector<uint8_t> packet;

  // Start bytes
  if (payload.size() <= 256) {
    packet.push_back(2);  // Short packet
    packet.push_back(static_cast<uint8_t>(payload.size()));
  } else {
    packet.push_back(3);  // Long packet
    packet.push_back(static_cast<uint8_t>(payload.size() >> 8));
    packet.push_back(static_cast<uint8_t>(payload.size() & 0xFF));
  }

  // Payload
  packet.insert(packet.end(), payload.begin(), payload.end());

  // CRC
  uint16_t crc = crc16(payload);
  packet.push_back(static_cast<uint8_t>(crc >> 8));
  packet.push_back(static_cast<uint8_t>(crc & 0xFF));

  // Stop byte
  packet.push_back(3);

  return packet;
}

std::vector<uint8_t> VescPacket::createSetRPM(int32_t rpm) {
  std::vector<uint8_t> payload;
  payload.push_back(static_cast<uint8_t>(CommandId::COMM_SET_RPM));
  appendInt32(payload, rpm);
  return frame(payload);
}

std::vector<uint8_t> VescPacket::createSetDuty(float duty_cycle) {
  std::vector<uint8_t> payload;
  payload.push_back(static_cast<uint8_t>(CommandId::COMM_SET_DUTY));
  appendInt32(payload, static_cast<int32_t>(duty_cycle * 100000.0f));
  return frame(payload);
}

std::vector<uint8_t> VescPacket::createSetCurrent(float current_amps) {
  std::vector<uint8_t> payload;
  payload.push_back(static_cast<uint8_t>(CommandId::COMM_SET_CURRENT));
  appendInt32(payload, static_cast<int32_t>(current_amps * 1000.0f));
  return frame(payload);
}

std::vector<uint8_t> VescPacket::createGetValues() {
  std::vector<uint8_t> payload;
  payload.push_back(static_cast<uint8_t>(CommandId::COMM_GET_VALUES));
  return frame(payload);
}

std::vector<uint8_t> VescPacket::createCANForward(uint8_t can_id, const std::vector<uint8_t>& payload) {
  std::vector<uint8_t> can_payload;
  can_payload.push_back(static_cast<uint8_t>(CommandId::COMM_FORWARD_CAN));
  can_payload.push_back(can_id);
  can_payload.insert(can_payload.end(), payload.begin(), payload.end());
  return frame(can_payload);
}

bool VescPacket::parseGetValues(const std::vector<uint8_t>& data,
                                 float& temp_fet, float& temp_motor,
                                 float& avg_motor_current, float& avg_input_current,
                                 float& duty_now, int32_t& rpm,
                                 float& input_voltage,
                                 float& amp_hours, float& amp_hours_charged,
                                 float& watt_hours, float& watt_hours_charged,
                                 int32_t& tachometer, int32_t& tachometer_abs,
                                 uint8_t& fault_code) {
  if (data.size() < 55) {
    return false;
  }

  size_t index = 1;  // Skip command ID

  // VESC 6.x GET_VALUES response layout (55 bytes total including cmd byte):
  //   temp_fet(2) + temp_motor(2) + avg_motor_current(4) + avg_input_current(4)
  //   + avg_id(4) + avg_iq(4) + duty_now(2) + rpm(4) + input_voltage(2)
  //   + amp_hours(4) + amp_hours_charged(4) + watt_hours(4) + watt_hours_charged(4)
  //   + tachometer(4) + tachometer_abs(4) + fault_code(1) = 54 payload bytes
  temp_fet = extractFloat(data, index, 10.0f);                   // int16, 2 bytes
  temp_motor = extractFloat(data, index, 10.0f);                 // int16, 2 bytes
  avg_motor_current = extractFloatInt32(data, index, 100.0f);    // int32, 4 bytes
  avg_input_current = extractFloatInt32(data, index, 100.0f);    // int32, 4 bytes
  index += 8;  // Skip avg_id (4 bytes) + avg_iq (4 bytes, VESC 6.x)
  duty_now = extractFloat(data, index, 1000.0f);                 // int16, 2 bytes
  rpm = extractInt32(data, index);                               // int32, 4 bytes
  input_voltage = extractFloat(data, index, 10.0f);              // int16, 2 bytes
  amp_hours = extractFloatInt32(data, index, 10000.0f);          // int32, 4 bytes
  amp_hours_charged = extractFloatInt32(data, index, 10000.0f);  // int32, 4 bytes
  watt_hours = extractFloatInt32(data, index, 10000.0f);         // int32, 4 bytes
  watt_hours_charged = extractFloatInt32(data, index, 10000.0f); // int32, 4 bytes
  tachometer = extractInt32(data, index);                        // int32, 4 bytes
  tachometer_abs = extractInt32(data, index);                    // int32, 4 bytes
  fault_code = data[index++];                                    // uint8, 1 byte

  return true;
}

uint16_t VescPacket::crc16(const std::vector<uint8_t>& data) {
  uint16_t crc = 0;
  for (uint8_t byte : data) {
    crc ^= static_cast<uint16_t>(byte) << 8;
    for (int i = 0; i < 8; i++) {
      if (crc & 0x8000) {
        crc = (crc << 1) ^ 0x1021;
      } else {
        crc = crc << 1;
      }
    }
  }
  return crc;
}

void VescPacket::appendInt32(std::vector<uint8_t>& buffer, int32_t value) {
  buffer.push_back(static_cast<uint8_t>((value >> 24) & 0xFF));
  buffer.push_back(static_cast<uint8_t>((value >> 16) & 0xFF));
  buffer.push_back(static_cast<uint8_t>((value >> 8) & 0xFF));
  buffer.push_back(static_cast<uint8_t>(value & 0xFF));
}

void VescPacket::appendInt16(std::vector<uint8_t>& buffer, int16_t value) {
  buffer.push_back(static_cast<uint8_t>((value >> 8) & 0xFF));
  buffer.push_back(static_cast<uint8_t>(value & 0xFF));
}

void VescPacket::appendFloat(std::vector<uint8_t>& buffer, float value, float scale) {
  appendInt32(buffer, static_cast<int32_t>(value * scale));
}

int32_t VescPacket::extractInt32(const std::vector<uint8_t>& data, size_t& index) {
  int32_t value = (static_cast<int32_t>(data[index]) << 24) |
                  (static_cast<int32_t>(data[index + 1]) << 16) |
                  (static_cast<int32_t>(data[index + 2]) << 8) |
                  static_cast<int32_t>(data[index + 3]);
  index += 4;
  return value;
}

int16_t VescPacket::extractInt16(const std::vector<uint8_t>& data, size_t& index) {
  int16_t value = (static_cast<int16_t>(data[index]) << 8) |
                  static_cast<int16_t>(data[index + 1]);
  index += 2;
  return value;
}

float VescPacket::extractFloat(const std::vector<uint8_t>& data, size_t& index, float scale) {
  return static_cast<float>(extractInt16(data, index)) / scale;
}

float VescPacket::extractFloatInt32(const std::vector<uint8_t>& data, size_t& index, float scale) {
  return static_cast<float>(extractInt32(data, index)) / scale;
}

} // namespace vesc_driver
