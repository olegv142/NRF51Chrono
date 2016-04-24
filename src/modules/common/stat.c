#include "stat.h"
#include "uart.h"
#include "rtc.h"
#include "bug.h"
#include "channels.h"

// Statistic collected for each transmitter
struct stat_entry {
    // Epoch incremented every time the reporting module restarted, 0 means it was not started at all
    unsigned epoch; 
    // Reports stat for current epoch
    unsigned first_report_ts;
    unsigned last_report_ts;
    unsigned reports_total;
    unsigned reports_received;
    // Last report received
    struct report_packet last_report;
};

static struct stat_entry g_stat_entry[MAX_GR_ROLES];
static unsigned g_stat_group;

void stat_init(unsigned group)
{
    g_stat_group = group;
}

// Update stat on new report arrival
void stat_update(struct report_packet const* r)
{
    unsigned ts = rtc_current();
    BUG_ON(r->role >= MAX_GR_ROLES);
    struct stat_entry* s = &g_stat_entry[r->role];
    int new_epoch = !s->epoch || s->last_report.sn >= r->sn;
    if (new_epoch) {
        ++s->epoch;
        s->first_report_ts = s->last_report_ts = ts;
        s->reports_total = s->reports_received = 1;
    } else {
        s->last_report_ts = ts;
        s->reports_total += r->sn - s->last_report.sn;
        s->reports_received += 1;
    }
    s->last_report = *r;
}

// Print stat to UART
void stat_dump(void)
{
    unsigned i, ts = rtc_current();
    uart_printf("%u %u" UART_EOL, g_stat_group, ts);
    for (i = 0; i < MAX_GR_ROLES; ++i)
    {
        struct stat_entry const* s = &g_stat_entry[i];
        uart_printf("%u %u %u %u %u ", 
            s->epoch,
            s->first_report_ts,
            s->last_report_ts,
            s->reports_total,
            s->reports_received
        );
        struct report_packet const* r = &s->last_report;
        uart_printf("%u %u %u %u %u %u" UART_EOL, 
            r->sn,
            r->ts,
            r->bt_pressed,
            r->bt_pressed_ts,
            r->bt_released_ts,
            r->vcc_mv
        );
    }
    uart_tx_flush();
}

void stat_help(void)
{
    uart_printf("Stat command (s) output consists of heading line followed by %u channel stat lines" UART_EOL, MAX_GR_ROLES);
    uart_printf("Heading line: group current_timestamp" UART_EOL);
    uart_printf("  the group identify radio frequency being used for communications:" UART_EOL);
    uart_printf("    0 - 24%02uMHz, 1 - 24%02uMHz" UART_EOL, GR0_CH, GR1_CH);
    uart_printf("Stat line: epoch first_ts last_ts rep_total rep_received sn ts bt_pressed pressed_ts released_ts vcc" UART_EOL);
    uart_printf("  epoch is a number incremented every time the transmitting module restart is detected" UART_EOL);
    uart_printf("  zero epoch means the corresponding module was never active" UART_EOL);
    uart_printf("  first_ts and last_ts are timestamps of first and last report received in current epoch" UART_EOL);
    uart_printf("  rep_total and rep_received are number of report messages in current epoch" UART_EOL);
    uart_printf("  sn is the last report sequence number" UART_EOL);
    uart_printf("  ts is the last report timestamp as reported by sender" UART_EOL);
    uart_printf("  bt_pressed pressed_ts released_ts are button status and the timestamps of its first press / last release" UART_EOL);
    uart_printf("  vcc is the transmitter power voltage measured in millivolts" UART_EOL);
    uart_printf("  all timestamps are measured in 1/1024 sec units" UART_EOL);
    uart_tx_flush();
}
