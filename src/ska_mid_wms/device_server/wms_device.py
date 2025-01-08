# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid WMS project
#
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module provides a Tango Device Server for a Weather Station."""

import traceback
from dataclasses import dataclass
from typing import Any, Dict

import tango.server  # type: ignore[import-untyped]
import yaml
from ska_control_model import CommunicationStatus, PowerState
from ska_tango_base.base import SKABaseDevice
from tango import AttrQuality, EnsureOmniThread

from ska_mid_wms.device_server.wms_component_manager import WMSComponentManager
from ska_mid_wms.wms_interface.weather_station_configuration import load_configuration


@dataclass
class WMSAttribute:
    """Class representing the internal state of a WMS attribute."""

    value: float
    quality: AttrQuality
    timestamp: float


class WMSDevice(SKABaseDevice[WMSComponentManager]):
    """Tango Device Server for a Weather Monitoring System."""

    # ----------
    # Properties
    # ----------
    # TODO: Default hardware host address is 128.1.1.100
    Host: str = tango.server.device_property(default_value="localhost")
    Port: int = tango.server.device_property(default_value=502)
    ConfigFile: str = tango.server.device_property(
        default_value="tests/data/weather_station.yaml"
    )

    # ---------------
    # Initialisation
    # ---------------

    def init_device(
        self,
    ) -> None:
        """Initialise the device."""
        super().init_device()
        self._attribute_data: Dict[str, WMSAttribute] = {}
        self._create_attributes()

    def delete_device(self) -> None:
        """Prepare to delete the device."""
        self.component_manager.unsubscribe()
        self.component_manager.stop_communicating()

    def create_component_manager(self):
        """Create and return the component manager."""
        return WMSComponentManager(
            self.ConfigFile,
            self.Host,
            self.Port,
            self.logger,
            communication_state_callback=self._communication_state_callback,
            component_state_callback=self._component_state_callback,
        )

    def _create_attributes(self):
        """Create the Tango device attributes and initialise the device state."""
        try:
            config = load_configuration(self.ConfigFile)
        except (ValueError, OSError, yaml.YAMLError, UnicodeDecodeError) as e:
            message = (
                "Could not load WeatherStation configuration from file: "
                f"{self.ConfigFile}"
            )
            self.logger.error(message)
            raise ValueError(message) from e
        for sensor_name, sensor_config in config["sensors"].items():
            # Initialise the device state
            self._attribute_data[sensor_name] = WMSAttribute(
                None, AttrQuality.ATTR_INVALID, 0
            )
            attr = tango.server.attribute(
                name=sensor_name,
                dtype=float,
                access=tango.AttrWriteType.READ,
                label=sensor_name,
                unit=sensor_config["unit"],
                rel_change=sensor_config["tango_deadband"],
                archive_rel_change=sensor_config["tango_archive_deadband"],
                fget=self._read_attribute,
            )
            self.add_attribute(attr)
            self.set_change_event(sensor_name, True, True)
            self.set_archive_event(sensor_name, True, True)

    def _read_attribute(self, attribute: tango.Attribute) -> None:
        """Set the attribute's value from the current device state."""
        attr_name = attribute.get_name()
        attr_value = self._attribute_data[attr_name].value
        if attr_value is None:
            msg = (
                f"{attr_name} value is None: perhaps we have "
                "attempted to read it before a value has been received?"
            )
            self.logger.warning(msg)
            raise tango.Except.throw_exception(
                f"Error: {attr_name} has no value",
                msg,
                "".join(traceback.format_stack()),
            )
        attribute.set_value_date_quality(
            attr_value,
            self._attribute_data[attr_name].timestamp,
            self._attribute_data[attr_name].quality,
        )

    # ----------
    # Callbacks
    # ----------
    def _communication_state_callback(
        self, communication_state: CommunicationStatus
    ) -> None:
        super()._communication_state_changed(communication_state)

    def _component_state_callback(
        self,
        **kwargs: Any,
    ) -> None:
        """Handle a change in component state.

        The WMS only sends sensor data, so we just simply infer that the PowerState is
        ON when we receive a callback. The fault status is set according to whether
        the callback data is valid.
        """
        fault_status: bool = False
        for sensor_name, value in kwargs.items():
            if sensor_name not in self._attribute_data:
                self.logger.warning(
                    f"Received callback for unknown sensor: {sensor_name}"
                )
                continue
            # Initialise the new data from the current values in case
            # the callback data is invalid
            new_value = self._attribute_data[sensor_name].value
            timestamp = self._attribute_data[sensor_name].timestamp
            try:
                new_value = value["value"]
                timestamp = value["timestamp"].timestamp()
            except (KeyError, AttributeError):
                self.logger.error(
                    f"Received invalid callback data for {sensor_name}: {value}"
                )
                quality = tango.AttrQuality.ATTR_INVALID
                fault_status = True
            else:
                quality = tango.AttrQuality.ATTR_VALID
            finally:
                self._attribute_data[sensor_name] = WMSAttribute(
                    value=new_value,
                    timestamp=timestamp,
                    quality=quality,
                )
            with EnsureOmniThread():  # Callback is from a separate Python thread
                self.push_change_event(
                    sensor_name,
                    self._attribute_data[sensor_name].value,
                    self._attribute_data[sensor_name].timestamp,
                    self._attribute_data[sensor_name].quality,
                )
                self.push_archive_event(
                    sensor_name,
                    self._attribute_data[sensor_name].value,
                    self._attribute_data[sensor_name].timestamp,
                    self._attribute_data[sensor_name].quality,
                )
        super()._component_state_changed(fault=fault_status, power=PowerState.ON)


def main(args=None, **kwargs):  # pylint: disable=unused-argument
    """Run the WMS Device Server with the supplied arguments."""
    return tango.server.run((WMSDevice,), **kwargs)


if __name__ == "__main__":
    main()
