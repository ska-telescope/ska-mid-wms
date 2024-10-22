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

---------------------------------
Connecting to the Weather Station
---------------------------------

Here is a brief example demonstrating how to use the WMS Python interface:

.. code-block:: py

    import logging
    import pprint
    from ska_mid_wms.wms_interface import WeatherStation, SensorEnum

    logger = logging.getLogger()
    weather_station = await WeatherStation.create_weather_station("config_file.json", logger)
    await weather_station.connect()

    # Set the polling interval (defaults to 1 second)
    weather_station.polling_interval = 2

    # Set the sensors to poll if required (defaults to the full set)
    sensors = [SensorEnum.PRESSURE, SensorEnum.RAINFALL]
    wms.configure_poll_sensors(sensors)

    # Start polling
    await weather_station.start_polling()

    # Subscribe to data updates
    def callback(result):
        # Result is a nested dict with the following keys:
        #    Value: converted value (float)
        #    Units: engineering units (str)
        #    Timestamp: Time the response was received (datetime object)
        pprint.pprint(event, indent=2)
    id = weather_station.subscribe_data(callback)

    # Unsubscribe and disconnect
    weather_station.unsubscribe_data(id)
    weather_station.stop_polling()
    weather_station.disconnect()
