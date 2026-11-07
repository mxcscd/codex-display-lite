#pragma once
#include "app_state.h"
void uiCreate();
void uiUpdate(const AppState& state, uint32_t elapsed_seconds);
void uiUpdateBattery(int percent, bool charging);
void uiShowToast(const char* text);
void uiShowPairingCode(uint32_t passkey);
void uiHidePairingCode();
bool uiPairingCodeVisible();

void uiSendAction(const char* action);
