# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid WMS project
#
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module provides a simulator for the Weather Monitoring System (WMS)."""
import asyncio
import logging

from pymodbus.server import ModbusSimulatorServer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


class WMSSimulatorServer:
    """Simulate the h/w for a Weather Station by responding to Modbus requests."""

    def __init__(self) -> None:
        """Initialise the simulator server."""
        self.simulator = ModbusSimulatorServer(
            modbus_server="WMSServer",
            modbus_device="station1",
            json_file="wms_simulation.json",
        )

    async def start(self):
        """Start the simulator."""
        logger.info("Starting Modbus simulator server...")
        await self.simulator.run_forever(only_start=False)

    async def stop(self):
        """Stop the simulator."""
        logger.info("Stopping Modbus simulator server...")
        await self.simulator.stop()


async def main():
    """Create and start the Modbus simulator server."""
    server = WMSSimulatorServer()
    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down.")
    finally:
        await server.stop()
        logging.info("Successfully shutdown the simulator.")


if __name__ == "__main__":
    asyncio.run(main())
