# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid WMS project
#
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module provides unit tests for the WeatherStation Tango DS."""

from typing import List

import pytest
import tango  # type: ignore[import-untyped]
from ska_control_model import AdminMode
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup

from ska_mid_wms.simulator import WMSSimulator, WMSSimulatorServer


@pytest.fixture(name="attribute_names")
def attribute_names_fixture() -> List[str]:
    """Return a list of the names of the attributes under test."""
    return [
        "wind_speed",
        "wind_direction",
        "humidity",
        "temperature",
        "pressure",
        "rainfall",
    ]


@pytest.fixture(name="change_event_callbacks")
def change_event_callbacks_fixture(
    attribute_names: List[str],
) -> MockTangoEventCallbackGroup:
    """
    Return a dictionary of change event callbacks with asynchrony support.

    :param attribute_names: List of the attribute names under test.
    :return: a collections.defaultdict that returns change event
        callbacks by name.
    """
    return MockTangoEventCallbackGroup(
        "state",
        *attribute_names,
        timeout=30.0,
        assert_no_error=False,
    )


def test_communication(
    wms_simulator_server: WMSSimulatorServer,  # pylint: disable=unused-argument
    simulator: WMSSimulator,
    wms_device: tango.DeviceProxy,
    change_event_callbacks: MockTangoEventCallbackGroup,
    attribute_names: List[str],
) -> None:
    """
    Test the Tango device's communication with the WeatherStation.

    :param wms_simulator_server: a running WMS simulator server.
    :param simulator: the running simulation so we can access the
        simulated data directly.
    :param wms_device: a proxy to the WMS device under test.
    :param change_event_callbacks: dictionary of mock change event
        callbacks with asynchrony support
    """
    assert wms_device.adminMode == AdminMode.OFFLINE

    wms_device.subscribe_event(
        "state",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["state"],
    )
    change_event_callbacks.assert_change_event("state", tango.DevState.DISABLE)

    wms_device.adminMode = AdminMode.ONLINE  # type: ignore[assignment]

    change_event_callbacks.assert_change_event("state", tango.DevState.ON)

    for attribute in attribute_names:
        wms_device.subscribe_event(
            attribute,
            tango.EventType.CHANGE_EVENT,
            change_event_callbacks[attribute],
        )

    # Check each attribute against its default simulated value
    # e.g. simulator.converted_wind_speed for the wind_speed attribute
    for attribute in attribute_names:
        change_event_callbacks.assert_change_event(
            attribute,
            pytest.approx(getattr(simulator, "converted_" + attribute), abs=0.01),
            lookahead=len(attribute_names),
        )
