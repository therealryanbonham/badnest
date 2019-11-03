import logging

from homeassistant.helpers.entity import Entity

from .api import NestTemperatureSensorAPI
from .const import DOMAIN, CONF_COOKIE, CONF_ISSUE_TOKEN

from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    DEVICE_CLASS_TEMPERATURE,
    CONF_EMAIL,
    CONF_PASSWORD,
    TEMP_CELSIUS
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass,
                               config,
                               async_add_entities,
                               discovery_info=None):
    """Set up the Nest climate device."""
    api = NestTemperatureSensorAPI(
        hass.data[DOMAIN][CONF_EMAIL],
        hass.data[DOMAIN][CONF_PASSWORD],
        hass.data[DOMAIN][CONF_ISSUE_TOKEN],
        hass.data[DOMAIN][CONF_COOKIE],
    )

    sensors = []
    _LOGGER.info("Adding temperature sensors")
    for sensor in api.get_devices():
        _LOGGER.info(f"Adding nest temp sensor uuid: {sensor}")
        sensors.append(
            NestTemperatureSensor(
                sensor,
                NestTemperatureSensorAPI(
                    hass.data[DOMAIN][CONF_EMAIL],
                    hass.data[DOMAIN][CONF_PASSWORD],
                    hass.data[DOMAIN][CONF_ISSUE_TOKEN],
                    hass.data[DOMAIN][CONF_COOKIE],
                    sensor
                )))

    async_add_entities(sensors)


class NestTemperatureSensor(Entity):
    """Implementation of the DHT sensor."""

    def __init__(self, device_id, api):
        """Initialize the sensor."""
        self._name = "Nest Temperature Sensor"
        self._unit_of_measurement = TEMP_CELSIUS
        self.device_id = device_id
        self.device = api

    @property
    def name(self):
        """Return the name of the sensor."""
        return self.device_id

    @property
    def state(self):
        """Return the state of the sensor."""
        return self.device.temperature

    @property
    def device_class(self):
        """Return the device class of this entity."""
        return DEVICE_CLASS_TEMPERATURE

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement

    def update(self):
        """Get the latest data from the DHT and updates the states."""
        self.device.update()

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {ATTR_BATTERY_LEVEL: self.device.battery_level}
