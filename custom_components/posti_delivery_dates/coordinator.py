"""DataUpdateCoordinator for Posti Delivery Dates integration."""

from __future__ import annotations

import logging
from datetime import date, datetime

import aiohttp

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    API_TIMEOUT,
    API_URL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    RETRY_UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class PostiDeliveryCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Posti delivery data."""

    def __init__(
        self, hass: HomeAssistant, postal_code: str, initial_data: dict | None = None
    ) -> None:
        """Initialize the coordinator."""
        self.postal_code = postal_code
        self._first_update = True
        self._skip_first_update = False
        self._tracked_next_delivery: str | None = None
        self._remove_midnight_tracker = None

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{postal_code}",
            update_interval=DEFAULT_UPDATE_INTERVAL,
        )

        if initial_data:
            self.data = {
                "delivery_dates": initial_data.get("delivery_dates", []),
                "last_updated": dt_util.as_local(
                    datetime.fromisoformat(initial_data["last_updated"])
                ),
                "last_delivery_date": initial_data.get("last_delivery_date"),
            }
            self._skip_first_update = True
            _LOGGER.debug(
                "Initialized coordinator for %s with cached data from config flow",
                postal_code,
            )

            if self._is_data_stale():
                last_updated = self.data.get("last_updated")
                age = dt_util.now() - last_updated if last_updated else None
                self.update_interval = RETRY_UPDATE_INTERVAL
                self._skip_first_update = False
                _LOGGER.warning(
                    "Data for %s is stale (age: %s, threshold: %s). Forcing refresh.",
                    postal_code,
                    age,
                    DEFAULT_UPDATE_INTERVAL,
                )

    def setup(self) -> None:
        """Set up midnight tracking after initial data load."""
        if self.data:
            self._tracked_next_delivery = self._get_next_delivery()

        self._remove_midnight_tracker = async_track_time_change(
            self.hass, self._handle_midnight, hour=0, minute=0, second=0
        )

    def shutdown(self) -> None:
        """Remove midnight tracker."""
        if self._remove_midnight_tracker:
            self._remove_midnight_tracker()

    @callback
    def _handle_midnight(self, now: datetime) -> None:
        """Update state at midnight when dates roll over."""
        if not self.data:
            return
        updated_last = self._update_last_delivery()
        self.async_set_updated_data({**self.data, "last_delivery_date": updated_last})

    def _get_next_delivery(self) -> str | None:
        """Return first future delivery date from current data."""
        if not self.data:
            return None
        today = date.today()
        return next(
            (
                d
                for d in self.data.get("delivery_dates", [])
                if datetime.strptime(d, "%Y-%m-%d").date() >= today
            ),
            None,
        )

    def _update_last_delivery(self) -> str | None:
        """Check if tracked next delivery has passed; return updated last_delivery_date."""
        current_last = self.data.get("last_delivery_date") if self.data else None

        if self._tracked_next_delivery:
            tracked_date = datetime.strptime(self._tracked_next_delivery, "%Y-%m-%d").date()
            if tracked_date < date.today():
                _LOGGER.debug(
                    "Delivery %s has passed for postal code %s",
                    self._tracked_next_delivery,
                    self.postal_code,
                )
                current_last = self._tracked_next_delivery

        self._tracked_next_delivery = self._get_next_delivery()
        return current_last

    def _is_data_stale(self) -> bool:
        """Check if cached data is stale (older than update interval)."""
        if not self.data:
            return True
        last_updated = self.data.get("last_updated")
        if not last_updated:
            return True
        return (dt_util.now() - last_updated) > DEFAULT_UPDATE_INTERVAL

    async def _async_update_data(self) -> dict:
        """Fetch data from Posti API."""
        if self._is_data_stale() and not self._skip_first_update:
            _LOGGER.info(
                "Forcing API fetch for %s due to stale data",
                self.postal_code,
            )

        elif self._skip_first_update:
            self._skip_first_update = False
            self._first_update = False
            _LOGGER.debug(
                "Skipping first API fetch for %s (using cached data)",
                self.postal_code,
            )
            return self.data

        if self._first_update:
            _LOGGER.debug("First update for %s", self.postal_code)
            self._first_update = False

        url = API_URL.format(postal_code=self.postal_code)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=API_TIMEOUT)
                ) as response:
                    if response.status != 200:
                        raise UpdateFailed(
                            f"Error fetching data from Posti API: HTTP {response.status}"
                        )

                    data = await response.json()

                    if not data or not isinstance(data, list) or len(data) == 0:
                        raise UpdateFailed("No data returned from Posti API")

                    first_entry = data[0]
                    if "deliveryDates" not in first_entry:
                        raise UpdateFailed("Invalid data structure from Posti API")

                    delivery_dates = first_entry["deliveryDates"]
                    if not delivery_dates:
                        raise UpdateFailed("No delivery dates returned from Posti API")

                    _LOGGER.debug(
                        "Successfully fetched %d delivery dates for postal code %s",
                        len(delivery_dates),
                        self.postal_code,
                    )

                    last_delivery_date = self._update_last_delivery()
                    self.update_interval = DEFAULT_UPDATE_INTERVAL

                    return {
                        "delivery_dates": delivery_dates,
                        "last_updated": dt_util.now(),
                        "last_delivery_date": last_delivery_date,
                    }

        except aiohttp.ClientError as err:
            self.update_interval = RETRY_UPDATE_INTERVAL
            raise UpdateFailed(f"Error communicating with Posti API: {err}") from err
        except Exception as err:
            self.update_interval = RETRY_UPDATE_INTERVAL
            raise UpdateFailed(f"Unexpected error fetching Posti data: {err}") from err
