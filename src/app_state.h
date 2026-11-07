#pragma once

#include <Arduino.h>
#include <stdint.h>

enum class ConnectionState : uint8_t {
  kDisconnected,
  kSyncing,
  kLinked,
  kStale,
};

struct AppState {
  uint8_t remaining_percent = 0;
  uint8_t weekly_remaining = 0;
  bool primary_valid = false;
  bool weekly_valid = false;
  uint32_t quota_reset_seconds = 0;
  uint32_t weekly_reset_seconds = 0;
  uint32_t sample_age_seconds = 0;

  uint64_t unix_time = 0;
  int16_t utc_offset_minutes = 0;
  ConnectionState connection = ConnectionState::kDisconnected;
  bool time_valid = false;
  bool data_valid = false;
};

String formatCountdown(uint32_t seconds);
String formatDateTime(const AppState& state, uint32_t elapsed_seconds = 0);
const char* connectionLabel(ConnectionState state);
