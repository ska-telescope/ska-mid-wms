# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid WMS project
#
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module provides a simulator for the Weather Monitoring System (WMS)."""
import pymodbus.datastore.simulator


class WMSSimulator:
    """Simulate the Modbus registers for the Weather Station h/w."""

    def __init__(self):
        """Initialise the simulator."""
        self._wind_speed = 200
        self._wind_direction = 602
        self._temperature = 12
        self._pressure = 222
        self._humidity = 28
        self._rainfall = 23

    @property
    def wind_speed(self) -> int:
        """Wind speed in raw ADC counts."""
        return self._wind_speed

    @wind_speed.setter
    def wind_speed(self, value: int) -> None:
        self._wind_speed = value

    @property
    def wind_direction(self) -> int:
        """Wind directon in raw ADC counts."""
        return self._wind_direction

    @wind_direction.setter
    def wind_direction(self, value: int) -> None:
        self._wind_direction = value

    @property
    def temperature(self) -> int:
        """Temperature in raw ADC counts."""
        return self._temperature

    @temperature.setter
    def temperature(self, value: int) -> None:
        self._temperature = value

    @property
    def humidity(self) -> int:
        """Humidity in raw ADC counts."""
        return self._humidity

    @humidity.setter
    def humidity(self, value: int) -> None:
        self._humidity = value

    @property
    def pressure(self) -> int:
        """Pressure in raw ADC counts."""
        return self._pressure

    @pressure.setter
    def pressure(self, value: int) -> None:
        self._pressure = value

    @property
    def rainfall(self) -> int:
        """Rainfall in raw ADC counts."""
        return self._rainfall

    @rainfall.setter
    def rainfall(self, value: int) -> None:
        self._rainfall = value

    def wind_speed_cell(
        self,
        _registers: list[pymodbus.datastore.simulator.Cell],
        _inx: int,
        _cell: pymodbus.datastore.simulator.Cell,
    ) -> None:
        """Set the wind speed register value."""
        _cell.value = self._wind_speed

    def wind_direction_cell(
        self,
        _registers: list[pymodbus.datastore.simulator.Cell],
        _inx: int,
        _cell: pymodbus.datastore.simulator.Cell,
    ) -> None:
        """Set the wind direction register value."""
        _cell.value = self._wind_direction

    def temperature_cell(
        self,
        _registers: list[pymodbus.datastore.simulator.Cell],
        _inx: int,
        _cell: pymodbus.datastore.simulator.Cell,
    ) -> None:
        """Set the temperature register value."""
        _cell.value = self._temperature

    def humidity_cell(
        self,
        _registers: list[pymodbus.datastore.simulator.Cell],
        _inx: int,
        _cell: pymodbus.datastore.simulator.Cell,
    ) -> None:
        """Set the humidity register value."""
        _cell.value = self._humidity

    def pressure_cell(
        self,
        _registers: list[pymodbus.datastore.simulator.Cell],
        _inx: int,
        _cell: pymodbus.datastore.simulator.Cell,
    ) -> None:
        """Set the pressure register value."""
        _cell.value = self._pressure

    def rainfall_cell(
        self,
        _registers: list[pymodbus.datastore.simulator.Cell],
        _inx: int,
        _cell: pymodbus.datastore.simulator.Cell,
    ) -> None:
        """Set the rainfall register value."""
        _cell.value = self._rainfall


simulator = WMSSimulator()

custom_actions_dict = {
    "wind_speed": simulator.wind_speed_cell,
    "wind_direction": simulator.wind_direction_cell,
    "temperature": simulator.temperature_cell,
    "humidity": simulator.humidity_cell,
    "pressure": simulator.pressure_cell,
    "rainfall": simulator.rainfall_cell,
}
