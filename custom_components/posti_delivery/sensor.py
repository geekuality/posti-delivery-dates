"""Sensor platform for Posti Delivery Dates integration."""
from __future__ import annotations

from datetime import datetime, date

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_ALL_DELIVERY_DATES,
    ATTR_DAYS_UNTIL_NEXT,
    ATTR_DELIVERY_COUNT,
    ATTR_LAST_UPDATED,
    ATTR_NEXT_DELIVERY,
    ATTR_POSTAL_CODE,
    CONF_POSTAL_CODE,
    DOMAIN,
    MANUFACTURER,
    MODEL,
)
from .coordinator import PostiDeliveryCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Posti Delivery sensor from a config entry."""
    coordinator: PostiDeliveryCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    postal_code = config_entry.data[CONF_POSTAL_CODE]

    async_add_entities([PostiDeliverySensor(coordinator, postal_code, config_entry)])


class PostiDeliverySensor(CoordinatorEntity, SensorEntity):
    """Representation of a Posti Delivery sensor."""

    _attr_has_entity_name = True
    _attr_name = "Next Delivery"
    _attr_icon = "mdi:mailbox"

    def __init__(
        self,
        coordinator: PostiDeliveryCoordinator,
        postal_code: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._postal_code = postal_code
        self._attr_unique_id = f"{DOMAIN}_{postal_code}"

        # Device info - creates a device for this postal code
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, postal_code)},
            name=f"Posti {postal_code}",
            manufacturer=MANUFACTURER,
            model=MODEL,
            entry_type="service",
        )

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor (next delivery date)."""
        if not self.coordinator.data:
            return None

        delivery_dates = self.coordinator.data.get("delivery_dates", [])
        if not delivery_dates:
            return None

        return delivery_dates[0]

    @property
    def extra_state_attributes(self) -> dict[str, any]:
        """Return the state attributes."""
        if not self.coordinator.data:
            return {}

        delivery_dates = self.coordinator.data.get("delivery_dates", [])
        last_updated = self.coordinator.data.get("last_updated")

        if not delivery_dates:
            return {
                ATTR_POSTAL_CODE: self._postal_code,
                ATTR_DELIVERY_COUNT: 0,
                ATTR_ALL_DELIVERY_DATES: [],
                ATTR_LAST_UPDATED: last_updated.isoformat() if last_updated else None,
            }

        next_delivery = delivery_dates[0]
        days_until_next = None

        # Calculate days until next delivery
        try:
            next_date = datetime.strptime(next_delivery, "%Y-%m-%d").date()
            today = date.today()
            days_until_next = (next_date - today).days
        except (ValueError, TypeError):
            pass

        return {
            ATTR_POSTAL_CODE: self._postal_code,
            ATTR_NEXT_DELIVERY: next_delivery,
            ATTR_DAYS_UNTIL_NEXT: days_until_next,
            ATTR_DELIVERY_COUNT: len(delivery_dates),
            ATTR_ALL_DELIVERY_DATES: delivery_dates,
            ATTR_LAST_UPDATED: last_updated.isoformat() if last_updated else None,
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Entity is available if we have data (even if it's old)
        # or if the coordinator is available (first successful fetch)
        return self.coordinator.last_update_success or self.coordinator.data is not None
