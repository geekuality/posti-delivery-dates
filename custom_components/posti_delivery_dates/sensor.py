"""Sensor platform for Posti Delivery Dates integration."""

from __future__ import annotations

from datetime import date, datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_ALL_DELIVERY_DATES,
    ATTR_DAYS_UNTIL_NEXT,
    ATTR_DELIVERY_COUNT,
    ATTR_LAST_SCHEDULED_DATE,
    ATTR_LAST_UPDATED,
    ATTR_NEXT_SCHEDULED_DATE,
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
        self._remove_midnight_tracker = None

    async def async_added_to_hass(self) -> None:
        """Handle entity added to hass."""
        await super().async_added_to_hass()

        # Track midnight to update state when dates change
        self._remove_midnight_tracker = async_track_time_change(
            self.hass, self._handle_midnight, hour=0, minute=0, second=0
        )

    async def async_will_remove_from_hass(self) -> None:
        """Handle entity removal."""
        if self._remove_midnight_tracker:
            self._remove_midnight_tracker()
        await super().async_will_remove_from_hass()

    @callback
    def _handle_midnight(self, now: datetime) -> None:
        """Handle midnight time change to update sensor state."""
        # Force state update at midnight since date filtering changes
        self.async_write_ha_state()

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor (next future delivery date)."""
        if not self.coordinator.data:
            return None

        delivery_dates = self.coordinator.data.get("delivery_dates", [])
        if not delivery_dates:
            return None

        # Filter to get only future dates (today or later)
        today = date.today()
        future_dates = [
            d for d in delivery_dates if datetime.strptime(d, "%Y-%m-%d").date() >= today
        ]

        # Return the first future date, or None if all dates are in the past
        return future_dates[0] if future_dates else None

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
                ATTR_NEXT_SCHEDULED_DATE: None,
                ATTR_LAST_SCHEDULED_DATE: None,
                ATTR_DAYS_UNTIL_NEXT: None,
                ATTR_LAST_UPDATED: last_updated.isoformat() if last_updated else None,
            }

        today = date.today()

        # Get future dates only
        future_dates = [
            d for d in delivery_dates if datetime.strptime(d, "%Y-%m-%d").date() >= today
        ]

        # Get next delivery (first future date)
        next_delivery = future_dates[0] if future_dates else None

        # Get last scheduled date from coordinator (tracked when delivery passes)
        last_scheduled = self.coordinator.data.get("last_delivery_date")

        # Calculate days until next delivery
        days_until_next = None
        if next_delivery:
            try:
                next_date = datetime.strptime(next_delivery, "%Y-%m-%d").date()
                days_until_next = (next_date - today).days
            except (ValueError, TypeError):
                pass

        return {
            ATTR_POSTAL_CODE: self._postal_code,
            ATTR_NEXT_SCHEDULED_DATE: next_delivery,
            ATTR_LAST_SCHEDULED_DATE: last_scheduled,
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
