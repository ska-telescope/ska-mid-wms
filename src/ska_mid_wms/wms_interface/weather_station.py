# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid WMS project
#
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module provides the interface to a Weather Station."""

from __future__ import annotations

import asyncio
import functools
import logging
from asyncio import Task
from asyncio.queues import Queue
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Final

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

ADC_FULL_SCALE: Final = 2**16 - 1  # Max value produced by the ADC in raw counts


@dataclass
@functools.total_ordering
class Sensor:
    """This class encapsulates a single Weather Station sensor."""

    modbus_address: int
    name: str
    description: str
    unit: str
    scale_high: float
    scale_low: float

    @property
    def range(self) -> float:
        """Return the range in engineering units."""
        return self.scale_high - self.scale_low

    def convert_raw_adc(self, adc_val: int) -> float:
        """Convert a raw ADC value into engineering units.

        :param adv_val: Raw input value
        :return: Converted value in engineering units.
        """
        return (adc_val / ADC_FULL_SCALE) * self.range + self.scale_low

    def __lt__(self, other: Sensor) -> bool:
        """Check if less than another Sensor object.

        :param other: other Sensor object to compare with
        :return: True if this Sensor's modbus address is less than the other's.
        """
        return self.modbus_address < other.modbus_address

    def __eq__(self, other: Any) -> bool:
        """Check if equal to another object.

        :param other: other Sensor object to compare with
        :return: True if this Sensor's modbus address is the same as another's.
        """
        if not isinstance(other, Sensor):
            return False
        return self.modbus_address == other.modbus_address


@dataclass
class WMSDatapoint:
    """Class to encapsulate a single datapoint."""

    sensor: Sensor  # sensor this corresponds to
    raw_value: int  # raw value read from the h/w
    timestamp: datetime  # timestamp of the reading


class SensorEnum(Enum):
    """Enumeration type for Sensors."""

    WIND_SPEED = "wind_speed"
    WIND_DIRECTION = "wind_direction"
    TEMPERATURE = "temperature"
    PRESSURE = "pressure"
    HUMIDITY = "humidity"
    RAINFALL = "rainfall"


class WMSPoller:
    """Class to implement polling the WMS hardware."""

    def __init__(
        self,
        client: AsyncModbusTcpClient,
        logger: logging.Logger,
        sensors: list[Sensor],
        poll_interval: float = 1,
    ) -> None:
        """Initialise the instance."""
        self._client = client
        self._logger = logger
        self._stop_polling_request: bool = True  # Don't start polling immediately
        self._poll_task: Task = asyncio.create_task(self._poll())
        self._read_requests: list[
            list[Sensor]
        ]  # Each Modbus request is a list of sensors with contiguous registers
        self.data_queue: Queue = Queue()
        self.poll_interval = poll_interval
        self.update_request_list(sensors)

    async def _poll(self) -> None:
        """Poll the hardware periodically for new data."""
        while True:
            # Each request is a list of Sensors with contiguous addresses
            for request in self._read_requests:
                if self._stop_polling_request:
                    break
                start_address = request[0].modbus_address
                read_count = len(request)
                try:
                    result = await self._client.read_input_registers(
                        start_address, read_count
                    )
                except ModbusException as e:
                    self._logger.error(f"{e}")
                    continue

                if result.isError():
                    self._logger.error(f"Received Modbus error: {result}")
                    continue

                self._logger.debug(
                    f"Read {read_count} registers from address "
                    f"{start_address}: {result.registers}"
                )
                new_data: list[WMSDatapoint] = []
                for index, value in enumerate(result.registers):
                    new_data.append(
                        WMSDatapoint(request[index], value, datetime.now(timezone.utc))
                    )
                await self._push_data(new_data)
            await asyncio.sleep(self.poll_interval)

    def update_request_list(self, sensors: list[Sensor]) -> None:
        """Update the Modbus request list.

        Update the Modbus request list by creating the necessary list
        of Modbus reads to ensure contiguous registers are read in the
        same operation.
        :param sensors: list of Sensors to be polled, in any order.
        """
        # Empty the request list and rebuild from scratch
        self._read_requests = []

        # Sort the list of sensors by modbus address
        sorted_sensors: list[Sensor] = sorted(sensors)
        current_request: list[Sensor] = [sorted_sensors[0]]

        for i, sensor in enumerate(sorted_sensors[1:], start=1):
            if sensor.modbus_address == sorted_sensors[i - 1].modbus_address + 1:
                current_request.append(sensor)
            else:
                # Sensor is not contiguous so create a new request
                self._read_requests.append(current_request)
                current_request = [sensor]

        self._read_requests.append(current_request)

    def start(self) -> None:
        """Start polling the weather station data."""
        self._stop_polling_request = False

    def stop(self) -> None:
        """Stop polling the weather station data."""
        self._stop_polling_request = True

    async def _push_data(self, data: list[WMSDatapoint]) -> None:
        """Push new data to a queue for the publish task to consume.

        :param data: dictionary mapping sensors to raw values
        """
        converted_data: Dict[str, Dict[str, Any]] = {}
        for datapoint in data:
            converted_data[datapoint.sensor.name] = {
                "value": datapoint.sensor.convert_raw_adc(datapoint.raw_value),
                "units": datapoint.sensor.unit,
                "timestamp": datapoint.timestamp,
            }
        await self.data_queue.put(converted_data)


class WMSPublisher:
    """Class to implement publishing the new data to subscribed clients."""

    def __init__(self, publish_queue: Queue, logger: logging.Logger) -> None:
        """Initialise the instance.

        :param data_queue: The queue to retrieve new data from.
        """
        self._publish_queue = publish_queue
        self._logger = logger
        self._subscriptions: Dict[int, Callable] = {}
        self._subscription_counter: int = 0
        self._publish_task: Task = asyncio.create_task(self._publish())

    async def _publish(self):
        while True:
            next_item = await self._publish_queue.get()
            for _, callback in self._subscriptions.items():
                callback(next_item)
            self._publish_queue.task_done()

    def subscribe(self, callback: Callable) -> int:
        """Subscribe to data updates.

        :param callback: Function to call when new data is available.
        :return: The subscription id.
        """
        self._subscription_counter += 1
        self._subscriptions[self._subscription_counter] = callback
        return self._subscription_counter

    def unsubscribe(self, subscription_id: int) -> None:
        """Unsubscribe from data updates.

        :param subscription_id: The subscription id to remove.
        """
        del self._subscriptions[subscription_id]


class WeatherStation:
    """Class to implement the Modbus interface to a Weather Station."""

    @classmethod
    async def create_weather_station(
        cls, config_file: str, logger: logging.Logger
    ) -> WeatherStation:
        """Create and return a WeatherStation.

        :param config_file: Path to a configuration yaml file.
        :param logger: A logging object.
        """
        weather_station = WeatherStation(config_file, logger)
        await weather_station._init()
        return weather_station

    def __init__(self, config_file: str, logger: logging.Logger) -> None:
        """Initialise the instance.

        :param config_file: Path to a configuration yaml file.
        :param logger: A logging object.
        """
        # TODO: Read the host and port from a configuration file (WOM-503)
        logger.info(f"Reading configuration file {config_file}")

        self._sensors: list[Sensor] = []
        self._create_sensors()
        self._logger = logger
        self._polling: bool = False

        self._client: AsyncModbusTcpClient
        self._poller: WMSPoller
        self._publisher: WMSPublisher

    async def _init(self):
        self._client = AsyncModbusTcpClient("localhost", port=502)
        await self.connect()
        self._logger.info("Connected Modbus TCP client to address localhost, port 502")

        self._poller = WMSPoller(self._client, self._logger, self._sensors)
        self._publisher = WMSPublisher(self._poller.data_queue, self._logger)

    @property
    def poll_interval(self) -> float:
        """Polling interval, in seconds."""
        return self._poller.poll_interval

    @poll_interval.setter
    def poll_interval(self, new_value: float) -> None:
        self._poller.poll_interval = new_value

    def _create_sensors(self) -> None:
        """Create the Sensor objects from the configuration."""
        # TODO: Read info from configuration file
        self._sensors = [
            Sensor(15, "wind_speed", "Wind speed", "m/s", 70, 0),
            Sensor(16, "wind_direction", "Wind direction", "degrees", 360, 0),
            Sensor(17, "temperature", "Temperature", "Deg C", 50, -10),
            Sensor(18, "pressure", "Pressure", "mbar", 1100, 600),
            Sensor(19, "humidity", "Humidity", "%", 100, 0),
            Sensor(20, "rainfall", "Rainfall", "mm", 500, 0),
        ]

    def configure_poll_sensors(self, sensors_to_poll: list[SensorEnum]) -> None:
        """Configure the subset of sensors to poll.

        :param sensors: List of sensors to poll.
        """
        sensor_names = [sensor.value for sensor in sensors_to_poll]
        self._poller.update_request_list(
            [sensor for sensor in self._sensors if sensor.name in sensor_names]
        )

    def subscribe_data(self, callback: Callable) -> int:
        """Subscribe to data updates.

        :param callback: Function to call when new data is available.
        :return: The subscription id.
        """
        return self._publisher.subscribe(callback)

    def unsubscribe_data(self, subscription_id: int) -> None:
        """Unsubscribe from data updates.

        :param id: The id to unsubscribe.
        """
        self._publisher.unsubscribe(subscription_id)

    # def subscribe_error(self, callback: Callable) -> int:
    #     """Subscribe to error updates.

    #     :param callback: Function to call when an error occurs.
    #     :return: The subscription id.
    #     """
    #     # TODO - WOM-504

    # def unsubscribe_error(self, subscription_id: int) -> None:
    #     """Unsubscribe from error updates.

    #     :param id: The id to unsubscribe.
    #     """
    #     # TODO - WOM-504

    async def connect(self) -> None:
        """Connect to the device."""
        await self._client.connect()

    def disconnect(self) -> None:
        """Disconnect from the device."""
        self.stop_polling()
        self._client.close()

    async def start_polling(self) -> None:
        """Start polling the weather station data."""
        if not self._client.connected:
            await self.connect()
        self._polling = True
        self._poller.start()

    def stop_polling(self) -> None:
        """Stop polling the weather station data."""
        self._poller.stop()
        self._polling = False
