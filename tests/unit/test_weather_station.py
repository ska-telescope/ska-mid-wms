# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid WMS project
#
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module provides unit tests for the WeatherStation class."""

import asyncio
from unittest.mock import MagicMock

import pytest

from ska_mid_wms.wms_interface import WeatherStation


class TestWeatherStation:
    """Test the interface to the WeatherStation."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_subscribe_data(
        self,
        weather_station: WeatherStation,
    ) -> None:
        """Test we can subscribe to data updates.

        :param weather_station: A WeatherStation connected to a running simulation.
        """
        callback = MagicMock()
        weather_station.subscribe_data(callback)
        await weather_station.start_polling()
        await asyncio.sleep(weather_station.poll_interval * 2)
        callback.assert_called()

    @pytest.mark.asyncio(loop_scope="function")
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
