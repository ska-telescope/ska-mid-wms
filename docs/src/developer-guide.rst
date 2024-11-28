=========================================
Weather Monitoring System Developer Guide
=========================================

---------------------------
Running a simulation server
---------------------------

To start up a Modbus server running the WMS simulation, run the
``wms_sim_server.py`` script as follows:

.. code-block:: bash

    cd src/ska_mid_wms/simulator  
    python wms_sim_server.py [-h] -c CONFIG -s SERVER -d DEVICE

* CONFIG: The path to a json configuration file (see `Pymodbus 
  <https://pymodbus.readthedocs.io/en/latest/source/library/simulator/config.html>`_ 
  for details)
* SERVER: The name of a server in this file to start
* DEVICE: The name of the device to simulate

-----------------------------
Configuring a Weather Station
-----------------------------

The WMS interface needs to be configured with a YAML file which specifies details about
the sensors to be read. This has the following format (note that the Modbus address
can either be specified in hexadecimal by using the 0x prefix, or in decimal):

.. code-block:: YAML

    Weather_Station:
      name: "Station 1"     # Optional name (str)
      slave_id: 1           # Modbus slave id (int)
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

-----------------------------
Using the Weather Station API
-----------------------------

Here is a brief example demonstrating how to use the WMS Python interface:

.. code-block:: py

    import logging
    import pprint
    from ska_mid_wms.wms_interface import WeatherStation, SensorEnum

    logger = logging.getLogger()
    
    # Create the WeatherStation interface, specifying:
    #   - path to a YAML configuration file (see above)
    #   - hostname of the Modbus server
    #   - port number of the Modbus server
    #   - Logger object to use for logging
    weather_station = WeatherStation("config_file.yaml", "localhost", 502, logger)

    # Set the polling interval (defaults to 1 second)
    weather_station.polling_interval = 2

    # Set the sensors to poll if required (defaults to the full set)
    sensors = [SensorEnum.PRESSURE, SensorEnum.RAINFALL]
    weather_station.configure_poll_sensors(sensors)

    # Start polling
    weather_station.start_polling()

    # Subscribe to data and error updates
    def callback(result):
        # Result is a nested dict with the following keys:
        #    value: converted value (float)
        #    unit: engineering unit (str)
        #    timestamp: Time the response was received (datetime object)
        pprint.pprint(result, indent=2)

    def error_callback(event):
        # event is a dict with the following keys:
        #    sensor_failures: the sensor names that could not be read (list[str])
        #    message: error message (str)
        #    timestamp: time the response was received (datetime object)
        pprint.pprint(event, indent=2)
    id = weather_station.subscribe_data(callback, error_callback)

    # Unsubscribe and disconnect
    weather_station.unsubscribe_data(id)
    weather_station.stop_polling()
    weather_station.disconnect()

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