# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid WMS project
#
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module provides unit tests for the Weather Monitoring System simulation."""
import time
from typing import List

import pytest
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.pdu import ModbusExceptions
from pymodbus.pdu.mei_message import ReadDeviceInformationResponse
from pymodbus.pdu.pdu import ExceptionResponse
from pymodbus.pdu.register_read_message import ReadInputRegistersResponse

from ska_mid_wms.simulator import WMSSimSensor, WMSSimulator


class TestWMSSimulator:
    """Test the WMS Simulator."""

    @pytest.mark.parametrize(
        ["input_value", "expected_result"],
        [
            pytest.param(
                41,
                26869,
            ),
            pytest.param(
                21.4,
                14024,
            ),
            pytest.param(100, 65535),
            pytest.param(0, 0),
        ],
    )
    def test_engineering_to_raw(
        self,
        simulated_sensor: WMSSimSensor,
        input_value: float,
        expected_result: int,
    ) -> None:
        """
        Test conversion function between engineering values and register values.

        :param input: the input in engineering units
        :param expected_result: the expected result in raw ADC counts
        """
        simulated_sensor.engineering_value = input_value
        assert simulated_sensor.raw_value == expected_result

    @pytest.mark.parametrize(
        ["input_value", "expected_result"],
        [
            pytest.param(
                26869,
                41,
            ),
            pytest.param(14024, 21.4),
            pytest.param(65535, 100),
            pytest.param(0, 0),
        ],
    )
    def test_raw_to_engineering(
        self,
        simulated_sensor: WMSSimSensor,
        input_value: int,
        expected_result: float,
    ) -> None:
        """
        Test conversion function between register values and engineering values.

        :param input: the input in raw ADC counts
        :param expected_result: the expected result in engineering units.
        """
        simulated_sensor.raw_value = input_value
        assert simulated_sensor.engineering_value == pytest.approx(
            expected_result, rel=0.0001
        )

    def test_sim_data_generator(self, simulator: WMSSimulator) -> None:
        """Test the simulator generates changing data."""
        assert simulator.humidity == WMSSimulator.DEFAULT_HUMIDITY
        assert simulator.temperature == WMSSimulator.DEFAULT_TEMPERATURE
        assert simulator.rainfall == WMSSimulator.DEFAULT_RAINFALL
        assert simulator.pressure == WMSSimulator.DEFAULT_PRESSURE
        assert simulator.wind_direction == WMSSimulator.DEFAULT_WIND_DIRECTION
        assert simulator.wind_speed == WMSSimulator.DEFAULT_WIND_SPEED

        # Generate a few cycles in case the data generator happens to generate
        # the default value again

        humidity: List[bool] = []
        temperature: List[bool] = []
        rainfall: List[bool] = []
        pressure: List[bool] = []
        wind_direction: List[bool] = []
        wind_speed: List[bool] = []

        def get_new_values():
            humidity.append(simulator.humidity == WMSSimulator.DEFAULT_HUMIDITY)
            temperature.append(
                simulator.temperature == WMSSimulator.DEFAULT_TEMPERATURE
            )
            rainfall.append(simulator.rainfall == WMSSimulator.DEFAULT_RAINFALL)
            pressure.append(simulator.pressure == WMSSimulator.DEFAULT_PRESSURE)
            wind_direction.append(
                simulator.wind_direction == WMSSimulator.DEFAULT_WIND_DIRECTION
            )
            wind_speed.append(simulator.wind_speed == WMSSimulator.DEFAULT_WIND_SPEED)

        simulator.start_sim_threads()
        for _ in range(4):
            time.sleep(simulator.LONGEST_UPDATE_CYCLE)
            get_new_values()

        assert not all(humidity)
        assert not all(temperature)
        assert not all(rainfall)
        assert not all(pressure)
        assert not all(wind_direction)
        assert not all(wind_speed)

    def test_set_sim_value(self, simulator: WMSSimulator) -> None:
        """Test we can set simulation values manually."""
        simulator.wind_speed = 26700
        simulator.wind_direction = 36125
        time.sleep(
            min(
                simulator.WIND_SPEED_UPDATE_FREQUENCY,
                simulator.WIND_DIRECTION_UPDATE_FREQUENCY,
            )
            + 1
        )
        assert simulator.wind_speed == 26700
        assert simulator.wind_direction == 36125

    @pytest.mark.asyncio(loop_scope="function")
    async def test_read_device_info(self, wms_client: AsyncModbusTcpClient) -> None:
        """Test we can read the device info.

        :param wms_client: a Modbus TCP client connected to the simulation server.
        """
        assert wms_client.connected
        deviceinfo = await wms_client.read_device_information()
        assert isinstance(deviceinfo, ReadDeviceInformationResponse)
        assert deviceinfo.information[0].decode("ASCII") == "ACROMAG"
        assert deviceinfo.information[1].decode("ASCII") == "961EN-4006"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_read_uint16(
        self,
        wms_client: AsyncModbusTcpClient,
    ) -> None:
        """Test we can read the six sensor registers.

        :param wms_client: a Modbus TCP client connected to the simulation server.
        """
        assert wms_client.connected

        expected_results = [
            WMSSimulator.DEFAULT_WIND_SPEED,
            WMSSimulator.DEFAULT_WIND_DIRECTION,
            WMSSimulator.DEFAULT_TEMPERATURE,
            WMSSimulator.DEFAULT_PRESSURE,
            WMSSimulator.DEFAULT_HUMIDITY,
            WMSSimulator.DEFAULT_RAINFALL,
        ]

        # Read 6 registers from address 15 on slave 1
        response = await wms_client.read_input_registers(15, 6, 1)
        assert isinstance(response, ReadInputRegistersResponse)
        assert response.registers == expected_results

    @pytest.mark.asyncio(loop_scope="function")
    async def test_read_invalid_register(
        self, wms_client: AsyncModbusTcpClient
    ) -> None:
        """Test reading an invalid register.

        :param wms_client: a Modbus TCP client connected to the simulation server.
        """
        assert wms_client.connected

        # Read 1 register at (invalid) address 14 on slave 1
        response = await wms_client.read_input_registers(1, 14, 1)
        assert isinstance(response, ExceptionResponse)
        assert response.exception_code == ModbusExceptions.IllegalAddress
