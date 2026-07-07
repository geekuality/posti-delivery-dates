"""The Posti Delivery Dates integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_INITIAL_DATA, CONF_POSTAL_CODE, DOMAIN
from .coordinator import PostiDeliveryCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Posti Delivery Dates from a config entry."""
    postal_code = entry.data[CONF_POSTAL_CODE]
    initial_data = entry.data.get(CONF_INITIAL_DATA)

    coordinator = PostiDeliveryCoordinator(hass, postal_code, initial_data)

    await coordinator.async_config_entry_first_refresh()
    coordinator.setup()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    def _persist_coordinator_data() -> None:
        if coordinator.last_update_success and coordinator.data:
            hass.config_entries.async_update_entry(
                entry,
                data={
                    **entry.data,
                    CONF_INITIAL_DATA: {
                        "delivery_dates": coordinator.data["delivery_dates"],
                        "last_updated": coordinator.data["last_updated"].isoformat(),
                        "last_delivery_date": coordinator.data.get("last_delivery_date"),
                    },
                },
            )

    entry.async_on_unload(coordinator.async_add_listener(_persist_coordinator_data))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: PostiDeliveryCoordinator | None = hass.data[DOMAIN].get(entry.entry_id)

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        if coordinator:
            coordinator.shutdown()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
