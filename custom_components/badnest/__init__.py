"""The example integration."""
import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

from .const import DOMAIN

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_EMAIL): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)
