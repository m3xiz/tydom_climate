# The basis of this code is not mine. Unfortunately I do not recall where I find it.

# Custom component for Tydom / Delta Dore
A platform which allows you to interact with the Delta Dore Thermostast.

## Current Features
- Read thermostat temperature.
- Set Temperature
- On / Off
- Preset : Away / Boost Mode / Eco Mode / Standard Mode

## Installation
Install the component manually by putting the files from `/custom_components/tydom_climate/` in your folder `<config directory>/custom_components/tydom_climate/`

## Configuration
**Example configuration.yaml:**

climate:
  - platform: tydom_climate
    username: Tydom Mac Addresss
    password: Tydom Password
    comfort_temperature: 20
    eco_temperature: 17
    away_temperature: 12
```

