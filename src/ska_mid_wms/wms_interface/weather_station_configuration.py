# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid WMS project
#
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module provides a WMS configuration utility."""

from typing import Final, TypedDict

import yaml
from cerberus import Validator  # type: ignore[import-untyped]

SENSOR_SCHEMA: Final = {
    "type": "dict",
    "required": True,
    "keysrules": {"type": "string"},
    "valuesrules": {
        "type": "dict",
        "schema": {
            "address": {
                "type": "integer",
                "required": True,
            },
            "description": {
                "type": "string",
                "required": True,
            },
            "units": {
                "type": "string",
                "required": True,
            },
            "scale_low": {
                "type": "float",
                "required": True,
            },
            "scale_high": {
                "type": "float",
                "required": True,
            },
        },
    },
}

WEATHER_STATION_SCHEMA: Final = {
    "Weather_Station": {
        "type": "dict",
        "schema": {
            "name": {"type": "string"},
            "slave_id": {
                "type": "integer",
                "required": True,
            },
            "poll_interval": {
                "type": "float",
                "default": 1.0,
            },
            "sensors": SENSOR_SCHEMA,
        },
    }
}


class SensorDict(TypedDict):
    """Typed Dict for a Sensor configuration.

    address (int)
    description (str)
    units (str)
    scale_low (float)
    scale_high (float)
    """

    address: int
    description: str
    units: str
    scale_low: float
    scale_high: float


class WeatherStationDict(TypedDict, total=False):
    """TypedDict for a Weather Station configuration.

    name (str): Name of the weather station (optional key)
    slave_id (int): Modbus slave id
    sensors (dict(str, SensorDict)): Dictionary of sensors
    """

    name: str
    slave_id: int
    poll_interval: float
    sensors: dict[str, SensorDict]


def load_configuration(config_path: str) -> WeatherStationDict:
    """
    Load and validate the configuration YAML file.

    :param config_path: path to the configuration file.
    :returns: validated configuration dictionary.
    :raises: OSError if the file cannot be opened.
    :raises: UnicodeDecodeError if the file cannot be decoded.
    :raises: YAMLError if the YAML cannot be loaded.
    :raises: ValueError if the configuration is invalid.
    """
    try:
        with open(config_path, "r", encoding="UTF-8") as file:
            config = yaml.safe_load(file)
    except FileNotFoundError as e:
        raise ValueError(f"Invalid WeatherStation configuration: {e}") from e

    # Validate the data and apply defaults if needed
    v = Validator(WEATHER_STATION_SCHEMA)
    if v.validate(config):
        return v.normalized(config)["Weather_Station"]
    raise ValueError(f"Invalid WeatherStation configuration: {v.errors}")
