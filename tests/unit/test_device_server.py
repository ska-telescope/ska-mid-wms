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
from ska_control_model import AdminMode, HealthState
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup

from ska_mid_wms.simulator import WMSSimulatorServer


@pytest.fixture(name="change_event_callbacks")
def change_event_callbacks_fixture() -> MockTangoEventCallbackGroup:
    """
    Return a dictionary of change event callbacks with asynchrony support.

    :return: a collections.defaultdict that returns change event
        callbacks by name.
    """
    return MockTangoEventCallbackGroup(
        "adminMode",
        "healthState",
        "longRunningCommandResult",
        "longRunningCommandStatus",
        "state",
        "wind_speed",
        "wind_direction",
        "humidity",
        "pressure",
        "rainfall",
        "temperature",
        timeout=30.0,
        assert_no_error=False,
    )


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


def test_communication(
    wms_simulator_server: WMSSimulatorServer,  # pylint: disable=unused-argument
    wms_device: tango.DeviceProxy,
    change_event_callbacks: MockTangoEventCallbackGroup,
    attribute_names: List[str],
) -> None:
    """
    Test the Tango device's communication with the WeatherStation.

    :param wms_device: a proxy to the WMS device under test.
    :param wms_simulator_server: a running WMS simulator server.
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

    wms_device.subscribe_event(
        "healthState",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["healthState"],
    )

    change_event_callbacks.assert_change_event("healthState", HealthState.UNKNOWN)
    assert wms_device.healthState == HealthState.UNKNOWN

    wms_device.adminMode = AdminMode.ONLINE  # type: ignore[assignment]

    change_event_callbacks.assert_change_event("state", tango.DevState.ON)
    # change_event_callbacks.assert_change_event("healthState", HealthState.OK)
    # assert wms_device.healthState == HealthState.OK

    for attribute in attribute_names:
        wms_device.subscribe_event(
            attribute,
            tango.EventType.CHANGE_EVENT,
            change_event_callbacks[attribute],
        )

    # TODO: Remove hardcoded values
    change_event_callbacks.assert_change_event(
        "wind_speed", pytest.approx(14.98, abs=0.01), lookahead=6
    )
    change_event_callbacks.assert_change_event(
        "wind_direction", pytest.approx(292, abs=0.01), lookahead=6
    )
    change_event_callbacks.assert_change_event(
        "humidity", pytest.approx(41, abs=0.01), lookahead=6
    )
    change_event_callbacks.assert_change_event(
        "pressure", pytest.approx(802, abs=0.01), lookahead=6
    )
    change_event_callbacks.assert_change_event(
        "rainfall", pytest.approx(22, abs=0.01), lookahead=6
    )
    change_event_callbacks.assert_change_event(
        "temperature", pytest.approx(25.8, abs=0.01), lookahead=6
    )
