# SKA-Mid Weather Monitoring System

This repository contains the source code for the SKA Mid Telescope Weather Monitoring System (known as WMS).

## Description
The WMS provides the ability to monitor weather related data at the SKA telescope sites. At the time of writing this includes wind speed, wind direction, temperature, pressure, humidity, and rainfall. An Acromag module receives filtered analogue signals sent over twisted pair and outputs the corresponding sensor readings over Modbus TCP/IP. This software module uses [Pymodbus](https://pymodbus.readthedocs.io/en/latest/) to read the sensor data, and provides callback functions to clients who wish to be notified when new readings are available. Please refer to the latest built docs for details.

## Authors and acknowledgment
This project is being developed by SKAO Team Wombat.

## License
Copyright 2024 SKA Observatory

## Project status
This project is in development.