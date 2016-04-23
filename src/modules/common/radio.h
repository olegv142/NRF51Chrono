#pragma once

#include "nrf51.h"

void radio_configure(void* packet, unsigned sz);

void send_packet(void);
