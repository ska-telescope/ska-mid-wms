# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid WMS project
#
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module provides a Component Manager for a WMS device."""

import logging
from typing import Callable, Optional

from ska_control_model import CommunicationStatus, TaskStatus
from ska_tango_base.base import BaseComponentManager, CommunicationStatusCallbackType

from ska_mid_wms.wms_interface import WeatherStation


class WMSComponentManager(BaseComponentManager):
    """Component Manager for a Weather Monitoring System."""

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        config_file_path: str,
        hostname: str,
        port: int,
        logger: logging.Logger,
        communication_state_callback: CommunicationStatusCallbackType,
        component_state_callback: Callable,
    ) -> None:
        """Initialise the instance."""
        self._logger = logger
        self._subscription_id: int = 0

        # Convert WMS callback event into kwargs for component callback
        self._data_callback = lambda event: component_state_callback(**event)
        try:
            self._wms_client = WeatherStation(config_file_path, hostname, port, logger)
        except ValueError as e:
            self._logger.error(f"Error creating Weather Station: {e}")
        finally:
            super().__init__(
                logger, communication_state_callback, component_state_callback
            )

    def start_communicating(self):
        """Start communicating with the h/w."""
        self._wms_client.connect()
        self._wms_client.start_polling()
        self._subscription_id = self._wms_client.subscribe_data(self._data_callback)
        self._update_communication_state(CommunicationStatus.ESTABLISHED)

    def stop_communicating(self):
        """Stop communicating with the h/w."""
        if self._subscription_id != 0:
            self._wms_client.unsubscribe_data(self._subscription_id)
            self._subscription_id = 0
        self._wms_client.stop_polling()
        self._wms_client.disconnect()
        self._update_communication_state(CommunicationStatus.DISABLED)

    # -----------------
    # Standard commands
    # -----------------

    def off(self, task_callback: Optional[Callable] = None) -> tuple[TaskStatus, str]:
        """
        Not implemented.

        :param task_callback: callback to be called when the status of
            the command changes
        :raises NotImplementedError: because the WMS does not support being turned off.
        """
        raise NotImplementedError("The WMS cannot be turned off - nothing to do.")

    def standby(
        self, task_callback: Optional[Callable] = None
    ) -> tuple[TaskStatus, str]:
        """
        Not implemented.

        :param task_callback: callback to be called when the status of
            the command changes

        :raises NotImplementedError: because the WMS does not support standby.
        """
        raise NotImplementedError("The WMS cannot be put into standby - nothing to do.")

    def on(self, task_callback: Optional[Callable] = None) -> tuple[TaskStatus, str]:
        """
        Not implemented.

        :param task_callback: callback to be called when the status of
            the command changes

        :raises NotImplementedError: because the WMS does not support being turned on.
        """
        raise NotImplementedError("The WMS cannot be turned on - nothing to do.")

    def reset(self, task_callback: Optional[Callable] = None) -> tuple[TaskStatus, str]:
        """
        Not implemented.

        :param task_callback: callback to be called when the status of
            the command changes

        :raises NotImplementedError: because the WMS does not support being reset.
        """
        raise NotImplementedError("The WMS cannot be reset - nothing to do.")
