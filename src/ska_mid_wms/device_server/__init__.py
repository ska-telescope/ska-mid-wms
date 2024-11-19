# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid WMS project
#
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This subpackage implements the Tango Device Server for the WMS."""

__all__ = ["WMSDevice", "WMSComponentManager"]

from .wms_device import WMSComponentManager, WMSDevice
