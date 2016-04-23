#pragma once

#define ROLE_MASTER (1<<8)
#define MAX_SLAVE_ROLES 8

unsigned role_get(void);
