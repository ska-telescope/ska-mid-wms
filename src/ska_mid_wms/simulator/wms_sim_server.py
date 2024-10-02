# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid WMS project
#
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module provides a simulator server for the Weather Monitoring System (WMS)."""
import argparse
import asyncio
import logging

from pymodbus.server import ModbusSimulatorServer

from ska_mid_wms.simulator import wms_sim

logging.basicConfig(level=logging.INFO)
_module_logger = logging.getLogger(__name__)


class WMSSimulatorServer:
    """Simulate the h/w for a Weather Station by responding to Modbus requests."""

    def __init__(
        self,
        config_path: str,
        server_name: str,
        device_name: str,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialise the simulator server.

        :param config_path: path to a configuration file
        :param server_name: name of server in config file
        :param device_name: name of device in config file
        :param logger: Logger object to use (optional)
        """
        self.server = ModbusSimulatorServer(
            modbus_server=server_name,
            modbus_device=device_name,
            json_file=config_path,
            custom_actions_module="ska_mid_wms.simulator.wms_sim",
        )
        self.logger = logger or _module_logger

    async def start(self, only_start: bool) -> None:
        """Start the simulator.

        :param only_start: set to True to return after starting.
        """
        self.logger.info("Starting Modbus simulator server...")
        try:
            await self.server.run_forever(only_start=only_start)
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error(f"Error starting Modbus server, reason: {e}")

    async def stop(self) -> None:
        """Stop the simulator."""
        self.logger.info("Stopping Modbus simulator server...")
        await self.server.stop()

    def start_simulator_threads(self) -> None:
        """Start generating changing data."""
        wms_sim.simulator.start_sim_threads()

    def stop_simulator_threads(self) -> None:
        """Stop generating changing data."""
        wms_sim.simulator.stop_sim_threads()


async def main(argv: list[str]) -> None:
    """Create and start the Modbus simulator server.

    :param argv: command line arguments.
    """
    parser = argparse.ArgumentParser(
        prog="WMS Simulation Server",
        description="Starts a Modbus server for the Weather "
        " Monitoring System simulation",
    )
    parser.add_argument(
        "-c",
        "--config",
        help="path to a json configuration file (see Pymodbus for specification)",
        required=True,
    )
    parser.add_argument("-s", "--server", help="name of server to start", required=True)
    parser.add_argument(
        "-d", "--device", help="name of device to simulate", required=True
    )
    args = parser.parse_args(argv)
    server = WMSSimulatorServer(
        config_path=args.config,
        server_name=args.server,
        device_name=args.device,
    )
    server.start_simulator_threads()
    try:
        await server.start(False)
    except KeyboardInterrupt:
        _module_logger.info("Received keyboard interrupt, shutting down.")
    finally:
        await server.stop()
        _module_logger.info("Successfully shutdown the simulator.")


if __name__ == "__main__":
    import sys

    asyncio.run(main(sys.argv[1:]))
