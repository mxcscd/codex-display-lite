#include "app_state.h"

#include <time.h>

String formatCountdown(uint32_t seconds) {
  const uint32_t days = seconds / 86400UL;
  const uint32_t hours = (seconds % 86400UL) / 3600UL;
  const uint32_t minutes = (seconds % 3600UL) / 60UL;

  if (days > 0) {
    return String(days) + "d " + String(hours) + "h";
  }
  if (hours > 0) {
    return String(hours) + "h " + String(minutes) + "m";
  }
  return String(minutes) + "m";
}

String formatDateTime(const AppState& state, uint32_t elapsed_seconds) {
  if (!state.time_valid) {
    return "--/-- --:--";
  }

  const time_t local_time = static_cast<time_t>(
      state.unix_time + elapsed_seconds +
      static_cast<int64_t>(state.utc_offset_minutes) * 60LL);
  struct tm value {};
  gmtime_r(&local_time, &value);

  char output[16];
  strftime(output, sizeof(output), "%m/%d %H:%M", &value);
  return String(output);
}

const char* connectionLabel(ConnectionState state) {
  switch (state) {
    case ConnectionState::kDisconnected:
      return "OFFLINE";
    case ConnectionState::kSyncing:
      return "SYNCING";
    case ConnectionState::kLinked:
      return "LINKED";
    case ConnectionState::kStale:
      return "STALE";
  }
  return "OFFLINE";
}
