"""The example integration."""
import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from .const import DOMAIN
from homeassistant.const import (
    CONF_EMAIL,
    CONF_PASSWORD
)

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

def setup(hass, config):
    """Set up the asuswrt component."""
    if config.get(DOMAIN) is not None:
        email = config[DOMAIN].get(CONF_EMAIL)
        password = config[DOMAIN].get(CONF_PASSWORD)
    else:
        email = None
        password = None

    from .api import NestAPI
    api = NestAPI(
        email,
        password
    )

    hass.data[DOMAIN] = api

    return True
