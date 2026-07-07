"""Sensor platform for Posti Delivery Dates integration."""

from __future__ import annotations

import logging
from datetime import date, datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_ALL_DELIVERY_DATES,
    ATTR_DELIVERY_COUNT,
    ATTR_LAST_SCHEDULED_DATE,
    ATTR_LAST_SCHEDULED_WEEKDAY,
    ATTR_NEXT_SCHEDULED_DATE,
    ATTR_NEXT_SCHEDULED_WEEKDAY,
    ATTR_POSTAL_CODE,
    CONF_POSTAL_CODE,
    DOMAIN,
    MANUFACTURER,
    MODEL,
)
from .coordinator import PostiDeliveryCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Posti Delivery sensors from a config entry."""
    coordinator: PostiDeliveryCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    postal_code = config_entry.data[CONF_POSTAL_CODE]

    async_add_entities(
        [
            PostiNextDeliverySensor(coordinator, postal_code),
            PostiDaysUntilNextSensor(coordinator, postal_code),
            PostiLastDeliverySensor(coordinator, postal_code),
            PostiDaysSinceLastSensor(coordinator, postal_code),
            PostiAllDeliveryDatesSensor(coordinator, postal_code),
            PostiLastUpdatedSensor(coordinator, postal_code),
        ]
    )


def _device_info(postal_code: str) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, postal_code)},
        name=f"Posti {postal_code}",
        manufacturer=MANUFACTURER,
        model=MODEL,
        entry_type="service",
    )


class PostiNextDeliverySensor(CoordinatorEntity, SensorEntity):
    """Next scheduled delivery date."""

    _attr_has_entity_name = True
    _attr_name = "Next Delivery"
    _attr_icon = "mdi:mailbox"
    _attr_device_class = SensorDeviceClass.DATE

    def __init__(self, coordinator: PostiDeliveryCoordinator, postal_code: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._postal_code = postal_code
        self._attr_unique_id = f"{DOMAIN}_{postal_code}"
        self._attr_device_info = _device_info(postal_code)

    @property
    def native_value(self) -> date | None:
        """Return next future delivery date."""
        if not self.coordinator.data:
            return None
        today = date.today()
        return next(
            (
                datetime.strptime(d, "%Y-%m-%d").date()
                for d in self.coordinator.data.get("delivery_dates", [])
                if datetime.strptime(d, "%Y-%m-%d").date() >= today
            ),
            None,
        )

    @property
    def extra_state_attributes(self) -> dict:
        """Return next delivery attributes."""
        if not self.coordinator.data:
            return {}

        today = date.today()
        next_delivery_str = next(
            (
                d
                for d in self.coordinator.data.get("delivery_dates", [])
                if datetime.strptime(d, "%Y-%m-%d").date() >= today
            ),
            None,
        )

        return {
            ATTR_POSTAL_CODE: self._postal_code,
            ATTR_NEXT_SCHEDULED_DATE: next_delivery_str,
            ATTR_NEXT_SCHEDULED_WEEKDAY: (
                datetime.strptime(next_delivery_str, "%Y-%m-%d").strftime("%A")
                if next_delivery_str
                else None
            ),
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success or self.coordinator.data is not None


class PostiDaysUntilNextSensor(CoordinatorEntity, SensorEntity):
    """Days remaining until next scheduled delivery."""

    _attr_has_entity_name = True
    _attr_name = "Days Until Next Delivery"
    _attr_icon = "mdi:calendar-arrow-right"
    _attr_native_unit_of_measurement = UnitOfTime.DAYS

    def __init__(self, coordinator: PostiDeliveryCoordinator, postal_code: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._postal_code = postal_code
        self._attr_unique_id = f"{DOMAIN}_{postal_code}_days_until_next"
        self._attr_device_info = _device_info(postal_code)

    @property
    def native_value(self) -> int | None:
        """Return days until next delivery."""
        if not self.coordinator.data:
            return None
        today = date.today()
        next_str = next(
            (
                d
                for d in self.coordinator.data.get("delivery_dates", [])
                if datetime.strptime(d, "%Y-%m-%d").date() >= today
            ),
            None,
        )
        if not next_str:
            return None
        return (datetime.strptime(next_str, "%Y-%m-%d").date() - today).days

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success or self.coordinator.data is not None


class PostiLastDeliverySensor(CoordinatorEntity, SensorEntity):
    """Most recent past delivery date."""

    _attr_has_entity_name = True
    _attr_name = "Last Delivery"
    _attr_icon = "mdi:mailbox-open"
    _attr_device_class = SensorDeviceClass.DATE

    def __init__(self, coordinator: PostiDeliveryCoordinator, postal_code: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._postal_code = postal_code
        self._attr_unique_id = f"{DOMAIN}_{postal_code}_last_delivery"
        self._attr_device_info = _device_info(postal_code)

    @property
    def native_value(self) -> date | None:
        """Return last delivery date."""
        if not self.coordinator.data:
            return None
        last = self.coordinator.data.get("last_delivery_date")
        if not last:
            return None
        return datetime.strptime(last, "%Y-%m-%d").date()

    @property
    def extra_state_attributes(self) -> dict:
        """Return last delivery attributes."""
        if not self.coordinator.data:
            return {}

        last = self.coordinator.data.get("last_delivery_date")
        attrs: dict = {ATTR_POSTAL_CODE: self._postal_code}

        if last:
            attrs[ATTR_LAST_SCHEDULED_DATE] = last
            attrs[ATTR_LAST_SCHEDULED_WEEKDAY] = datetime.strptime(last, "%Y-%m-%d").strftime("%A")

        return attrs

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success or self.coordinator.data is not None


class PostiDaysSinceLastSensor(CoordinatorEntity, SensorEntity):
    """Days elapsed since last scheduled delivery."""

    _attr_has_entity_name = True
    _attr_name = "Days Since Last Delivery"
    _attr_icon = "mdi:calendar-arrow-left"
    _attr_native_unit_of_measurement = UnitOfTime.DAYS

    def __init__(self, coordinator: PostiDeliveryCoordinator, postal_code: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._postal_code = postal_code
        self._attr_unique_id = f"{DOMAIN}_{postal_code}_days_since_last"
        self._attr_device_info = _device_info(postal_code)

    @property
    def native_value(self) -> int | None:
        """Return days since last delivery."""
        if not self.coordinator.data:
            return None
        last = self.coordinator.data.get("last_delivery_date")
        if not last:
            return None
        return (date.today() - datetime.strptime(last, "%Y-%m-%d").date()).days

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success or self.coordinator.data is not None


class PostiAllDeliveryDatesSensor(CoordinatorEntity, SensorEntity):
    """Count of all scheduled delivery dates with full list as attribute."""

    _attr_has_entity_name = True
    _attr_name = "All Delivery Dates"
    _attr_icon = "mdi:calendar-multiselect"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PostiDeliveryCoordinator, postal_code: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._postal_code = postal_code
        self._attr_unique_id = f"{DOMAIN}_{postal_code}_all_dates"
        self._attr_device_info = _device_info(postal_code)

    @property
    def native_value(self) -> int | None:
        """Return total count of delivery dates."""
        if not self.coordinator.data:
            return None
        return len(self.coordinator.data.get("delivery_dates", []))

    @property
    def extra_state_attributes(self) -> dict:
        """Return full list of delivery dates."""
        if not self.coordinator.data:
            return {}
        delivery_dates = self.coordinator.data.get("delivery_dates", [])
        return {
            ATTR_DELIVERY_COUNT: len(delivery_dates),
            ATTR_ALL_DELIVERY_DATES: delivery_dates,
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success or self.coordinator.data is not None


class PostiLastUpdatedSensor(CoordinatorEntity, SensorEntity):
    """Timestamp of last successful data fetch — diagnostic."""

    _attr_has_entity_name = True
    _attr_name = "Last Updated"
    _attr_icon = "mdi:clock-outline"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PostiDeliveryCoordinator, postal_code: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._postal_code = postal_code
        self._attr_unique_id = f"{DOMAIN}_{postal_code}_last_updated"
        self._attr_device_info = _device_info(postal_code)

    @property
    def native_value(self) -> datetime | None:
        """Return timestamp of last data fetch."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("last_updated")

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success or self.coordinator.data is not None
