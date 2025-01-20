=========================================
Weather Monitoring System Developer Guide
=========================================

-----------------------------
Configuring a Weather Station
-----------------------------

The WMS interface needs to be configured with a YAML file which specifies details about
the sensors to be read. This has the following format (note that the Modbus address
can either be specified in hexadecimal by using the 0x prefix, or in decimal):

.. code-block:: YAML

    Weather_Station:
      name: "Station 1"     # Optional name (str)
      slave_id: 0           # Modbus slave id (int)
      poll_interval: 0.2    # Optional poll interval (float) - defaults to 1 second
      sensors:              # Repeat block for each sensor to be read
        wind_speed:         # Sensor name (str) - should match a value in SensorEnum
          address: 15       # Modbus register address (int) - can be in hex or decimal
          description: "..."# Sensor description (str)
          unit: m/s         # Engineering unit (str)
          scale_low: 0.0    # Value in engineering units corresponding to min ADC reading (float)
          scale_high: 70.0  # Value in engineering units corresponding to max ADC reading (float)
          tango_deadband: 0.2  # rel_change for the Tango attribute (float) - defaults to 0.1
          tango_archive_deadband: 0.5 # archive_rel_change (float) - defaults to 0.1

-------------------
Tango Device Server
-------------------

A :ref:`tango_device` has been developed to publish the Weather Station automatically
to interested clients. The following Tango device properties should be set:

* *Host*: hostname of the Weather Station Modbus server
* *Port*: port number to connect to
* *ConfigFile*: path to a Weather Station configuration file (see `Configuring a Weather Station`_).

The device's attributes are created automatically using the same names as the
sensors defined in the supplied configuration.

---------------------------
Running a simulation server
---------------------------

The WMS simulator is contained in the 
`ska-mid-wms-interface <https://developer.skao.int/projects/ska-mid-wms>`_ package.