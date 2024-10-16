# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid WMS project
#
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module provides a WeatherStation class."""

import logging
import queue
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Thread
from typing import Callable

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

from .sensor import Sensor

# from pymodbus.pdu import ModbusResponse
# from pymodbus.pdu.register_read_message import ReadInputRegistersResponse


@dataclass
class WMSDatapoint:
    """Class to encapsulate a single datapoint."""

    sensor: Sensor  # sensor this corresponds to
    raw_value: int  # raw value read from the h/w
    timestamp: datetime  # timestamp of the reading


class WMSPoller:
    """Class to implement polling the WMS hardware."""

    def __init__(self, client: ModbusTcpClient, logger: logging.Logger) -> None:
        """Initialise the instance."""
        self._client = client
        self._logger = logger
        self._poll_thread: Thread = Thread(target=self._poll)
        self._stop_polling_request: bool = False
        self._read_requests: list[
            list[Sensor]
        ]  # Each Modbus request is a list of sensors with contiguous registers
        self._data_queue: queue.Queue = queue.Queue()
        self._poll_interval: float = 1

    def _poll(self) -> None:
        """Poll the hardware periodically for new data."""
        while True:
            if not self._stop_polling_request:
                for request in self._read_requests:
                    start_address = request[0].modbus_address
                    read_count = len(request)
                    try:
                        result = self._client.read_input_registers(
                            start_address, read_count
                        )
                    except ModbusException as e:
                        self._logger.error(f"Error reading input registers: {e}")
                        continue
                    self._logger.debug(
                        f"Read {read_count} registers from address "
                        f"{start_address}: {result.registers}"
                    )
                    new_data: list[WMSDatapoint] = []
                    for index, value in enumerate(result.registers):
                        new_data.append(
                            WMSDatapoint(
                                request[index], value, datetime.now(timezone.utc)
                            )
                        )
                    self._push_data(new_data)
            time.sleep(self._poll_interval)

    def update_sensor_list(self, sensors: list[Sensor]) -> None:
        """Update the list of sensors to be polled.

        :param: sensors: list of Sensors to be polled.
        """
        # Empty the request list and rebuild from scratch
        # TODO: Combine contiguous addresses into a single read request
        self._read_requests = []
        for sensor in sensors:
            self._read_requests.append([sensor])

    def start(self) -> None:
        """Start polling the weather station data."""
        self._stop_polling_request = False
        if not self._poll_thread.is_alive():
            self._poll_thread.start()

    def stop(self) -> None:
        """Stop polling the weather station data."""
        self._stop_polling_request = True

    def _push_data(self, data: list[WMSDatapoint]) -> None:
        """Push new data to a queue for the publish thread to consume.

        :param data: dictionary mapping sensors to raw values
        """
        for datapoint in data:
            converted_value = datapoint.sensor.convert_raw_adc(datapoint.raw_value)
            self._data_queue.put(
                {
                    datapoint.sensor.name: {
                        "value": converted_value,
                        "units": datapoint.sensor.unit,
                        "timestamp": datapoint.timestamp,
                    }
                }
            )


class WeatherStation:
    """Class to implement the Modbus interface to a Weather Station."""

    def __init__(self, config_file: str, logger: logging.Logger) -> None:
        """Initialise the instance.

        :param config_file: Path to a configuration yaml file.
        """
        # TODO: Read the host and port from the configuration file
        self._client = ModbusTcpClient("localhost", port=502)
        logger.info("Created Modbus TCP client for address localhost, port 502")

        self._sensors: list[Sensor] = []
        self._create_sensors()
        self._poller = WMSPoller(self._client, logger)

        self.configure_poll_sensors(self._sensors)

    @property
    def poll_interval(self) -> float:
        """Polling interval, in seconds."""
        return self._poll_interval

    @poll_interval.setter
    def poll_interval(self, new_value: float) -> None:
        self._poll_interval = new_value

    def _create_sensors(self) -> None:
        """Create the Sensor objects from the configuration."""
        # TODO: Read info from configuration file
        self._sensors = [
            Sensor(15, "wind_speed", "Wind speed", "m/s", 70, 0),
            Sensor(16, "wind_direction", "Wind direction", "degrees", 360, 0),
        ]

    # TODO: Convert to accept list of Enums
    def configure_poll_sensors(self, sensors: list[Sensor]) -> None:
        """Configure the subset of sensors to poll.

        :param sensors: List of sensors to poll.
        """
        self._poller.update_sensor_list(sensors)

    def subscribe_data(self, callback: Callable) -> int:
        """Subscribe to data updates.

        :param callback: Function to call when new data is available.
        :return: The subscription id.
        """
        return 0

    def unsubscribe_data(self, subscription_id: int) -> None:
        """Unsubscribe from data updates.

        :param id: The id to unsubscribe.
        """

    def subscribe_error(self, callback: Callable) -> int:
        """Subscribe to error updates.

        :param callback: Function to call when an error occurs.
        :return: The subscription id.
        """
        return 0

    def unsubscribe_error(self, subscription_id: int) -> None:
        """Unsubscribe from error updates.

        :param id: The id to unsubscribe.
        """

    def connect(self) -> None:
        """Connect to the device."""
        self._client.connect()

    def disconnect(self) -> None:
        """Disconnect from the device."""
        self._client.close()

    def start_polling(self) -> None:
        """Start polling the weather station data."""
        if not self._client.connected:
            self.connect()
        self._poller.start()

    def stop_polling(self) -> None:
        """Stop polling the weather station data."""
        self._poller.stop()
