# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid WMS project
#
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module provides unit tests for the Weather Monitoring System simulation."""
import pytest
from pymodbus.client import AsyncModbusTcpClient

from ska_mid_wms.simulator import WMSSimulatorServer


@pytest.fixture(name="simulator_config_path", scope="session")
def simulator_config_path_fixture() -> str:
    """
    Return the path to the simulator configuration file to be used in these tests.

    :return: path to the simulator configuration file to be used in these tests.
    """
    return "tests/data/wms_simulation.json"


@pytest.fixture(name="wms_simulator")
async def wms_simulator_fixture(simulator_config_path: str) -> WMSSimulatorServer:
    """Fixture that starts a WMS simulator server."""
    server = WMSSimulatorServer(simulator_config_path)
    await server.start(True)
    yield server
    await server.stop()


class TestWMSSimulator:
    """Test the WMS Simulator."""

    @pytest.mark.asyncio()
    async def test_read_unit16(self, wms_simulator: WMSSimulatorServer) -> None:
        """Test we can read the six sensor registers.

        :param wms_simulator: a WMSSimlator fixture
        """
        client = AsyncModbusTcpClient("localhost", port=502)
        await client.connect()
        assert client.connected
        deviceinfo = await client.read_device_information()
        assert deviceinfo.information[0].decode("ASCII") == "ACROMAG"

        client.close()

    def test_read_invalid_register(self):
        """Test reading an invalid register."""
        assert 1
