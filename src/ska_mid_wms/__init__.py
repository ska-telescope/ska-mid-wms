# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid WMS project
#
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This package implements the SKA-Mid Weather Monitoring System Tango device server."""

from .wms_component_manager import WMSComponentManager
from .wms_device import WMSDevice

__all__ = ["WMSDevice", "WMSComponentManager"]

__version__ = "0.2.0"
