#
# Project makefile for SKA-Mid Weather Monitoring System project. 
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

include .make/base.mk

-include PrivateRules.mak

########################################################################
# PYTHON
########################################################################
include .make/python.mk

PYTHON_LINE_LENGTH = 88

python-post-lint:
	$(PYTHON_RUNNER) mypy src/ tests/

########################################################################
# OCI
########################################################################
include .make/oci.mk

########################################################################
# DOCS
########################################################################
include .make/docs.mk