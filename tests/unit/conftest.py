# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid WMS project
#
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module provides test fixtures for the Weather Monitoring System."""

import importlib
from typing import AsyncGenerator, Generator

import pytest
from pymodbus.client import AsyncModbusTcpClient

from ska_mid_wms.simulator import (
    WMSSimSensor,
    WMSSimulator,
    WMSSimulatorServer,
    wms_sim,
)


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


@pytest.fixture(name="simulator_config_path", scope="module")
def simulator_config_path_fixture() -> str:
    """
    Fixture to provide the path to the simulator configuration file.

    :return: path to the simulator configuration file to be used in these tests.
    """
    return "tests/data/wms_simulation.json"


@pytest.fixture(name="wms_simulator_server")
async def wms_simulator_server_fixture(
    simulator_config_path: str,
    simulator: WMSSimulator,
) -> AsyncGenerator[WMSSimulatorServer, None]:
    """Fixture that starts a WMS simulator server."""
    assert simulator is not None
    server = WMSSimulatorServer(simulator_config_path)
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
