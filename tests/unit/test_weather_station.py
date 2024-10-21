# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid WMS project
#
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module provides unit tests for the WeatherStation class."""

import asyncio
from datetime import datetime
from typing import Dict
from unittest.mock import MagicMock

import pytest

from ska_mid_wms.wms_interface import SensorEnum, WeatherStation


class TestWeatherStation:
    """Test the interface to the WeatherStation."""

    @pytest.mark.asyncio()
    async def test_subscribe_data(
        self,
        weather_station: WeatherStation,
        expected_callback_data_full: list[Dict[str, str]],
    ) -> None:
        """Test we can subscribe to data updates.

        :param weather_station: A WeatherStation connected to a running simulation.
        :param expected_callback_data_full: The full set of expected callback data.
        """
        callback = MagicMock()
        weather_station.subscribe_data(callback)
        await weather_station.start_polling()
        await asyncio.sleep(
            weather_station.poll_interval + weather_station.poll_interval / 2
        )
        assert callback.call_count == len(expected_callback_data_full)

        for call, expected_results in zip(
            callback.call_args_list,
            expected_callback_data_full,
        ):
            assert isinstance(call.args[0], dict)
            assert expected_results["name"] in call.args[0]
            value_dict = call.args[0][expected_results["name"]]
            assert isinstance(value_dict["timestamp"], datetime)
            assert isinstance(value_dict["value"], float)
            assert value_dict["units"] == expected_results["units"]

    @pytest.mark.asyncio()
    async def test_unsubscribe_data(
        self,
        weather_station: WeatherStation,
    ) -> None:
        """Test we can unsubscribe.

        :param weather_station: A WeatherStation connected to a running simulation.
        """
        callback = MagicMock()
        subscription_id = weather_station.subscribe_data(callback)
        await weather_station.start_polling()
        await asyncio.sleep(weather_station.poll_interval * 2)
        weather_station.unsubscribe_data(subscription_id)
        callback.assert_called()
        call_count = callback.call_count
        await asyncio.sleep(weather_station.poll_interval * 10)
        # Check we have not received any more callbacks
        assert callback.call_count == call_count

    @pytest.mark.asyncio()
    async def test_start_stop_polling(
        self,
        weather_station: WeatherStation,
    ) -> None:
        """Test we can start and stop polling.

        :param weather_station: A WeatherStation connected to a running simulation.
        """
        callback = MagicMock()
        weather_station.subscribe_data(callback)
        await weather_station.start_polling()
        await asyncio.sleep(
            weather_station.poll_interval + weather_station.poll_interval / 2
        )
        weather_station.stop_polling()
        callback.assert_called()
        call_count = callback.call_count
        await asyncio.sleep(weather_station.poll_interval * 10)
        # Check we have not received any more callbacks
        assert callback.call_count == call_count

        await weather_station.start_polling()
        await asyncio.sleep(
            weather_station.poll_interval + weather_station.poll_interval / 2
        )
        assert callback.call_count > call_count

    @pytest.mark.asyncio()
    @pytest.mark.parametrize(
        "sensor_list",
        [
            [SensorEnum.TEMPERATURE, SensorEnum.RAINFALL],
            [SensorEnum.WIND_DIRECTION, SensorEnum.PRESSURE, SensorEnum.HUMIDITY],
            [SensorEnum.WIND_SPEED],
        ],
    )
    async def test_configure_sensors(
        self,
        weather_station: WeatherStation,
        sensor_list: list[SensorEnum],
        expected_callback_data: list[Dict[str, str]],
    ) -> None:
        """Test we can configure a subset of sensors to poll.

        :param weather_station: A WeatherStation connected to a running simulation.
        :param sensor_list: A list of non-contiguous Sensors to poll.
        :param expected_callback_data: The expected callback data.
        """
        callback = MagicMock()
        weather_station.subscribe_data(callback)
        weather_station.configure_poll_sensors(sensor_list)
        await weather_station.start_polling()
        await asyncio.sleep(
            weather_station.poll_interval + weather_station.poll_interval / 2
        )
        assert callback.call_count == len(sensor_list)

        for call, expected_results in zip(
            callback.call_args_list,
            expected_callback_data,
        ):
            assert isinstance(call.args[0], dict)
            assert expected_results["name"] in call.args[0]
            value_dict = call.args[0][expected_results["name"]]
            assert isinstance(value_dict["timestamp"], datetime)
            assert isinstance(value_dict["value"], float)
            assert value_dict["units"] == expected_results["units"]
