# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid WMS project
#
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module provides unit tests for the WeatherStation class."""

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict
from unittest.mock import MagicMock

import pytest
from freezegun import freeze_time

from ska_mid_wms.simulator import WMSSimulator, WMSSimulatorServer
from ska_mid_wms.wms_interface import SensorEnum, WeatherStation

from .conftest import Helpers


class TestWeatherStation:
    """Test the interface to the WeatherStation."""

    def test_subscribe_data(
        self,
        weather_station: WeatherStation,
        simulator: WMSSimulator,
        expected_callback_data_full: list[Dict[str, str]],
    ) -> None:
        """Test we can subscribe to data updates.

        :param weather_station: A WeatherStation connected to the Modbus server.
        :param simulator: A running simulator.
        :param expected_callback_data_full: The full set of expected callback data.
        """
        callback = MagicMock()
        # Let's generate some changing data for this test
        simulator.start_sim_threads()
        weather_station.subscribe_data(callback)
        weather_station.start_polling()
        time.sleep(weather_station.poll_interval)
        assert callback.call_count == 1  # 1 Modbus read for all contiguous registers

        for call, expected_results in zip(
            callback.call_args_list,
            expected_callback_data_full,
        ):
            assert isinstance(call.args[0], dict)
            assert expected_results["name"] in call.args[0]
            value_dict = call.args[0][expected_results["name"]]
            assert isinstance(value_dict["timestamp"], datetime)
            assert isinstance(value_dict["value"], float)
            assert value_dict["unit"] == expected_results["unit"]

    def test_unsubscribe_data(
        self,
        weather_station: WeatherStation,
    ) -> None:
        """Test we can unsubscribe.

        :param weather_station: A WeatherStation connected to a running simulation.
        """
        callback = MagicMock()
        subscription_id = weather_station.subscribe_data(callback)
        weather_station.start_polling()
        time.sleep(weather_station.poll_interval * 2)
        weather_station.unsubscribe_data(subscription_id)
        callback.assert_called()
        call_count = callback.call_count
        time.sleep(weather_station.poll_interval * 10)
        # Check we have not received any more callbacks
        assert callback.call_count == call_count

    def test_start_stop_polling(
        self,
        weather_station: WeatherStation,
    ) -> None:
        """Test we can start and stop polling.

        :param weather_station: A WeatherStation connected to a running simulation.
        """
        callback = MagicMock()
        weather_station.subscribe_data(callback)
        weather_station.start_polling()
        time.sleep(weather_station.poll_interval)
        weather_station.stop_polling()
        callback.assert_called()
        call_count = callback.call_count
        time.sleep(weather_station.poll_interval * 10)
        # Check we have not received any more callbacks
        assert callback.call_count == call_count

        weather_station.start_polling()
        time.sleep(weather_station.poll_interval)
        assert callback.call_count > call_count

    @pytest.mark.parametrize(
        "sensor_list,number_modbus_reads",
        [
            (
                [SensorEnum.TEMPERATURE, SensorEnum.RAINFALL],
                2,
            ),  # non-contiguous so two reads required
            (
                [
                    SensorEnum.WIND_SPEED,
                    SensorEnum.TEMPERATURE,
                    SensorEnum.HUMIDITY,
                    SensorEnum.RAINFALL,
                ],
                3,  # Humidity and rainfall can be read together so three reads in total
            ),
            ([SensorEnum.WIND_DIRECTION], 1),
        ],
    )
    def test_configure_sensors(
        self,
        weather_station: WeatherStation,
        sensor_list: list[SensorEnum],
        number_modbus_reads: int,
        expected_callback_data: list[Dict[str, str]],
    ) -> None:
        """Test we can configure a subset of sensors to poll.

        :param weather_station: A WeatherStation connected to a running simulation.
        :param sensor_list: A list of Sensors to poll.
        :param number of modbus reads: The number of modbus reads required.
        :param expected_callback_data: The expected callback data.
        """
        callback = MagicMock()
        weather_station.subscribe_data(callback)
        weather_station.configure_poll_sensors(sensor_list)
        weather_station.start_polling()
        time.sleep(weather_station.poll_interval)
        assert callback.call_count == number_modbus_reads

        for call, expected_results in zip(
            callback.call_args_list,
            expected_callback_data,
        ):
            assert isinstance(call.args[0], dict)
            assert expected_results["name"] in call.args[0]
            value_dict = call.args[0][expected_results["name"]]
            assert isinstance(value_dict["timestamp"], datetime)
            assert isinstance(value_dict["value"], float)
            assert value_dict["unit"] == expected_results["unit"]

    def test_configure_invalid_sensor(
        self, weather_station: WeatherStation, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test trying to configure an invalid sensor.

        :param weather_station: A WeatherStation connected to a running simulation.
        """
        sensor_list = [SensorEnum.HUMIDITY, SensorEnum.RAINFALL, "Not a sensor"]
        weather_station.configure_poll_sensors(sensor_list)  # type: ignore
        Helpers.assert_expected_logs(
            caplog,
            ["Could not configure sensors: 'Not a sensor' is not a valid sensor."],
        )

    @freeze_time("2024-01-01")
    def test_error_callbacks(
        self,
        wms_simulator_server: tuple[WMSSimulatorServer, asyncio.AbstractEventLoop],
        weather_station: WeatherStation,
    ) -> None:
        """Test the error callbacks in the event of a comms error.

        :param wms_simulator_server: A Modbus simulation server for WMS and its event
            loop (used to cause an error by stopping the server).
        :param weather_station: A WeatherStation connected to the above server.
        """
        data_callback = MagicMock()
        error_callback = MagicMock()
        weather_station.configure_poll_sensors([SensorEnum.HUMIDITY])
        weather_station.subscribe_data(data_callback, error_callback)
        # Stop the simulator server before polling.
        server = wms_simulator_server[0]
        event_loop = wms_simulator_server[1]
        _ = asyncio.run_coroutine_threadsafe(server.stop(), event_loop).result()
        weather_station.start_polling()
        time.sleep(weather_station.poll_interval)
        print("data callback calls:", data_callback.mock_calls)
        data_callback.assert_not_called()
        error_callback.assert_called_once_with(
            {
                "sensor_failures": ["humidity"],
                "message": "Received Modbus error: Modbus Error: [Input/Output] Modbus "
                "Error: [Connection] ModbusTcpClient localhost:502: Connection "
                "unexpectedly closed 0.000 seconds into read of 8 bytes without "
                "response from slave before it closed connection",
                "timestamp": datetime.now(timezone.utc),
            }
        )
