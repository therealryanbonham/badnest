"""This component provides basic support for Foscam IP cameras."""
import logging
from datetime import timedelta
from homeassistant.util.dt import utcnow

from homeassistant.components.camera import Camera, SUPPORT_ON_OFF

from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from .api import NestCameraAPI
from .const import DOMAIN, CONF_ISSUE_TOKEN, CONF_COOKIE, CONF_APIKEY


_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Nest Camera"


async def async_setup_platform(hass,
                               config,
                               async_add_entities,
                               discovery_info=None):
    """Set up a Nest Camera."""
    api = NestCameraAPI(
        hass.data[DOMAIN][CONF_EMAIL],
        hass.data[DOMAIN][CONF_PASSWORD],
        hass.data[DOMAIN][CONF_ISSUE_TOKEN],
        hass.data[DOMAIN][CONF_COOKIE],
        hass.data[DOMAIN][CONF_APIKEY]
    )

    # cameras = await hass.async_add_executor_job(nest.get_cameras())
    cameras = []
    _LOGGER.info("Adding cameras")
    for camera in api.get_cameras():
        _LOGGER.info("Adding nest cam uuid: %s", camera["uuid"])
        device = NestCamera(camera["uuid"], NestCameraAPI(
            hass.data[DOMAIN][CONF_EMAIL],
            hass.data[DOMAIN][CONF_PASSWORD],
            hass.data[DOMAIN][CONF_ISSUE_TOKEN],
            hass.data[DOMAIN][CONF_COOKIE],
            hass.data[DOMAIN][CONF_APIKEY],
            camera["uuid"]
        ))
        cameras.append(device)

    async_add_entities(cameras)


class NestCamera(Camera):
    """An implementation of a Nest camera."""

    def __init__(self, uuid, api):
        """Initialize a Nest camera."""
        super().__init__()
        self._uuid = uuid
        self._device = api
        self._time_between_snapshots = timedelta(seconds=30)
        self._last_image = None
        self._next_snapshot_at = None

    @property
    def device_info(self):
        """Return information about the device."""
        return {
            "identifiers": {(DOMAIN, self._uuid)},
            "name": self.name,
            "manufacturer": "Nest Labs",
            "model": "Camera",
        }

    @property
    def should_poll(self):
        return True

    @property
    def unique_id(self):
        """Return an unique ID."""
        return self._uuid

    @property
    def is_on(self):
        """Return true if on."""
        return self._device.online

    @property
    def is_recording(self):
        return True
        """Return true if the device is recording."""
        return self._device.is_streaming

    def turn_off(self):
        self._device.turn_off()
        self.schedule_update_ha_state()

    def turn_on(self):
        self._device.turn_on()
        self.schedule_update_ha_state()

    @property
    def supported_features(self):
        """Return supported features."""
        return SUPPORT_ON_OFF

    def update(self):
        """Cache value from Python-nest."""
        self._device.update()

    @property
    def name(self):
        """Return the name of this camera."""
        return self._device.name

    def _ready_for_snapshot(self, now):
        return self._next_snapshot_at is None or now > self._next_snapshot_at

    def camera_image(self):
        """Return a still image response from the camera."""
        now = utcnow()
        if self._ready_for_snapshot(now) or True:
            image = self._device.get_image(now)
            #  _LOGGER.info(image)

            self._next_snapshot_at = now + self._time_between_snapshots
            self._last_image = image

        return self._last_image
