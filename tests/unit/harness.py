# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid WMS project
#
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module provides a Tango test harness for the WeatherStation device."""

from __future__ import annotations

from contextlib import contextmanager
from types import TracebackType
from typing import Any, Callable, Iterator

from ska_tango_testing.harness import TangoTestHarness, TangoTestHarnessContext
from tango import DeviceProxy
from tango.server import Device

DEFAULT_WEATHER_STATION_LABEL = "s1"


def get_wms_name(wms_label: str | None = None) -> str:
    """
    Return the WMS Tango device name.

    :param wms_label: name of the weather station under test.
        Defaults to None, in which case the module default is used.

    :return: the WMS Tango device name
    """
    return f"mid/wms/{wms_label or DEFAULT_WEATHER_STATION_LABEL}"


class WMSTangoTestHarnessContext:  # pylint: disable=too-few-public-methods
    """Handle for the WMS test harness context."""

    def __init__(
        self,
        tango_context: TangoTestHarnessContext,
        wms_label: str,
    ) -> None:
        """
        Initialise a new instance.

        :param tango_context: handle for the underlying test harness
            context.
        :param wms_label: name of the weather station under test.
        """
        self._wms_label = wms_label
        self._tango_context = tango_context

    def get_wms_device(self) -> DeviceProxy:
        """
        Get a proxy to the WMS Tango device.

        :returns: a proxy to the WMS Tango device.
        """
        return self._tango_context.get_device(get_wms_name(self._wms_label))


class WMSTangoTestHarness:
    """A test harness for testing monitoring and control of WMS hardware."""

    def __init__(self, wms_label: str | None = None) -> None:
        """
        Initialise a new test harness instance.

        :param wms_label: name of the weather station under test.
            Defaults to None, in which case "s1" is used.
        """
        self._wms_label = wms_label or DEFAULT_WEATHER_STATION_LABEL
        self._tango_test_harness = TangoTestHarness()

    def set_wms_device(
        self: WMSTangoTestHarness,
        config_file: str,
        address: tuple[str, int] | None = None,
        device_class: type[Device] | str = "ska_mid_wms.WMSDevice",
    ) -> None:
        """
        Set the WMS Tango device in the test harness.

        :param address: address of the WMS
            to be monitored and controlled by this Tango device.
            It is a tuple of hostname or IP address, and port.
        :param device_class: The device class to use.
            This may be used to override the usual device class,
            for example with a patched subclass.
            device should poll.
        """
        port: Callable[[dict[str, Any]], int] | int  # for the type checker

        if address is None:
            host = "localhost"
            port = 502

        else:
            (host, port) = address

        self._tango_test_harness.add_device(
            get_wms_name(self._wms_label),
            device_class,
            Host=host,
            Port=port,
            ConfigFile=config_file,
        )

    def __enter__(
        self,
    ) -> WMSTangoTestHarnessContext:
        """
        Enter the context.

        :return: the entered context.
        """
        with self._cleanup_on_error():
            return WMSTangoTestHarnessContext(
                self._tango_test_harness.__enter__(), self._wms_label
            )

    @contextmanager
    def _cleanup_on_error(self) -> Iterator[None]:
        # pylint: disable=protected-access
        with self._tango_test_harness._exit_stack as stack:
            stack.push(self)
            yield
            stack.pop_all()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exception: BaseException | None,
        trace: TracebackType | None,
    ) -> bool | None:
        """
        Exit the context.

        :param exc_type: the type of exception thrown in the with block,
            if any.
        :param exception: the exception thrown in the with block, if
            any.
        :param trace: the exception traceback, if any,

        :return: whether the exception (if any) has been fully handled
            by this method and should be swallowed i.e. not re-
            raised
        """
        return self._tango_test_harness.__exit__(exc_type, exception, trace)
