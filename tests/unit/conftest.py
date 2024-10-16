# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid WMS project
#
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module provides test fixtures for the Weather Monitoring System."""

import importlib
import logging
from logging import Logger
from typing import AsyncGenerator, Dict, Generator

import pytest
from pymodbus.client import AsyncModbusTcpClient

from ska_mid_wms.simulator import (
    WMSSimSensor,
    WMSSimulator,
    WMSSimulatorServer,
    wms_sim,
)
from ska_mid_wms.wms_interface import WeatherStation


@pytest.fixture(name="simulated_sensor")
def simulated_sensor_fixture() -> WMSSimSensor:
    """
    Fixture to return a WMSSimSensor object.

    :return: a WMSSimSensor to be used in these tests.
    """
    return WMSSimSensor(0, 100, 21678, 1)


@pytest.fixture(name="simulator")
def simulator_fixture() -> Generator[WMSSimulator, None, None]:
    """
    Fixture to return the WMSSimulator object to access the simulation directly.

    :return: the WMSSimulator object to be used in these tests.
    """
    importlib.reload(wms_sim)  # Reload so we re-initialise the simulator each time
    yield wms_sim.simulator
    wms_sim.simulator.stop_sim_threads()


@pytest.fixture(name="simulator_config", scope="module")
def simulator_config_fixture() -> Dict[str, str]:
    """
    Fixture to provide the configuration for the simulator.

    :return: simulator configuration dictionary.
    """
    return {
        "config_path": "tests/data/wms_simulation.json",
        "server_name": "WMSServer",
        "device_name": "station1",
    }


@pytest.fixture(scope="session", name="logger")
def logger_fixture() -> logging.Logger:
    """
    Fixture that returns a default logger.

    The logger will be set to DEBUG level.

    :returns: a logger.
    """
    debug_logger = logging.getLogger()
    debug_logger.setLevel(logging.DEBUG)
    return debug_logger


@pytest.fixture(name="wms_simulator_server")
async def wms_simulator_server_fixture(
    simulator_config: Dict[str, str],
    simulator: WMSSimulator,
) -> AsyncGenerator[WMSSimulatorServer, None]:
    """Fixture that starts a WMS simulator server."""
    assert simulator is not None
    server = WMSSimulatorServer(
        config_path=simulator_config["config_path"],
        server_name=simulator_config["server_name"],
        device_name=simulator_config["device_name"],
    )
    await server.start(True)
    yield server
    await server.stop()


@pytest.fixture(name="wms_client")
async def wms_client_fixture(
    wms_simulator_server: WMSSimulatorServer,
) -> AsyncGenerator[AsyncModbusTcpClient, None]:
    """Fixture that creates a TCP client and connects to the Modbus server.

    :param wms_simulator: a running WMS Simulator Server
    """
    assert wms_simulator_server is not None
    client = AsyncModbusTcpClient("localhost", port=502, timeout=5)
    await client.connect()
    yield client
    client.close()


@pytest.fixture(name="weather_station")
async def wms_interface_fixture(
    wms_simulator_server: WMSSimulatorServer, logger: Logger
) -> AsyncGenerator[WeatherStation, None]:
    """Fixture that creates a WeatherStation and connects it to a running simulation.

    :param wms_simulator_server: a running WMS Simulator Server
    """
    assert wms_simulator_server is not None
    weather_station = await WeatherStation.create_weather_station("", logger)
    await weather_station.connect()
    yield weather_station
    weather_station.disconnect()
