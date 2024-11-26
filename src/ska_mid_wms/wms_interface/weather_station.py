# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid WMS project
#
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module provides the interface to a Weather Station."""

from __future__ import annotations

import functools
import logging
import queue
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from threading import Event, Thread
from typing import Any, Callable, Dict, Final, Optional

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException
from yaml import YAMLError

from .weather_station_configuration import WeatherStationDict, load_configuration

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

        This comparison function is used to determine whether sensors
        have contiguous registers and therefore how many Modbus reads
        are required for a given set.

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


class WMSPoller:  # pylint: disable=too-many-instance-attributes
    """Class to implement polling the WMS hardware."""

    def __init__(
        self,
        client: ModbusTcpClient,
        slave_id: int,
        logger: logging.Logger,
        poll_interval: float = 1,
    ) -> None:
        """Initialise the instance."""
        self._client = client
        self._logger = logger
        self._stop_event: Event = Event()
        self._stop_event.set()  # Don't start polling immediately
        self._poll_thread: Thread = Thread(
            target=self._poll, args=(self._stop_event,), daemon=True
        )
        self._read_requests: list[
            list[Sensor]
        ]  # Each Modbus request is a list of sensors with contiguous registers
        self._slave_id = slave_id
        self.publish_queue: queue.Queue = queue.Queue()
        self.poll_interval = poll_interval

    def _poll(self, stop_event: Event) -> None:
        """Poll the hardware periodically for new data."""
        while True:
            if not stop_event.is_set():
                # Each request is a list of Sensors with contiguous addresses
                for request in self._read_requests:
                    start_address = request[0].modbus_address
                    read_count = len(request)
                    try:
                        result = self._client.read_input_registers(
                            start_address, read_count, self._slave_id
                        )
                    except ModbusException as e:
                        error_message = f"Caught {e}"
                        self._logger.error(error_message)
                        self._push_error(
                            request, error_message, datetime.now(timezone.utc)
                        )
                        continue

                    if result.isError():
                        error_message = f"Received Modbus error: {result}"
                        self._logger.error(error_message)
                        self._push_error(
                            request, error_message, datetime.now(timezone.utc)
                        )
                        continue

                    self._logger.debug(
                        f"Read {read_count} registers from address "
                        f"{start_address}: {result.registers}"
                    )
                    new_data: list[WMSDatapoint] = []
                    for index, value in enumerate(result.registers):
                        new_data.append(
                            WMSDatapoint(
                                request[index],
                                value,
                                datetime.now(timezone.utc),
                            )
                        )
                    self._push_data(new_data)
            time.sleep(self.poll_interval)

    def update_request_list(self, sensors: list[Sensor]) -> None:
        """Update the Modbus request list.

        Update the Modbus request list by creating the necessary list
        of Modbus reads to ensure contiguous registers are read in the
        same operation.
        :param sensors: list of Sensors to be polled, in any order.
        """
        # Empty the request list and rebuild from scratch
        self._read_requests = []
        if not sensors:
            return

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
        self._stop_event.clear()
        if not self._poll_thread.is_alive():
            self._poll_thread.start()

    def stop(self) -> None:
        """Stop polling the weather station data."""
        self._stop_event.set()

    def _push_data(self, data: list[WMSDatapoint]) -> None:
        """Push new data to a queue for the publish task to consume.

        :param data: dictionary mapping sensors to raw values
        """
        converted_data: Dict[str, Dict[str, Any]] = {}
        for datapoint in data:
            converted_data[datapoint.sensor.name] = {
                "value": datapoint.sensor.convert_raw_adc(datapoint.raw_value),
                "unit": datapoint.sensor.unit,
                "timestamp": datapoint.timestamp,
            }
        self.publish_queue.put(converted_data)

    def _push_error(
        self,
        sensor_failures: list[Sensor],
        error_message: str,
        timestamp: datetime,
    ) -> None:
        """Push error information to a queue for the publish task to consume.

        :param sensor_list: list of the Sensors which we failed to read
        :param error_message: description of the error
        :param timestamp: timestamp of the error
        """
        self.publish_queue.put(
            {
                "sensor_failures": [sensor.name for sensor in sensor_failures],
                "message": error_message,
                "timestamp": timestamp,
            }
        )


class WMSPublisher:
    """Class to implement publishing the new data to subscribed clients."""

    def __init__(self, publish_queue: queue.Queue, logger: logging.Logger) -> None:
        """Initialise the instance.

        :param publish_queue: The queue to retrieve new data from.
        """
        self._publish_queue = publish_queue
        self._logger = logger

        # The subscriptions dict maps a subscription id to
        # a data callback and optional error callback
        self._subscriptions: Dict[int, tuple[Callable, Callable | None]] = {}
        self._subscription_counter: int = 0
        self._publish_thread: Thread = Thread(target=self._publish, daemon=True)
        self._publish_thread.start()

    def _publish(self) -> None:
        while True:
            next_item = self._publish_queue.get()
            for _, callback in self._subscriptions.items():
                if "sensor_failures" in next_item:
                    # Item is an error
                    if callback[1] is not None:
                        # Error callback is optional.
                        callback[1](next_item)
                else:
                    # Item contains new data
                    callback[0](next_item)
            self._publish_queue.task_done()

    def subscribe(
        self, data_callback: Callable, error_callback: Optional[Callable]
    ) -> int:
        """Subscribe to updates.

        :param data_callback: Function to call when new data is available.
        :param error_callback: Function to call in event of a comms error.
        :return: The subscription id.
        """
        self._subscription_counter += 1
        self._subscriptions[self._subscription_counter] = (
            data_callback,
            error_callback,
        )
        return self._subscription_counter

    def unsubscribe(self, subscription_id: int) -> None:
        """Unsubscribe from all updates (data and error).

        :param subscription_id: The subscription id to remove.
        """
        if subscription_id in self._subscriptions:
            del self._subscriptions[subscription_id]
        else:
            self._logger.warning(
                "Could not unsubscribe from subscription with ID: %s", subscription_id
            )


class WeatherStation:
    """Class to implement the Modbus interface to a Weather Station."""

    def __init__(
        self,
        config_file: str,
        hostname: str,
        port: int,
        logger: logging.Logger,
    ) -> None:
        """Initialise the instance.

        :param config_file: Path to a configuration yaml file.
        :param hostname: Host name of the Modbus server.
        :param port: Port number of the Modbus server.
        :param logger: A logging object.
        :raises: ValueError if the configuration could not be loaded or is invalid.
        """
        logger.info(f"Reading configuration file {config_file}...")
        try:
            config: WeatherStationDict = load_configuration(config_file)
        except (OSError, UnicodeDecodeError, YAMLError) as e:
            logger.error(
                f"Caught {type(e)} while trying to load configuration file: "
                f"{config_file}"
            )
            raise ValueError(f"Error opening configuration file {config_file}") from e
        except ValueError:
            logger.error(f"Invalid configuration found in: {config_file}")
            raise

        self._sensors: list[Sensor] = self._create_sensors(config)
        self._logger = logger
        self._polling: bool = False

        self._client = ModbusTcpClient(hostname, port=port)
        self.connect()
        if self._client.connected:
            self._logger.info(
                f"Connected Modbus TCP client to address {hostname}, port {port}"
            )
        else:
            self._logger.error(f"Couldn't connect to address {hostname}, port {port}")

        self._poller = WMSPoller(
            self._client,
            config["slave_id"],
            self._logger,
            config["poll_interval"],
        )
        self._poller.update_request_list(self._sensors)
        self._publisher = WMSPublisher(self._poller.publish_queue, self._logger)

    @property
    def poll_interval(self) -> float:
        """Polling interval, in seconds."""
        return self._poller.poll_interval

    @poll_interval.setter
    def poll_interval(self, new_value: float) -> None:
        self._poller.poll_interval = new_value

    @property
    def available_sensors(self) -> list[Sensor]:
        """Sensors read from the configuration file."""
        return self._sensors

    def _create_sensors(self, config: WeatherStationDict) -> list[Sensor]:
        """Create the Sensor objects from the supplied configuration."""
        return [
            Sensor(
                sensor_config["address"],
                sensor_name,
                sensor_config["description"],
                sensor_config["unit"],
                sensor_config["scale_high"],
                sensor_config["scale_low"],
            )
            for sensor_name, sensor_config in config["sensors"].items()
        ]

    def configure_poll_sensors(self, sensors_to_poll: list[SensorEnum]) -> None:
        """Configure the subset of sensors to poll.

        :param sensors: List of sensors to poll.
        """
        for sensor in sensors_to_poll:
            if not isinstance(sensor, SensorEnum):
                self._logger.error(
                    f"Could not configure sensors: '{sensor}' is not a valid sensor."
                )
                return

        sensor_names = [sensor.value for sensor in sensors_to_poll]
        self._poller.update_request_list(
            [sensor for sensor in self._sensors if sensor.name in sensor_names]
        )

    def subscribe_data(
        self,
        data_callback: Callable,
        error_callback: Optional[Callable] = None,
    ) -> int:
        """Subscribe to data updates and error notifications.

        :param data_callback: Function to call when new data is available.
        :param error_callback: Function to call in the event of a comms error.
        :return: The subscription id.
        """
        return self._publisher.subscribe(data_callback, error_callback)

    def unsubscribe_data(self, subscription_id: int) -> None:
        """Unsubscribe from all updates.

        :param id: The id to unsubscribe.
        """
        self._publisher.unsubscribe(subscription_id)

    def connect(self) -> None:
        """Connect to the device."""
        self._client.connect()

    def disconnect(self) -> None:
        """Disconnect from the device."""
        self._client.close()

    def start_polling(self) -> None:
        """Start (or restart) polling the weather station data."""
        if not self._client.connected:
            self.connect()
        self._polling = True
        self._poller.start()

    def stop_polling(self) -> None:
        """Stop polling the weather station data."""
        self._poller.stop()
        self._polling = False
