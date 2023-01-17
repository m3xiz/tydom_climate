"""
Adds support for the Essent Icy E-Thermostaat units.
For more details about this platform, please refer to the documentation at
https://github.com/custom-components/climate.e_thermostaat
"""
#

# import requests
import voluptuous as vol

# import time
import logging

from .tydom_api import Tydom
from homeassistant.components.climate import PLATFORM_SCHEMA
import homeassistant.helpers.config_validation as cv

from homeassistant.const import (
    CONF_USERNAME,
    CONF_PASSWORD,
)

CONF_MAC_ADDRESS = "mac_address"
CONF_NAME = "name"
CONF_COMFORT_TEMPERATURE = "comfort_temperature"
CONF_SAVING_TEMPERATURE = "eco_temperature"
CONF_AWAY_TEMPERATURE = "away_temperature"
CONF_HOST = "host"

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Tydom Climate"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_MAC_ADDRESS): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_HOST, default="mediation.tydom.com"): cv.string,
        vol.Optional(CONF_COMFORT_TEMPERATURE, default=21.0): cv.string,
        vol.Optional(CONF_SAVING_TEMPERATURE, default=18.0): cv.string,
        vol.Optional(CONF_AWAY_TEMPERATURE, default=10.0): cv.string,
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Setup the Tydom Platform."""
    # name = config.get(CONF_NAME)
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    host = config.get(CONF_HOST)
    comfort = config.get(CONF_COMFORT_TEMPERATURE)
    saving = config.get(CONF_SAVING_TEMPERATURE)
    away = config.get(CONF_AWAY_TEMPERATURE)
    tydombox = Tydom(
        hass,
        host=host,
        username=username,
        password=password,
        comfort=comfort,
        saving=saving,
        away=away,
    )

    await tydombox.async_connect("First")
    await tydombox.async_system_info()
    tyd = await tydombox.async_get_entities()
    # for clim in tyd:
    #     _LOGGER.debug("creating entity: %s", clim.name)
    #     await async_add_entities([clim], False)
    #     _LOGGER.debug("done")
    async_add_entities(tyd, False)