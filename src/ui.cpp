#include "ui.h"
#include "ble_bridge.h"
#include <lvgl.h>

LV_FONT_DECLARE(font_montserrat_100);
namespace {
lv_obj_t *clock_label, *status_label, *battery_label, *primary_label;
lv_obj_t *primary_reset, *pairing_overlay, *quota_arc, *quota_title, *percent_label;
lv_obj_t* metric_values[4];
lv_obj_t *pairing_code, *toast;
lv_timer_t* toast_timer = nullptr;
constexpr uint32_t kCyan = 0x08C9F4;

lv_obj_t* label(lv_obj_t* parent, const char* text, const lv_font_t* font,
                uint32_t color, lv_align_t align, int x, int y) {
  auto* obj = lv_label_create(parent);
  lv_label_set_text(obj, text);
  lv_obj_set_style_text_font(obj, font, 0);
  lv_obj_set_style_text_color(obj, lv_color_hex(color), 0);
  lv_obj_align(obj, align, x, y);
  return obj;
}
void hideToast(lv_timer_t*) {
  lv_obj_add_flag(toast, LV_OBJ_FLAG_HIDDEN);
  toast_timer = nullptr;
}
void dismissPairing(lv_event_t*) { uiHidePairingCode(); }
void onControl(lv_event_t* event) {
  uiSendAction(static_cast<const char*>(lv_event_get_user_data(event)));
}
void controlButton(lv_obj_t* screen, const char* text, int x, const char* action) {
  auto* button = lv_btn_create(screen);
  lv_obj_set_size(button, 116, 26);
  lv_obj_set_pos(button, x, 350);
  lv_obj_set_style_bg_opa(button, LV_OPA_TRANSP, 0);
  lv_obj_set_style_border_color(button, lv_color_hex(0x303538), 0);
  lv_obj_set_style_border_width(button, 1, 0);
  lv_obj_set_style_radius(button, 7, 0);
  lv_obj_set_style_shadow_width(button, 0, 0);
  lv_obj_add_event_cb(button, onControl, LV_EVENT_CLICKED, const_cast<char*>(action));
  label(button, text, &lv_font_montserrat_12, kCyan, LV_ALIGN_CENTER, 0, 0);
}
void resetValuePosition() {
  lv_obj_align(primary_label, LV_ALIGN_TOP_MID, -6, 165);
  lv_obj_align_to(percent_label, primary_label, LV_ALIGN_OUT_RIGHT_BOTTOM, 4, -4);
  lv_obj_align(primary_reset, LV_ALIGN_TOP_MID, 0, 320);
}
uint32_t remaining(uint32_t seconds, uint32_t elapsed) {
  return seconds > elapsed ? seconds - elapsed : 0;
}
}

void uiCreate() {
  auto* screen = lv_scr_act();
  lv_obj_set_style_bg_color(screen, lv_color_hex(0x000000), 0);
  lv_obj_clear_flag(screen, LV_OBJ_FLAG_SCROLLABLE);
  clock_label = label(screen, "--/-- --:--", &lv_font_montserrat_18, 0xAEB8BD, LV_ALIGN_TOP_LEFT, 28, 20);
  status_label = label(screen, LV_SYMBOL_BLUETOOTH " OFFLINE", &lv_font_montserrat_14, 0xFFB800, LV_ALIGN_TOP_RIGHT, -28, 21);
  battery_label = label(screen, "", &lv_font_montserrat_14, 0xAEB8BD, LV_ALIGN_TOP_RIGHT, -142, 21);

  quota_arc = lv_arc_create(screen);
  lv_obj_set_size(quota_arc, 304, 304);
  lv_obj_align(quota_arc, LV_ALIGN_TOP_MID, 0, 54);
  lv_arc_set_rotation(quota_arc, 135);
  lv_arc_set_bg_angles(quota_arc, 0, 270);
  lv_arc_set_range(quota_arc, 0, 100);
  lv_arc_set_value(quota_arc, 0);
  lv_obj_remove_style(quota_arc, nullptr, LV_PART_KNOB);
  lv_obj_set_style_arc_width(quota_arc, 18, LV_PART_MAIN);
  lv_obj_set_style_arc_color(quota_arc, lv_color_hex(0x24282B), LV_PART_MAIN);
  lv_obj_set_style_arc_width(quota_arc, 18, LV_PART_INDICATOR);
  lv_obj_set_style_arc_color(quota_arc, lv_color_hex(kCyan), LV_PART_INDICATOR);
  lv_obj_set_style_bg_opa(quota_arc, LV_OPA_TRANSP, 0);
  lv_obj_clear_flag(quota_arc, LV_OBJ_FLAG_CLICKABLE);
  quota_title = label(screen, "7 DAY LEFT", &lv_font_montserrat_18, kCyan, LV_ALIGN_TOP_MID, 0, 126);
  primary_label = label(screen, "", &font_montserrat_100, 0xFFFFFF, LV_ALIGN_TOP_MID, -6, 165);
  percent_label = label(screen, "%", &lv_font_montserrat_26, 0xFFFFFF, LV_ALIGN_TOP_MID, 0, 240);
  lv_obj_add_flag(percent_label, LV_OBJ_FLAG_HIDDEN);
  primary_reset = label(screen, "WAITING FOR DATA", &lv_font_montserrat_18, kCyan, LV_ALIGN_TOP_MID, 0, 320);
  controlButton(screen, "FOCUS CODEX", 119, "focus");
  controlButton(screen, "REFRESH QUOTA", 245, "refresh");

  auto* metrics = lv_obj_create(screen);
  lv_obj_set_pos(metrics, 24, 382);
  lv_obj_set_size(metrics, 432, 74);
  lv_obj_set_style_radius(metrics, 10, 0);
  lv_obj_set_style_bg_color(metrics, lv_color_hex(0x020506), 0);
  lv_obj_set_style_border_color(metrics, lv_color_hex(kCyan), 0);
  lv_obj_set_style_border_width(metrics, 1, 0);
  lv_obj_set_style_pad_all(metrics, 0, 0);
  lv_obj_clear_flag(metrics, LV_OBJ_FLAG_SCROLLABLE);
  const char* titles[] = {"SHORT LEFT", "RESET IN", "WEEK LEFT", "RESET IN"};
  const int starts[] = {0, 100, 216, 316};
  for (int i = 0; i < 4; ++i) {
    label(metrics, titles[i], &lv_font_montserrat_12, kCyan, LV_ALIGN_TOP_LEFT, starts[i] + 10, 11);
    metric_values[i] = label(metrics, "--", &lv_font_montserrat_24, 0xFFFFFF, LV_ALIGN_TOP_LEFT, starts[i] + 10, 35);
    if (i > 0) {
      auto* divider = lv_obj_create(metrics);
      lv_obj_remove_style_all(divider);
      lv_obj_set_pos(divider, starts[i], 13);
      lv_obj_set_size(divider, 1, 48);
      lv_obj_set_style_bg_color(divider, lv_color_hex(0x303538), 0);
      lv_obj_set_style_bg_opa(divider, LV_OPA_COVER, 0);
    }
  }

  pairing_overlay = lv_obj_create(screen);
  lv_obj_set_size(pairing_overlay, 420, 240);
  lv_obj_center(pairing_overlay);
  lv_obj_set_style_bg_color(pairing_overlay, lv_color_hex(0x091A24), 0);
  lv_obj_set_style_border_color(pairing_overlay, lv_color_hex(kCyan), 0);
  lv_obj_set_style_border_width(pairing_overlay, 1, 0);
  lv_obj_clear_flag(pairing_overlay, LV_OBJ_FLAG_SCROLLABLE);
  lv_obj_add_flag(pairing_overlay, LV_OBJ_FLAG_CLICKABLE);
  lv_obj_add_event_cb(pairing_overlay, dismissPairing, LV_EVENT_CLICKED, nullptr);
  label(pairing_overlay, "ENTER ON YOUR MAC", &lv_font_montserrat_18, 0xAEB8BD, LV_ALIGN_TOP_MID, 0, 25);
  pairing_code = label(pairing_overlay, "", &lv_font_montserrat_48, 0xFFFFFF, LV_ALIGN_CENTER, 0, 0);
  label(pairing_overlay, "TAP TO DISMISS", &lv_font_montserrat_14, 0xAEB8BD, LV_ALIGN_BOTTOM_MID, 0, -20);
  lv_obj_add_flag(pairing_overlay, LV_OBJ_FLAG_HIDDEN);
  toast = label(screen, "", &lv_font_montserrat_14, 0xFFFFFF, LV_ALIGN_BOTTOM_MID, 0, -82);
  lv_obj_add_flag(toast, LV_OBJ_FLAG_HIDDEN);
}

void uiUpdate(const AppState& state, uint32_t elapsed) {
  lv_label_set_text(clock_label, formatDateTime(state, elapsed).c_str());
  lv_label_set_text(status_label, (String(LV_SYMBOL_BLUETOOTH " ") + connectionLabel(state.connection)).c_str());
  lv_obj_align(status_label, LV_ALIGN_TOP_RIGHT, -28, 21);
  const bool fresh = state.connection == ConnectionState::kLinked && state.sample_age_seconds + elapsed < 120;
  const uint32_t accent = fresh ? kCyan : (state.connection == ConnectionState::kStale ? 0xFFB800 : 0x7C878C);
  lv_obj_set_style_text_color(status_label, lv_color_hex(fresh ? 0x4DA3FF : 0xFFB800), 0);
  lv_obj_set_style_arc_color(quota_arc, lv_color_hex(accent), LV_PART_INDICATOR);
  lv_obj_set_style_text_color(quota_title, lv_color_hex(accent), 0);
  lv_obj_set_style_text_color(primary_reset, lv_color_hex(accent), 0);
  const uint32_t p = remaining(state.quota_reset_seconds, elapsed);
  const uint32_t w = remaining(state.weekly_reset_seconds, elapsed);
  const bool pv = fresh && state.data_valid && state.primary_valid && p > 0;
  const bool wv = fresh && state.data_valid && state.weekly_valid && w > 0;
  if (wv) {
    lv_arc_set_value(quota_arc, state.weekly_remaining);
    lv_label_set_text_fmt(primary_label, "%u", state.weekly_remaining);
    lv_obj_clear_flag(percent_label, LV_OBJ_FLAG_HIDDEN);
    lv_label_set_text(primary_reset, (String("QUOTA RESET ") + formatCountdown(w)).c_str());
  } else {
    lv_arc_set_value(quota_arc, 0);
    // The large custom font contains digits and %, so unknown uses a standard-font label below.
    lv_label_set_text(primary_label, "");
    lv_obj_add_flag(percent_label, LV_OBJ_FLAG_HIDDEN);
    lv_label_set_text(primary_reset, fresh ? "WEEKLY QUOTA UNAVAILABLE" : "WAITING FOR FRESH DATA");
  }
  if (pv) {
    lv_label_set_text_fmt(metric_values[0], "%u%%", state.remaining_percent);
    lv_label_set_text(metric_values[1], formatCountdown(p).c_str());
  } else {
    lv_label_set_text(metric_values[0], "--");
    lv_label_set_text(metric_values[1], "--");
  }
  if (wv) {
    lv_label_set_text_fmt(metric_values[2], "%u%%", state.weekly_remaining);
    lv_label_set_text(metric_values[3], formatCountdown(w).c_str());
  } else {
    lv_label_set_text(metric_values[2], "--");
    lv_label_set_text(metric_values[3], "--");
  }
  resetValuePosition();
}

void uiUpdateBattery(int percent, bool charging) {
  if (percent < 0 || percent > 100) {
    lv_label_set_text(battery_label, "");
    return;
  }
  lv_label_set_text_fmt(battery_label, charging ? "CHG %d%%" : "BAT %d%%", percent);
  lv_obj_align_to(battery_label, status_label, LV_ALIGN_OUT_LEFT_MID, -12, 0);
}
void uiShowToast(const char* text) {
  lv_label_set_text(toast, text);
  lv_obj_align(toast, LV_ALIGN_BOTTOM_MID, 0, -82);
  lv_obj_clear_flag(toast, LV_OBJ_FLAG_HIDDEN);
  lv_obj_move_foreground(toast);
  if (toast_timer) lv_timer_del(toast_timer);
  toast_timer = lv_timer_create(hideToast, 2000, nullptr);
  lv_timer_set_repeat_count(toast_timer, 1);
}
void uiShowPairingCode(uint32_t passkey) {
  lv_label_set_text_fmt(pairing_code, "%03lu %03lu", static_cast<unsigned long>(passkey / 1000), static_cast<unsigned long>(passkey % 1000));
  lv_obj_center(pairing_code);
  lv_obj_clear_flag(pairing_overlay, LV_OBJ_FLAG_HIDDEN);
  lv_obj_move_foreground(pairing_overlay);
}
void uiHidePairingCode() { lv_obj_add_flag(pairing_overlay, LV_OBJ_FLAG_HIDDEN); }
bool uiPairingCodeVisible() { return !lv_obj_has_flag(pairing_overlay, LV_OBJ_FLAG_HIDDEN); }

void uiSendAction(const char* action) {
  uiShowToast(bleSendAction(action) ? "REQUEST SENT" : "OFFLINE / WAIT");
}
