# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid WMS project
#
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module provides a simulator for the Weather Monitoring System (WMS)."""
import math
import random
import time
from threading import Thread
from typing import Final

import numpy as np
import pymodbus.datastore.simulator

ADC_FULL_SCALE: Final = 2**16 - 1  # Max value produced by the ADC in raw counts


class WMSSimSensor:
    """Simulate a weather station sensor."""

    # pylint: disable=too-many-instance-attributes

    def generate_data(self, update_frequency: float) -> None:
        """Generate changing data for the sensor.

        :param update_frequency: update rate in Hz.
        """
        # Create a sine wave between two random points (allowing room for noise)
        signal_start = random.randint(0, math.floor(ADC_FULL_SCALE / 2))
        signal_end = random.randint(signal_start + 500, ADC_FULL_SCALE - 10000)
        signal_range = signal_end - signal_start
        time_array = np.arange(0.0, np.pi * 2, 0.001)
        sine_wave = (
            signal_start + (signal_range / 2) + np.sin(time_array) * (signal_range / 2)
        )
        # Inject some noise
        noise_width = random.randint(1, 10) / 100 * signal_range
        noise = np.random.normal(0, noise_width, len(sine_wave))
        signal = sine_wave + noise
        while True:
            for datapoint in signal:
                if not self._generate:
                    return  # Exit here: request to stop generating has been made
                self.raw_value = math.floor(datapoint)
                time.sleep(1 / update_frequency)

    def __init__(
        self,
        min_value: float,
        max_value: float,
        init_value: int,
        update_frequency: float,
    ):
        """Initialise the sensor.

        :param min_value: Minimum value in engineering units.
        :param max_value: Maximum value in engineering units.
        :param init_value: Initial value in raw ADC counts.
        :param: update_frequency: Update frequency in Hz.
        """
        self._min_value = min_value
        self._range = max_value - min_value
        self._raw_value = init_value
        self._engineering_value = self.convert_raw_to_egu(init_value)

        self._generate: bool = False
        self._sim_thread = Thread(target=self.generate_data, args=[update_frequency])

    def start_generating_data(self) -> None:
        """Start generating data."""
        self._generate = True
        if not self._sim_thread.is_alive():
            self._sim_thread.start()

    def stop_generating_data(self) -> None:
        """Stop generating data."""
        self._generate = False

    @property
    def engineering_value(self) -> float:
        """Return the current value in engineering units."""
        return self._engineering_value

    @engineering_value.setter
    def engineering_value(self, new_value: float) -> None:
        self._engineering_value = new_value
        self._raw_value = self.convert_egu_to_raw(new_value)

    @property
    def raw_value(self) -> int:
        """Return the current value in raw ADC counts."""
        return self._raw_value

    @raw_value.setter
    def raw_value(self, new_value: int) -> None:
        self._raw_value = new_value
        self._engineering_value = self.convert_raw_to_egu(new_value)

    def convert_egu_to_raw(self, engineering_val: float) -> int:
        """Convert a value in engineering units to raw ADC counts.

        :param engineering_val: the value to convert.
        :return: the converted value.
        """
        return math.floor(
            (engineering_val - self._min_value) / self._range * ADC_FULL_SCALE
        )

    def convert_raw_to_egu(self, raw_value: int) -> float:
        """Convert a value in raw ADC counts to engineering units.

        :param raw_value: the value to convert.
        :return: the converted value.
        """
        return (raw_value / ADC_FULL_SCALE) * self._range + self._min_value


class WMSSimulator:
    """Simulate the Modbus registers for the Weather Station h/w."""

    # Initial default values (raw counts)
    DEFAULT_WIND_SPEED: Final = 14024  # 21.4 m/s
    DEFAULT_WIND_DIRECTION: Final = 53156  # 292 degrees
    DEFAULT_TEMPERATURE: Final = 39102  # 25.8 deg Celsius
    DEFAULT_PRESSURE: Final = 26476  # 802 mbar
    DEFAULT_HUMIDITY: Final = 26869  # 41 %
    DEFAULT_RAINFALL: Final = 2883  # 22 mm

    # Update frequencies for data generation (Hz)
    WIND_SPEED_UPDATE_FREQUENCY: Final = 1
    WIND_DIRECTION_UPDATE_FREQUENCY: Final = 2
    TEMPERATURE_UPDATE_FREQUENCY: Final = 3
    PRESSURE_UPDATE_FREQUENCY: Final = 5
    HUMIDITY_UPDATE_FREQUENCY: Final = 10
    RAINFALL_UPDATE_FREQUENCY: Final = 5
    LONGEST_UPDATE_CYCLE: Final = HUMIDITY_UPDATE_FREQUENCY

    def __init__(self):
        """Initialise the simulator."""
        self._wind_speed_sensor = WMSSimSensor(
            0, 40, self.DEFAULT_WIND_SPEED, self.WIND_SPEED_UPDATE_FREQUENCY
        )
        self._wind_direction_sensor = WMSSimSensor(
            0, 360, self.DEFAULT_WIND_DIRECTION, self.WIND_DIRECTION_UPDATE_FREQUENCY
        )
        self._temperature_sensor = WMSSimSensor(
            -10, 50, self.DEFAULT_TEMPERATURE, self.TEMPERATURE_UPDATE_FREQUENCY
        )
        self._pressure_sensor = WMSSimSensor(
            600, 1100, self.DEFAULT_PRESSURE, self.PRESSURE_UPDATE_FREQUENCY
        )
        self._humidity_sensor = WMSSimSensor(
            0, 100, self.DEFAULT_HUMIDITY, self.HUMIDITY_UPDATE_FREQUENCY
        )
        self._rainfall_sensor = WMSSimSensor(
            0, 500, self.DEFAULT_RAINFALL, self.RAINFALL_UPDATE_FREQUENCY
        )

        self._sensors = [
            self._wind_speed_sensor,
            self._wind_direction_sensor,
            self._temperature_sensor,
            self._pressure_sensor,
            self._humidity_sensor,
            self._rainfall_sensor,
        ]

    def start_sim_threads(self) -> None:
        """Start all the sensors generating data."""
        for sensor in self._sensors:
            sensor.start_generating_data()

    def stop_sim_threads(self) -> None:
        """Stop all the sensors generating data."""
        for sensor in self._sensors:
            sensor.stop_generating_data()

    @property
    def wind_speed(self) -> int:
        """Wind speed in raw ADC counts."""
        return self._wind_speed_sensor.raw_value

    @wind_speed.setter
    def wind_speed(self, value: int) -> None:
        self._wind_speed_sensor.raw_value = value

    @property
    def converted_wind_speed(self) -> float:
        """Wind speed in engineering units."""
        return self._wind_speed_sensor.engineering_value

    @converted_wind_speed.setter
    def converted_wind_speed(self, value: float) -> None:
        self._wind_speed_sensor.engineering_value = value

    @property
    def wind_direction(self) -> int:
        """Wind directon in raw ADC counts."""
        return self._wind_direction_sensor.raw_value

    @wind_direction.setter
    def wind_direction(self, value: int) -> None:
        self._wind_direction_sensor.raw_value = value

    @property
    def converted_wind_direction(self) -> float:
        """Wind directon in engineering units."""
        return self._wind_direction_sensor.engineering_value

    @converted_wind_direction.setter
    def converted_wind_direction(self, value: float) -> None:
        self._wind_direction_sensor.engineering_value = value

    @property
    def temperature(self) -> int:
        """Temperature in raw ADC counts."""
        return self._temperature_sensor.raw_value

    @temperature.setter
    def temperature(self, value: int) -> None:
        self._temperature_sensor.raw_value = value

    @property
    def converted_temperature(self) -> float:
        """Temperature in engineering units."""
        return self._temperature_sensor.engineering_value

    @converted_temperature.setter
    def converted_temperature(self, value: float) -> None:
        self._temperature_sensor.engineering_value = value

    @property
    def humidity(self) -> int:
        """Humidity in raw ADC counts."""
        return self._humidity_sensor.raw_value

    @humidity.setter
    def humidity(self, value: int) -> None:
        self._humidity_sensor.raw_value = value

    @property
    def converted_humidity(self) -> float:
        """Humidity in engineering units."""
        return self._humidity_sensor.engineering_value

    @converted_humidity.setter
    def converted_humidity(self, value: float) -> None:
        self._humidity_sensor.engineering_value = value

    @property
    def pressure(self) -> int:
        """Pressure in raw ADC counts."""
        return self._pressure_sensor.raw_value

    @pressure.setter
    def pressure(self, value: int) -> None:
        self._pressure_sensor.raw_value = value

    @property
    def converted_pressure(self) -> float:
        """Pressure in engineering units."""
        return self._pressure_sensor.engineering_value

    @converted_pressure.setter
    def converted_pressure(self, value: float) -> None:
        self._pressure_sensor.engineering_value = value

    @property
    def rainfall(self) -> int:
        """Rainfall in raw ADC counts."""
        return self._rainfall_sensor.raw_value

    @rainfall.setter
    def rainfall(self, value: int) -> None:
        self._rainfall_sensor.raw_value = value

    @property
    def converted_rainfall(self) -> float:
        """Rainfall in engineering units."""
        return self._rainfall_sensor.engineering_value

    @converted_rainfall.setter
    def converted_rainfall(self, value: float) -> None:
        self._rainfall_sensor.engineering_value = value

    # Custom action methods called by Pymodbus
    def wind_speed_cell(
        self,
        _registers: list[pymodbus.datastore.simulator.Cell],
        _inx: int,
        _cell: pymodbus.datastore.simulator.Cell,
    ) -> None:
        """Set the wind speed register value."""
        _cell.value = self.wind_speed

    def wind_direction_cell(
        self,
        _registers: list[pymodbus.datastore.simulator.Cell],
        _inx: int,
        _cell: pymodbus.datastore.simulator.Cell,
    ) -> None:
        """Set the wind direction register value."""
        _cell.value = self.wind_direction

    def temperature_cell(
        self,
        _registers: list[pymodbus.datastore.simulator.Cell],
        _inx: int,
        _cell: pymodbus.datastore.simulator.Cell,
    ) -> None:
        """Set the temperature register value."""
        _cell.value = self.temperature

    def humidity_cell(
        self,
        _registers: list[pymodbus.datastore.simulator.Cell],
        _inx: int,
        _cell: pymodbus.datastore.simulator.Cell,
    ) -> None:
        """Set the humidity register value."""
        _cell.value = self.humidity

    def pressure_cell(
        self,
        _registers: list[pymodbus.datastore.simulator.Cell],
        _inx: int,
        _cell: pymodbus.datastore.simulator.Cell,
    ) -> None:
        """Set the pressure register value."""
        _cell.value = self.pressure

    def rainfall_cell(
        self,
        _registers: list[pymodbus.datastore.simulator.Cell],
        _inx: int,
        _cell: pymodbus.datastore.simulator.Cell,
    ) -> None:
        """Set the rainfall register value."""
        _cell.value = self.rainfall


simulator = WMSSimulator()

# Declare the customs_actions dict needed by Pymodbus
custom_actions_dict = {
    "wind_speed": simulator.wind_speed_cell,
    "wind_direction": simulator.wind_direction_cell,
    "temperature": simulator.temperature_cell,
    "humidity": simulator.humidity_cell,
    "pressure": simulator.pressure_cell,
    "rainfall": simulator.rainfall_cell,
}
