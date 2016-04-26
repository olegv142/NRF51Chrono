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
#include "nrf_gpio.h"
#include "nrf_drv_gpiote.h"
#include "nrf_drv_config.h"
#include "nrf_drv_rtc.h"
#include "nrf_adc.h"
#include "clock.h"
#include "boards.h"
#include "app_error.h"
#include "bug.h"
#include "rtc.h"
#include "role.h"
#include "radio.h"
#include "packet.h"
#include "channels.h"
#include "app_util_platform.h"

#include <stdint.h>
#include <stdbool.h>

// The module role read from input pins on startup
unsigned g_role;

unsigned g_clk_decim_;
unsigned g_clk_ticks_;
unsigned g_clk_ticks;
unsigned g_clk_msec;
unsigned g_clk_sec;

// Blink counter
unsigned g_blink_cnt;

// Button status
unsigned g_btn_pressed;  // debounced
int      g_btn_pressed_; // raw status

// The timestamp of first pressed event
unsigned g_btn_pressed_ts;

// The timestamp of last released event
unsigned g_btn_released_ts;

// The power voltage in millivolts
unsigned g_vcc_mv;

// Report packet
struct report_packet g_report_packet;

// Report sequence number
unsigned g_report_sn;

// Send report request for main loop
int g_report_req;

// Reporting period
unsigned g_reporting_ticks[MAX_GR_ROLES] = {
    191, 193, 197, 199, 211, 223, 227, 229 // prime numbers
};

#define LED_PWR_BIT (1<<LED_PWR)
#define DEBOUNCE_PERIOD 2
#define DEBOUNCE_TICKS 256
#define BLINK_PERIOD 10
#define BLINK_TICKS 8

// RTC CC channels
#define CC_PERIODIC 0 // Periodic tasks
#define CC_DEBOUNCE 1 // Debounce channel
#define CC_BLINK    2 // LED blink channel

BUILD_BUG_ON(RTC0_CONFIG_FREQUENCY != 1024);

static inline void led_on(void)
{
    NRF_GPIO->OUTSET = LED_PWR_BIT;
}

static inline void led_off(void)
{
    NRF_GPIO->OUTCLR = LED_PWR_BIT;
}

static inline int is_btn_pressed(void)
{
    return !(NRF_GPIO->IN & (1<<BUTTON_USER));
}

static inline unsigned reporting_ticks(void)
{
    return g_reporting_ticks[g_role];
}

static inline void rtc_cc_schedule(unsigned chan, unsigned time)
{
    ret_code_t err_code = nrf_drv_rtc_cc_set(&g_rtc, chan, rtc_current() + time, true);
    APP_ERROR_CHECK(err_code);
}

static inline void rtc_cc_disable(unsigned chan)
{
    ret_code_t err_code = nrf_drv_rtc_cc_disable(&g_rtc, chan);
    APP_ERROR_CHECK(err_code);
}

static inline void periodic_task(void)
{
    g_report_req = 1;
    if (++g_blink_cnt >= BLINK_PERIOD)
    {
        g_blink_cnt = 0;
        rtc_cc_schedule(CC_BLINK, BLINK_TICKS);
        nrf_adc_start();
        led_on();
    }
    rtc_cc_schedule(CC_PERIODIC, reporting_ticks());
}

static void btn_pressed_cb(nrf_drv_gpiote_pin_t pin, nrf_gpiote_polarity_t action)
{
    if (!g_btn_pressed) {
        g_btn_pressed_ts = rtc_current();
        led_on();
    }
    g_btn_pressed_ = 1;
    g_btn_pressed = DEBOUNCE_TICKS;
    rtc_cc_schedule(CC_DEBOUNCE, DEBOUNCE_PERIOD);
}

static void btn_debounce(void)
{
    if (!is_btn_pressed())
    {
        if (g_btn_pressed_) {
            g_btn_released_ts = rtc_current();
        }
        g_btn_pressed_ = 0;
        if (g_btn_pressed <= DEBOUNCE_PERIOD) {
            g_btn_pressed = 0;
            led_off();
            rtc_cc_disable(CC_DEBOUNCE);
            return;
        }
        g_btn_pressed -= DEBOUNCE_PERIOD;
    }
    rtc_cc_schedule(CC_DEBOUNCE, DEBOUNCE_PERIOD);
}

/** @brief: Function for handling the RTC0 interrupts.
 * Triggered on TICK and COMPARE0 match.
 */
static void rtc_handler(nrf_drv_rtc_int_type_t int_type)
{
    switch (int_type)
    {
    case CC_PERIODIC:
        periodic_task();
        break;
    case CC_DEBOUNCE:
        btn_debounce();
        break;
    case CC_BLINK:
        if (!g_btn_pressed)
            led_off();
        rtc_cc_disable(CC_BLINK);
        break;
    default:
        ;
    }
}

/**
 * @brief ADC interrupt handler.
 */
void ADC_IRQHandler(void)
{
    unsigned adc_sample;
    nrf_adc_conversion_event_clean();
    adc_sample = nrf_adc_result_get();
    g_vcc_mv = adc_sample * 3600 / 1024;
}

/**
 * @brief ADC initialization.
 */
static void adc_initialize(void)
{
    const nrf_adc_config_t nrf_adc_config = { NRF_ADC_CONFIG_RES_10BIT,
        NRF_ADC_CONFIG_SCALING_SUPPLY_ONE_THIRD,
        NRF_ADC_CONFIG_REF_VBG
    };
    // Initialize and configure ADC
    nrf_adc_configure( (nrf_adc_config_t *)&nrf_adc_config);
    nrf_adc_int_enable(ADC_INTENSET_END_Enabled << ADC_INTENSET_END_Pos);
    NVIC_SetPriority(ADC_IRQn, APP_IRQ_PRIORITY_LOW);
    NVIC_EnableIRQ(ADC_IRQn);
}

static void btn_initialize(void)
{
    nrf_drv_gpiote_in_config_t cfg = {
        .is_watcher = false,
        .hi_accuracy = false,
        .pull = NRF_GPIO_PIN_PULLUP,
        .sense = NRF_GPIOTE_POLARITY_HITOLO,
    };
    ret_code_t err_code = nrf_drv_gpiote_init();
    APP_ERROR_CHECK(err_code);
    err_code = nrf_drv_gpiote_in_init(BUTTON_USER, &cfg, btn_pressed_cb);
    APP_ERROR_CHECK(err_code);
    nrf_drv_gpiote_in_event_enable(BUTTON_USER, true);
}

/**
 * @brief Function for application main entry.
 */
int main(void)
{
    unsigned role = role_get();
    g_role = role & ROLE_MASK;
    BUG_ON(g_role >= MAX_GR_ROLES);
    nrf_gpio_cfg_output(LED_PWR);
    btn_initialize();
    adc_initialize();
    nrf_adc_start();
    rtc_initialize(rtc_handler);

    radio_configure(
        &g_report_packet, sizeof(g_report_packet),
        role & ROLE_GR_SELECT ? GR1_CH : GR0_CH
    );

    rtc_cc_schedule(CC_PERIODIC, reporting_ticks());

    while (true)
    {
        __WFI();
        if (g_report_req) {
            g_report_req = 0;
            g_report_packet.sn = ++g_report_sn;
            g_report_packet.ts = rtc_current();
            g_report_packet.role = g_role;
            g_report_packet.vcc_mv = g_vcc_mv;
            g_report_packet.bt_pressed = (g_btn_pressed != 0);
            g_report_packet.bt_pressed_ts = g_btn_pressed_ts;
            g_report_packet.bt_released_ts = g_btn_released_ts;
            send_packet();
        }
    }
}


/**  @} */
