# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid WMS project
#
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module provides a simulator server for the Weather Monitoring System (WMS)."""
import asyncio
import logging

from pymodbus.server import ModbusSimulatorServer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


class WMSSimulatorServer:
    """Simulate the h/w for a Weather Station by responding to Modbus requests."""

    def __init__(self, config_path: str) -> None:
        """Initialise the simulator server.

        :param config_path: path to a configuration file
        """
        self.simulator = ModbusSimulatorServer(
            modbus_server="WMSServer",
            modbus_device="station1",
            json_file=config_path,
            custom_actions_module="ska_mid_wms.simulator.wms_sim",
        )

    async def start(self, only_start: bool) -> None:
        """Start the simulator.

        :param only_start: set to True to return after starting.
        """
        logger.info("Starting Modbus simulator server...")
        await self.simulator.run_forever(only_start=only_start)

    async def stop(self) -> None:
        """Stop the simulator."""
        logger.info("Stopping Modbus simulator server...")
        await self.simulator.stop()


async def main(*args: str) -> None:
    """Create and start the Modbus simulator server."""
    server = WMSSimulatorServer(*args)
    try:
        await server.start(False)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down.")
    finally:
        await server.stop()
        logging.info("Successfully shutdown the simulator.")


if __name__ == "__main__":
    import sys

    asyncio.run(main(sys.argv[1]))
