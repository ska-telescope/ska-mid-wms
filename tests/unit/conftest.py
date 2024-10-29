# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid WMS project
#
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module provides test fixtures for the Weather Monitoring System."""

import asyncio
import importlib
import logging
import threading
import time
from logging import Logger
from typing import Dict, Generator

import pytest
from pymodbus.client import ModbusTcpClient
from pytest import FixtureRequest

from ska_mid_wms.simulator import (
    WMSSimSensor,
    WMSSimulator,
    WMSSimulatorServer,
    wms_sim,
)
from ska_mid_wms.wms_interface import WeatherStation


@pytest.fixture(name="simulated_sensor")
def simulated_sensor_fixture() -> WMSSimSensor:
    """
    Fixture to return a WMSSimSensor object.

    :return: a WMSSimSensor to be used in these tests.
    """
    return WMSSimSensor(0, 100, 21678, 1)


@pytest.fixture(name="simulator")
def simulator_fixture() -> Generator[WMSSimulator, None, None]:
    """
    Fixture to return the WMSSimulator object to access the simulation directly.

    :return: the WMSSimulator object to be used in these tests.
    """
    importlib.reload(wms_sim)  # Reload so we re-initialise the simulator each time
    yield wms_sim.simulator
    wms_sim.simulator.stop_sim_threads()


@pytest.fixture(name="simulator_config", scope="module")
def simulator_config_fixture() -> Dict[str, str]:
    """
    Fixture to provide the configuration for the simulator.

    :return: simulator configuration dictionary.
    """
    return {
        "config_path": "tests/data/wms_simulation.json",
        "server_name": "WMSServer",
        "device_name": "station1",
    }


@pytest.fixture(scope="session", name="logger")
def logger_fixture() -> logging.Logger:
    """
    Fixture that returns a default logger.

    The logger will be set to DEBUG level.

    :returns: a logger.
    """
    debug_logger = logging.getLogger()
    debug_logger.setLevel(logging.DEBUG)
    return debug_logger


# Start the server in a separate thread before running the tests
# otherwise we can't use a synchronous client to connect to it
# because the event loop gets closed
@pytest.fixture(name="wms_simulator_server")
def wms_simulator_server_fixture(
    simulator_config: Dict[str, str],
    simulator: WMSSimulator,
) -> Generator[None, None, None]:
    """Start the Modbus server in a separate Thread."""

    def run_event_loop(
        event_loop: asyncio.AbstractEventLoop,
        thread_started_event: threading.Event,
    ) -> None:
        asyncio.set_event_loop(event_loop)
        thread_started_event.set()  # Signal that the event loop thread has started
        event_loop.run_forever()

    async def start_server(simulator_config: Dict[str, str]) -> WMSSimulatorServer:
        server = WMSSimulatorServer(
            config_path=simulator_config["config_path"],
            server_name=simulator_config["server_name"],
            device_name=simulator_config["device_name"],
        )
        await server.start(True)
        return server

    async def stop_server(server: WMSSimulatorServer) -> None:
        await server.stop()

    assert simulator is not None
    event_loop = asyncio.new_event_loop()
    thread_started_event = threading.Event()
    event_loop_thread = threading.Thread(
        target=run_event_loop,
        args=(event_loop, thread_started_event),
        name="asyncio event loop for Modbus server",
        daemon=True,
    )
    event_loop_thread.start()
    thread_started_event.wait(5.0)  # Wait for the event loop thread to start

    server = asyncio.run_coroutine_threadsafe(
        start_server(simulator_config), event_loop
    ).result()

    yield

    _ = asyncio.run_coroutine_threadsafe(stop_server(server), event_loop).result()


@pytest.fixture(name="wms_client")
def wms_client_fixture(
    wms_simulator_server: WMSSimulatorServer,  # pylint: disable=unused-argument
) -> Generator[ModbusTcpClient, None, None]:
    """Fixture that creates a TCP client and connects to the Modbus server.

    :param wms_simulator: a running WMS Simulator Server
    """
    client = ModbusTcpClient("localhost", port=502, timeout=5)
    client.connect()
    yield client
    client.close()


@pytest.fixture(name="weather_station")
def wms_interface_fixture(
    wms_simulator_server: WMSSimulatorServer,  # pylint: disable=unused-argument
    logger: Logger,
) -> Generator[WeatherStation, None, None]:
    """Fixture that creates a WeatherStation and connects it to a running simulation.

    :param wms_simulator_server: a running WMS Simulator Server
    """
    weather_station = WeatherStation("", logger)
    weather_station.connect()
    yield weather_station
    weather_station.disconnect()


# Expected callback data (in polling order)
expected_callback_data: Dict[str, Dict[str, str]] = {
    "wind_speed": {"name": "wind_speed", "units": "m/s"},
    "wind_direction": {"name": "wind_direction", "units": "degrees"},
    "temperature": {"name": "temperature", "units": "Deg C"},
    "pressure": {"name": "pressure", "units": "mbar"},
    "humidity": {"name": "humidity", "units": "%"},
    "rainfall": {"name": "rainfall", "units": "mm"},
}


@pytest.fixture(name="expected_callback_data_full")
def expected_callback_data_full_fixture() -> list[Dict]:
    """Fixture that returns a list of all the expected callback dictionaries.

    :return: List of expected callback dictionary data.
    """
    return list(expected_callback_data.values())


@pytest.fixture(name="expected_callback_data")
def expected_callback_data_fixture(
    request: FixtureRequest,
) -> list[Dict]:
    """Fixture that returns the expected data for the given sensor subset.

    :param request: The FixtureRequest for this test (a list of SensorEnums).
    :return: List of expected callback dictionary data.
    """
    sensors = request.node.funcargs["sensor_list"]

    return [expected_callback_data[sensor.value] for sensor in sensors]


class Helpers:  # pylint: disable=too-few-public-methods
    """Test helper functions."""

    @staticmethod
    def assert_expected_logs(
        caplog: pytest.LogCaptureFixture,
        expected_logs: list[str],
        timeout: int = 2,
    ) -> None:
        """
        Assert the expected log messages are in the captured logs.

        The expected list of log messages must appear in the records in the same order.
        The captured logs are cleared before returning for subsequent assertions.

        :param caplog: pytest log capture fixture.
        :param expected_logs: to assert are in the log capture fixture.
        :param timeout: time to wait for the last log message to appear, default 2 secs.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if expected_logs[-1] in caplog.text:
                break
        else:
            pytest.fail(f"'{expected_logs}' not found in logs within {timeout} seconds")
        test_logs = [record.message for record in caplog.records]
        assert test_logs == expected_logs
        caplog.clear()
