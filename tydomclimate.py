""" Define the class TydomClimate """

import logging

# import requests
# import time

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    CURRENT_HVAC_OFF,
    #    PRESET_AWAY,
    #    PRESET_COMFORT,
    #    PRESET_HOME,
    #    PRESET_SLEEP,
    SUPPORT_PRESET_MODE,
    SUPPORT_TARGET_TEMPERATURE,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
)
from homeassistant.const import (
    #    ATTR_TEMPERATURE,
    TEMP_CELSIUS,
)


__version__ = "0.0.2"

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Tydom Climate"

# DEFAULT_AWAY_TEMPERATURE = 18.0
# DEFAULT_SAVING_TEMPERATURE = 20.0
# DEFAULT_COMFORT_TEMPERATURE = 21.0


STATE_COMFORT = "Comfort"
STATE_BOOST = "Boost"
STATE_AWAY = "Away"
STATE_ECO = "Economic"


MIN_TEMP = 10
MAX_TEMP = 30

SUPPORT_FLAGS = SUPPORT_PRESET_MODE | SUPPORT_TARGET_TEMPERATURE
SUPPORT_PRESET = [STATE_COMFORT, STATE_BOOST, STATE_AWAY, STATE_ECO]

# class TydomClimate(ClimateDevice):
class TydomClimate(ClimateEntity):
    """Representation of a E-Thermostaat device."""

    def __init__(
        self,
        device_id,
        device_name,
        # temperature,
        # target_temperature,
        # not_sure,
        # hvac_mode,
        tydombox,
    ):
        """Initialize the thermostat."""
        self._name = device_name
        self._device_id = device_id
        # self._current_temperature = temperature
        # self._target_temperature = target_temperature
        # self._old_conf = None
        # self._hvac_mode = hvac_mode  # dev["authorization"]
        # self._mode = not_sure
        self._tydombox = tydombox
        self._data = None

        # self.update()

    # @property
    # def payload(self):
    #     """Return the payload."""
    #     return {"username": self._username, "password": self._password}

    @property
    def name(self):
        """Return the name of the thermostat."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique ID for this thermostat."""
        return "_".join([self._name, "climate"])

    @property
    def should_poll(self):
        """Polling is required."""
        return False

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return MIN_TEMP

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return MAX_TEMP

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._tydombox.getinfo(self._device_id, "temperature")
        # return self._current_temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._tydombox.getinfo(self._device_id, "setpoint")
        # return self._target_temperature

    @property
    def hvac_mode(self):
        """Return hvac operation ie. heat, cool mode."""
        # _LOGGER.debug("Get hvac mode")
        authorization = self._tydombox.getinfo(self._device_id, "authorization")
        if authorization == "STOP":
            return HVAC_MODE_OFF
        elif authorization == "HEATING":
            return HVAC_MODE_HEAT
        return None

        # return None

    @property
    def hvac_action(self):
        """Return the current running hvac operation."""
        # _LOGGER.debug("Get hvac action")
        authorization = self._tydombox.getinfo(self._device_id, "authorization")
        if authorization == "STOP":
            return CURRENT_HVAC_OFF
        elif authorization == "HEATING":
            temp = self._tydombox.getinfo(self._device_id, "temperature")
            tgt = self._tydombox.getinfo(self._device_id, "setpoint")
            if temp <= tgt:
                return CURRENT_HVAC_HEAT
            else:
                return CURRENT_HVAC_IDLE
        return None

    @property
    def hvac_modes(self):
        """HVAC modes."""
        # _LOGGER.debug("Get list of hvac mode")
        return [HVAC_MODE_OFF, HVAC_MODE_HEAT]
        

    @property
    def preset_mode(self):
        """Return the current preset mode, e.g., home, away, temp."""
        # _LOGGER.debug("Get Preset mode")
        return self._tydombox.getinfo(self._device_id, "authorization")
        # return self._hvac_mode

    @property
    def preset_modes(self):
        """Return a list of available preset modes."""
        # _LOGGER.debug("Get a list Preset modes")
        return SUPPORT_PRESET

    @property
    def is_away_mode_on(self):
        """Return true if away mode is on."""
        # _LOGGER.debug("Check if away")
        hvac_mode = self._tydombox.getinfo(self._device_id, "havcMode")
        return hvac_mode in [STATE_AWAY]

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    def set_preset_mode(self, preset_mode: str):
        """Set new preset mode."""
        # STATE_COMFORT, STATE_BOOST, STATE_AWAY, STATE_ECO

        if preset_mode == STATE_COMFORT:
            self._set_temperature(self._tydombox.comfort)
        elif preset_mode == STATE_ECO:
            self._set_temperature(self._tydombox.saving)
        elif preset_mode == STATE_AWAY:
            self._set_temperature(self._tydombox.away)
        elif preset_mode == STATE_BOOST:
            self._set_temperature(MAX_TEMP)

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        # temperature = kwargs.get(ATTR_TEMPERATURE)
        temperature = kwargs.get("temperature")
        if temperature is None:
            return
        self._set_temperature(temperature)

    def _set_temperature(self, temperature):
        """Set new target temperature, via URL commands."""
        # self._target_temperature = temperature
        self._tydombox.set_temp(self._device_id, temperature)

    async def async_added_to_hass(self):
        """ Called when an entity has their entity_id and hass object assigned """
        _LOGGER.info("%s is addedd to hass", self._name)

    async def async_will_remove_from_hass(self):
        """ Called when an entity is about to be removed from Home Assistant """
        _LOGGER.info("%s is removed from hass", self._name)

    async def async_send_update(self):
        """ this function is called when a entity is updating """
        _LOGGER.denug("%s is updating", self._name)

    async def async_set_hvac_mode(self, hvac_mode):
        _LOGGER.debug("Set hvac mode %s", hvac_mode)
        """Set new target hvac mode."""

    # async def async_update(self):
    #     """Get the latest data."""
    #     _LOGGER.info("%s is updating", self._name)
    #     await self._get_data()
