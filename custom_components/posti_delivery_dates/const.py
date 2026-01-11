"""Constants for the Posti Delivery Dates integration."""

from datetime import timedelta

DOMAIN = "posti_delivery_dates"

# API Configuration
API_URL = "https://www.posti.fi/maildelivery-api-proxy/?q={postal_code}"
API_TIMEOUT = 10

# Update Configuration
DEFAULT_UPDATE_INTERVAL = timedelta(hours=12)
INITIAL_RANDOM_OFFSET_MAX = timedelta(minutes=30)
UPDATE_JITTER_MAX = timedelta(minutes=2)

# Configuration
CONF_POSTAL_CODE = "postal_code"
CONF_INITIAL_DATA = "initial_data"

# Sensor Attributes
ATTR_ALL_DELIVERY_DATES = "all_delivery_dates"
ATTR_NEXT_SCHEDULED_DATE = "next_scheduled_date"
ATTR_LAST_SCHEDULED_DATE = "last_scheduled_date"
ATTR_DAYS_UNTIL_NEXT = "days_until_next"
ATTR_DELIVERY_COUNT = "delivery_count"
ATTR_POSTAL_CODE = "postal_code"
ATTR_LAST_UPDATED = "last_updated"

# Device Info
MANUFACTURER = "Community Integration"
MODEL = "Posti Mail Delivery Schedule"
