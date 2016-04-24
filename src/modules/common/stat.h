#pragma once

#include "role.h"
#include "packet.h"

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

// Statistic reported to the client
struct stat {
    // The group number (0 - 2400MHz, 1 - 2403MHz)
    unsigned group;
    // Current timestamp
    unsigned current_ts;
    // Array of transmitters stat
    struct stat_entry entry[MAX_GR_ROLES];
};

void stat_init(unsigned group);

// Update stat on new report arrival
void stat_update(struct report_packet const* r);

// Print stat to UART
void stat_dump(void);
