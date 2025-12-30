"""Config flow for Posti Delivery Dates integration."""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    API_TIMEOUT,
    API_URL,
    CONF_INITIAL_DATA,
    CONF_POSTAL_CODE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_POSTAL_CODE): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    postal_code = data[CONF_POSTAL_CODE].strip()

    # Validate postal code format (exactly 5 digits)
    if not re.match(r"^\d{5}$", postal_code):
        raise InvalidPostalCode

    # Test API connectivity
    url = API_URL.format(postal_code=postal_code)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=API_TIMEOUT)) as response:
                if response.status != 200:
                    raise CannotConnect

                data_json = await response.json()

                # Validate we got valid data
                if not data_json or not isinstance(data_json, list):
                    raise NoData

                if len(data_json) == 0:
                    raise NoData

                first_entry = data_json[0]
                if "postalCode" not in first_entry or "deliveryDates" not in first_entry:
                    raise NoData

                if not first_entry["deliveryDates"]:
                    raise NoData

                # Store the fetched data to reuse it
                delivery_dates = first_entry["deliveryDates"]

    except aiohttp.ClientError as err:
        _LOGGER.error("Error connecting to Posti API: %s", err)
        raise CannotConnect from err
    except Exception as err:
        _LOGGER.exception("Unexpected error validating postal code: %s", err)
        raise UnknownError from err

    return {
        "title": f"Posti {postal_code}",
        "postal_code": postal_code,
        "delivery_dates": delivery_dates,
    }


class PostiDeliveryConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Posti Delivery Dates."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except InvalidPostalCode:
                errors["base"] = "invalid_postal_code"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except NoData:
                errors["base"] = "no_data"
            except UnknownError:
                errors["base"] = "unknown"
            else:
                # Check if this postal code is already configured
                await self.async_set_unique_id(info["postal_code"])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=info["title"],
                    data={
                        CONF_POSTAL_CODE: info["postal_code"],
                        CONF_INITIAL_DATA: {
                            "delivery_dates": info["delivery_dates"],
                            "last_updated": datetime.now().isoformat(),
                        },
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class InvalidPostalCode(HomeAssistantError):
    """Error to indicate invalid postal code format."""


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class NoData(HomeAssistantError):
    """Error to indicate no data was returned."""


class UnknownError(HomeAssistantError):
    """Error to indicate an unknown error occurred."""
