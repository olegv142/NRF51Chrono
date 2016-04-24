#include "stat.h"
#include "uart.h"

/*static*/ struct stat_entry g_stat_entry[MAX_GR_ROLES];
/*static*/ unsigned g_stat_group;

void stat_init(unsigned group)
{
    g_stat_group = group;
}

// Update stat on new report arrival
void stat_update(struct report_packet const* r)
{
}

// Print stat to UART
void stat_dump(void)
{
        uart_printf("stat TBD" UART_EOL);
        uart_tx_flush();
}


