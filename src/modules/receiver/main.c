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
#include "radio.h"
#include "packet.h"
#include "role.h"
#include "stat.h"
#include "rtc.h"
#include "bug.h"
#include "uart.h"
#include "channels.h"
#include "app_error.h"

// Report packet
struct report_packet g_report_packet;

int g_stat_request;

void uart_rx_process(void)
{
    if (g_uart_rx_buff[0] == 's') {
        g_stat_request = 1;
    } else {
        uart_printf("Hello!" UART_EOL);
        uart_tx_flush();
    }
}

static void on_packet_received(void)
{
    if (receive_crc_ok())
        stat_update(&g_report_packet);
    receive_start();
}

/**
 * @brief Function for application main entry.
 */
int main(void)
{
    unsigned role = role_get();
    unsigned group = role >> ROLE_GR_SHIFT;
    rtc_initialize(rtc_dummy_handler);
    uart_init();
    stat_init(group);
 
    radio_configure(
            &g_report_packet, sizeof(g_report_packet),
            group ? GR1_CH : GR0_CH
        );

    receiver_on(on_packet_received);
    receive_start();

    while (true)
    {
        __WFI();
        if (g_stat_request) {
            g_stat_request = 0;
            stat_dump();
        }
    }
}

/**  @} */
