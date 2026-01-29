"""DataUpdateCoordinator for Posti Delivery Dates integration."""

from __future__ import annotations

import logging
from datetime import date, datetime

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

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

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{postal_code}",
            update_interval=DEFAULT_UPDATE_INTERVAL,
        )

        # If initial data is provided, use it and skip first API fetch
        if initial_data:
            self.data = {
                "delivery_dates": initial_data.get("delivery_dates", []),
                "last_updated": datetime.fromisoformat(initial_data["last_updated"]),
                "last_delivery_date": None,  # No deliveries have occurred yet
            }
            self._skip_first_update = True
            _LOGGER.debug(
                "Initialized coordinator for %s with cached data from config flow",
                postal_code,
            )

    def _check_last_delivery(self) -> str | None:
        """Check if the previous next delivery has now passed."""
        if not self.data:
            return None

        last_delivery_date = self.data.get("last_delivery_date")
        prev_delivery_dates = self.data.get("delivery_dates", [])

        if not prev_delivery_dates:
            return last_delivery_date

        today = date.today()
        # Get previous next delivery (first future date from previous data)
        prev_future_dates = [
            d for d in prev_delivery_dates if datetime.strptime(d, "%Y-%m-%d").date() >= today
        ]
        prev_next_delivery = prev_future_dates[0] if prev_future_dates else None

        # If previous next delivery is now in the past, it's our last delivery
        if prev_next_delivery:
            prev_delivery_date = datetime.strptime(prev_next_delivery, "%Y-%m-%d").date()
            if prev_delivery_date < today:
                _LOGGER.debug(
                    "Delivery date %s has passed for postal code %s",
                    prev_next_delivery,
                    self.postal_code,
                )
                return prev_next_delivery

        return last_delivery_date

    def _is_data_stale(self) -> bool:
        """Check if cached data is stale (older than update interval)."""
        if not self.data:
            return True

        last_updated = self.data.get("last_updated")
        if not last_updated:
            return True

        # Data is stale if it's older than the update interval
        age = datetime.now() - last_updated
        is_stale = age > DEFAULT_UPDATE_INTERVAL

        if is_stale:
            _LOGGER.warning(
                "Data for %s is stale (age: %s, threshold: %s). Forcing refresh.",
                self.postal_code,
                age,
                DEFAULT_UPDATE_INTERVAL,
            )

        return is_stale

    async def _async_update_data(self) -> dict:
        """Fetch data from Posti API."""
        # Check if data is stale and force refresh if needed
        if self._is_data_stale() and not self._skip_first_update:
            _LOGGER.info(
                "Forcing API fetch for %s due to stale data",
                self.postal_code,
            )
            # Continue to API fetch below

        # If we have initial data from config flow, skip the first API fetch
        elif self._skip_first_update:
            self._skip_first_update = False
            self._first_update = False
            _LOGGER.debug(
                "Skipping first API fetch for %s (using cached data)",
                self.postal_code,
            )
            return self.data

        # Log first update
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

                    # Track last delivery date
                    last_delivery_date = self._check_last_delivery()

                    # Update successful, use normal interval
                    self.update_interval = DEFAULT_UPDATE_INTERVAL

                    return {
                        "delivery_dates": delivery_dates,
                        "last_updated": datetime.now(),
                        "last_delivery_date": last_delivery_date,
                    }

        except aiohttp.ClientError as err:
            # Update failed, retry more frequently
            self.update_interval = RETRY_UPDATE_INTERVAL
            raise UpdateFailed(f"Error communicating with Posti API: {err}") from err
        except Exception as err:
            # Update failed, retry more frequently
            self.update_interval = RETRY_UPDATE_INTERVAL
            raise UpdateFailed(f"Unexpected error fetching Posti data: {err}") from err
