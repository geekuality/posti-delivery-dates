"""DataUpdateCoordinator for Posti Delivery Dates integration."""
from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_TIMEOUT,
    API_URL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    INITIAL_RANDOM_OFFSET_MAX,
    UPDATE_JITTER_MAX,
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
            }
            self._skip_first_update = True
            _LOGGER.debug(
                "Initialized coordinator for %s with cached data from config flow",
                postal_code,
            )

    async def _async_update_data(self) -> dict:
        """Fetch data from Posti API."""
        # If we have initial data from config flow, skip the first API fetch
        if self._skip_first_update:
            self._skip_first_update = False
            self._first_update = False
            # Schedule next update with offset
            offset_seconds = random.randint(0, int(INITIAL_RANDOM_OFFSET_MAX.total_seconds()))
            self.update_interval = DEFAULT_UPDATE_INTERVAL + timedelta(seconds=offset_seconds)
            _LOGGER.debug(
                "Skipping first API fetch for %s (using cached data), next update in %s",
                self.postal_code,
                self.update_interval,
            )
            return self.data

        # Add initial random offset on first update (when no initial data was provided)
        if self._first_update:
            offset_seconds = random.randint(0, int(INITIAL_RANDOM_OFFSET_MAX.total_seconds()))
            _LOGGER.debug(
                "First update for %s, adding random offset of %d seconds",
                self.postal_code,
                offset_seconds,
            )
            self._first_update = False
            # Schedule next update with offset
            self.update_interval = DEFAULT_UPDATE_INTERVAL + timedelta(seconds=offset_seconds)

        # Add jitter to update interval (after first update)
        else:
            jitter_seconds = random.randint(
                -int(UPDATE_JITTER_MAX.total_seconds()),
                int(UPDATE_JITTER_MAX.total_seconds()),
            )
            self.update_interval = DEFAULT_UPDATE_INTERVAL + timedelta(seconds=jitter_seconds)
            _LOGGER.debug(
                "Adding jitter of %d seconds to update interval for %s",
                jitter_seconds,
                self.postal_code,
            )

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

                    return {
                        "delivery_dates": delivery_dates,
                        "last_updated": datetime.now(),
                    }

        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with Posti API: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error fetching Posti data: {err}") from err
