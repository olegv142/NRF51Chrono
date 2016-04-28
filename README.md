This is the multichannel chronometry system designed to measure time taken to pass the lanes between start and finish gates.
The time counter is started upon releasing button on the start gate and stopped upon pressing button on the finish gate.
The gates are continuously reporting their status to receiver module using proprietary RF protocol at raw bit rate of 
250 kbit/sec. The receiver module provides simple UART protocol for reporting collected status data to the host. The python
application program running on the host is able to visualize gates status information and collect time data.

Both start and finish gates are using NRF51822 modules running identical firmware. The module role is being set by jumpers
connected to module IO pads. The receiver module is using the same NRF module paired with FT232RL USB-serial adaptor operating
at 115200 baud rate.
