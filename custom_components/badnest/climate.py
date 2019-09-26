"""Demo platform that offers a fake climate device."""
from datetime import datetime

from homeassistant.components.climate import ClimateDevice
from homeassistant.components.climate.const import (
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    FAN_AUTO,
    FAN_ON,
    HVAC_MODE_AUTO,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    SUPPORT_PRESET_MODE,
    SUPPORT_FAN_MODE,
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_TARGET_TEMPERATURE_RANGE,
    PRESET_AWAY,
    PRESET_ECO,
    PRESET_NONE,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
    CURRENT_HVAC_COOL,
)
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS, TEMP_FAHRENHEIT

from .api import NestAPI
from .const import DOMAIN

NEST_MODE_HEAT_COOL = "range"
NEST_MODE_ECO = "eco"
NEST_MODE_HEAT = "heat"
NEST_MODE_COOL = "cool"
NEST_MODE_OFF = "off"

MODE_HASS_TO_NEST = {
    HVAC_MODE_AUTO: NEST_MODE_HEAT_COOL,
    HVAC_MODE_HEAT: NEST_MODE_HEAT,
    HVAC_MODE_COOL: NEST_MODE_COOL,
    HVAC_MODE_OFF: NEST_MODE_OFF,
}

ACTION_NEST_TO_HASS = {
    "off": CURRENT_HVAC_IDLE,
    "heating": CURRENT_HVAC_HEAT,
    "cooling": CURRENT_HVAC_COOL,
}

MODE_NEST_TO_HASS = {v: k for k, v in MODE_HASS_TO_NEST.items()}

PRESET_AWAY_AND_ECO = "Away and Eco"

PRESET_MODES = [PRESET_NONE, PRESET_AWAY, PRESET_ECO, PRESET_AWAY_AND_ECO]

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Nest climate device."""
    add_entities(
        [
            ShittyNestClimate(hass.data[DOMAIN]),
        ]
    )


class ShittyNestClimate(ClimateDevice):
    """Representation of a demo climate device."""

    def __init__(self, api):
        """Initialize the thermostat."""
        self._name = "Nest"
        self._unit_of_measurement = TEMP_CELSIUS
        self._fan_modes = [FAN_ON, FAN_AUTO]

        # Set the default supported features
        self._support_flags = SUPPORT_TARGET_TEMPERATURE #| SUPPORT_PRESET_MODE

        # Not all nest devices support cooling and heating remove unused
        self._operation_list = []

        self.device = api

        if self.device.can_heat and self.device.can_cool:
            self._operation_list.append(HVAC_MODE_AUTO)
            self._support_flags = self._support_flags | SUPPORT_TARGET_TEMPERATURE_RANGE

        # Add supported nest thermostat features
        if self.device.can_heat:
            self._operation_list.append(HVAC_MODE_HEAT)

        if self.device.can_cool:
            self._operation_list.append(HVAC_MODE_COOL)

        self._operation_list.append(HVAC_MODE_OFF)

        # feature of device
        if self.device.has_fan:
            self._support_flags = self._support_flags | SUPPORT_FAN_MODE

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return self._support_flags

    @property
    def should_poll(self):
        """Return the polling state."""
        return True

    @property
    def name(self):
        """Return the name of the climate device."""
        return self._name

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self.device.current_temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        if self.device.mode not in (NEST_MODE_HEAT_COOL, NEST_MODE_ECO):
            return self.device.target_temperature
        return None

    @property
    def target_temperature_high(self):
        """Return the highbound target temperature we try to reach."""
        if self.device.mode == NEST_MODE_ECO:
            #TODO: Grab properly
            return None
        if self.device.mode == NEST_MODE_HEAT_COOL:
            return self.device.target_temperature_high
        return None

    @property
    def target_temperature_low(self):
        """Return the lowbound target temperature we try to reach."""
        if self.device.mode == NEST_MODE_ECO:
            #TODO: Grab properly
            return None
        if self.device.mode == NEST_MODE_HEAT_COOL:
            return self.device.target_temperature_low
        return None

    @property
    def hvac_action(self):
        """Return current operation ie. heat, cool, idle."""
        return ACTION_NEST_TO_HASS[self.device.get_action()]

    @property
    def hvac_mode(self):
        """Return hvac target hvac state."""
        if self.device.mode == NEST_MODE_ECO:
            # We assume the first operation in operation list is the main one
            return self._operation_list[0]

        return MODE_NEST_TO_HASS[self.device.mode]

    @property
    def hvac_modes(self):
        """Return the list of available operation modes."""
        return self._operation_list

    @property
    def preset_mode(self):
        """Return current preset mode."""
        if self.device.away and self.device.mode == NEST_MODE_ECO:
            return PRESET_AWAY_AND_ECO

        if self.device.away:
            return PRESET_AWAY

        if self.device.mode == NEST_MODE_ECO:
            return PRESET_ECO

        return None

    @property
    def preset_modes(self):
        """Return preset modes."""
        return PRESET_MODES

    @property
    def fan_mode(self):
        """Return whether the fan is on."""
        if self.device.has_fan:
            # Return whether the fan is on
            return FAN_ON if self.device.fan else FAN_AUTO
        # No Fan available so disable slider
        return None

    @property
    def fan_modes(self):
        """Return the list of available fan modes."""
        if self.device.has_fan:
            return self._fan_modes
        return None

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        temp = None
        target_temp_low = kwargs.get(ATTR_TARGET_TEMP_LOW)
        target_temp_high = kwargs.get(ATTR_TARGET_TEMP_HIGH)
        if self.device.mode == NEST_MODE_HEAT_COOL:
            if target_temp_low is not None and target_temp_high is not None:
                self.device.set_temp(target_temp_low, target_temp_high)
        else:
            temp = kwargs.get(ATTR_TEMPERATURE)
            if temp is not None:
                self.device.set_temp(temp)

    def set_hvac_mode(self, hvac_mode):
        """Set operation mode."""
        self.device.set_mode(MODE_HASS_TO_NEST[hvac_mode])

    def set_fan_mode(self, fan_mode):
        """Turn fan on/off."""
        if self.device.has_fan:
            if fan_mode == 'on':
                self.device.set_fan(int(datetime.now().timestamp() + 60 * 30))
            else:
                self.device.set_fan(0)

    def set_preset_mode(self, preset_mode):
        """Set preset mode."""
        need_away = preset_mode in (PRESET_AWAY, PRESET_AWAY_AND_ECO)
        need_eco = preset_mode in (PRESET_ECO, PRESET_AWAY_AND_ECO)
        is_away = self.device.away
        is_eco = self.device.mode == NEST_MODE_ECO

        if is_away != need_away:
            pass
            #self.device.set_away()

        if is_eco != need_eco:
            if need_eco:
                self.device.set_eco_mode()
            else:
                self.device.mode = MODE_HASS_TO_NEST[self._operation_list[0]]

    def update(self):
        """Updates data"""
        self.device.update()

