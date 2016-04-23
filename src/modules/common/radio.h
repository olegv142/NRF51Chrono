#pragma once

#include "nrf51.h"

void radio_configure(void* packet, unsigned sz);

void send_packet(void);

void receiver_on(void);

void receive_start(void);

static inline int receive_done(void)
{
    return NRF_RADIO->EVENTS_END != 0;
}

static inline int receive_crc_ok(void)
{
    return NRF_RADIO->CRCSTATUS == 1U;
}
