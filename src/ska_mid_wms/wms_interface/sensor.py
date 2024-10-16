# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid WMS project
#
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module provides a Sensor class for the Weather Monitoring System."""

from typing import Final

ADC_FULL_SCALE: Final = 2**16 - 1  # Max value produced by the ADC in raw counts


class Sensor:
    """This class encapsulates a single Weather Station sensor."""

    def __init__(
        self,
        modbus_address: int,
        name: str,
        description: str,
        unit: str,
        scale_high: float,
        scale_low: float,
    ) -> None:
        """Initialise the instance.

        :param modbus_address: Modbus register address
        :param name: Sensor name
        :param description: Sensor description
        :param unit: Sensor unit string
        :param scale_high: Maximum value in engineering units
        :param scale_low: Minimum value in engineering units
        """
        self.modbus_address = modbus_address
        self.name = name
        self.description = description
        self.unit = unit
        self._scale_high = scale_high
        self._scale_low = scale_low
        self._range = scale_high - scale_low

    def convert_raw_adc(self, adc_val: int) -> float:
        """Convert a raw ADC value into engineering units.

        :param adv_val: Raw input value
        :return: Converted value in engineering units.
        """
        return (adc_val / ADC_FULL_SCALE) * self._range + self._scale_low
