/* Copyright (c) 2014 Nordic Semiconductor. All Rights Reserved.
 *
 * The information contained herein is property of Nordic Semiconductor ASA.
 * Terms and conditions of usage are described in detail in NORDIC
 * SEMICONDUCTOR STANDARD SOFTWARE LICENSE AGREEMENT.
 *
 * Licensees are granted free, non-transferable use of the information. NO
 * WARRANTY of ANY KIND is provided. This heading must NOT be removed from
 * the file.
 *
 */

/** @file
 * @defgroup rtc_example_main main.c
 * @{
 * @ingroup rtc_example
 * @brief Real Time Counter Example Application main file.
 *
 * This file contains the source code for a sample application using the Real Time Counter (RTC).
 * 
 */

#include "nrf.h"
#include "nrf_drv_clock.h"
#include "radio.h"
#include "packet.h"
#include "role.h"
#include "channels.h"
#include "app_error.h"

// Report packet
struct report_packet g_report_packet;

static void on_packet_received(void)
{
    // TBD
}

/**
 * @brief Function for application main entry.
 */
int main(void)
{
    unsigned role = role_get();
    radio_configure(
        &g_report_packet, sizeof(g_report_packet),
        role & ROLE_GR_SELECT ? GR1_CH : GR0_CH
    );
    receiver_on();

    while (true)
    {
        receive_start();
        while (!receive_done())
        {
            // wait
        }
        if (receive_crc_ok())
        {
            on_packet_received();
        }
    }
}

/**  @} */
