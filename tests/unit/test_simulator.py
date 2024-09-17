# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid WMS project
#
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module provides unit tests for the Weather Monitoring System simulation."""
from typing import AsyncGenerator

import pytest
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.pdu import ModbusExceptions
from pymodbus.pdu.mei_message import ReadDeviceInformationResponse
from pymodbus.pdu.pdu import ExceptionResponse
from pymodbus.pdu.register_read_message import ReadInputRegistersResponse

from ska_mid_wms.simulator import WMSSimulatorServer


@pytest.fixture(name="simulator_config_path", scope="session")
def simulator_config_path_fixture() -> str:
    """
    Fixture to provide the path to the simulator configuration file.

    :return: path to the simulator configuration file to be used in these tests.
    """
    return "tests/data/wms_simulation.json"


@pytest.fixture(name="wms_simulator", scope="module")
async def wms_simulator_fixture(
    simulator_config_path: str,
) -> AsyncGenerator[WMSSimulatorServer, None]:
    """Fixture that starts a WMS simulator server."""
    server = WMSSimulatorServer(simulator_config_path)
    await server.start(True)
    yield server
    await server.stop()


@pytest.fixture(name="wms_client", scope="module")
async def wms_client_fixture(
    wms_simulator: WMSSimulatorServer,
) -> AsyncGenerator[AsyncModbusTcpClient, None]:
    """Fixture that creates a TCP client and connects to the Modbus server.

    :param wms_simulator: a running WMS Simulator Server
    """
    assert wms_simulator is not None
    client = AsyncModbusTcpClient("localhost", port=502)
    await client.connect()
    yield client
    client.close()


class TestWMSSimulator:
    """Test the WMS Simulator."""

    @pytest.mark.asyncio(loop_scope="module")
    async def test_read_device_info(self, wms_client: AsyncModbusTcpClient) -> None:
        """Test we can read the device info.

        :param wms_client: a Modbus TCP client connected to the simulation server.
        """
        assert wms_client.connected
        deviceinfo = await wms_client.read_device_information()
        assert isinstance(deviceinfo, ReadDeviceInformationResponse)
        assert deviceinfo.information[0].decode("ASCII") == "ACROMAG"
        assert deviceinfo.information[1].decode("ASCII") == "961EN-4006"

    @pytest.mark.asyncio(loop_scope="module")
    async def test_read_uint16(self, wms_client: AsyncModbusTcpClient) -> None:
        """Test we can read the six sensor registers.

        :param wms_client: a Modbus TCP client connected to the simulation server.
        """
        assert wms_client.connected

        # Read 6 registers from address 15 on slave 1
        response = await wms_client.read_input_registers(15, 6, 1)
        assert isinstance(response, ReadInputRegistersResponse)
        assert response.registers == [126, 22251, 153, 8192, 943, 117]

    @pytest.mark.asyncio(loop_scope="module")
    async def test_read_invalid_register(
        self, wms_client: AsyncModbusTcpClient
    ) -> None:
        """Test reading an invalid register.

        :param wms_client: a Modbus TCP client connected to the simulation server.
        """
        assert wms_client.connected

        # Read 1 register at address 1 on slave 1
        response = await wms_client.read_input_registers(1, 1, 1)
        assert isinstance(response, ExceptionResponse)
        assert response.exception_code == ModbusExceptions.IllegalAddress
