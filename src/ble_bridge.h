#pragma once

#include <Arduino.h>

#include "app_state.h"

bool bleBegin();
bool bleConnected();
void bleMaintainConnection();
void bleStartAdvertising();
bool bleTakeState(AppState& state);
bool bleTakePairingCode(uint32_t& passkey);
bool bleTakePairingFinished(bool& success);
bool bleClearBonds();

struct BleActionResult { char message[49]; };
bool bleTakeActionResult(BleActionResult& result);
bool bleSendAction(const char* action);
