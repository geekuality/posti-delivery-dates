# Posti Delivery Dates - Home Assistant Integration

A custom Home Assistant integration for tracking Posti Finland mail delivery dates by postal code.

> [!NOTE]
> This integration is not approved, supported or endorsed by Posti Group Oy in any way, shape or form. It uses a publicly available API endpoint. The Posti logo is a trademark of Posti Group Oy — its use within Home Assistant is purely informative and does not imply partnership or affiliation.

## Features

- **UI Configuration**: Add postal codes through Home Assistant's UI
- **Multiple Postal Codes**: Track delivery dates for multiple locations
- **Automatic Updates**: Fetches delivery dates every 12 hours
- **Device per Postal Code**: Each postal code creates a device with six sensor entities
- **Offline Resilience**: Retains last known data when API is temporarily unavailable

## Installation

### HACS (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=geekuality&repository=posti-delivery-dates&category=Integration)

Or add this repository (`geekuality/posti-delivery-dates`) as a custom repository in HACS, then install "Posti Delivery Dates" and restart Home Assistant.

### Manual Installation

1. Download or clone this repository
2. Copy the `custom_components/posti_delivery_dates` directory to your Home Assistant's `config/custom_components/` directory
3. Your final path should be: `config/custom_components/posti_delivery_dates/`
4. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Posti Delivery Dates"
4. Enter a Finnish postal code (5 digits, e.g., `00100`)
5. The integration will validate the postal code and fetch initial data

To add multiple postal codes, repeat the process.

## Sensors

Each postal code creates six sensors.

### Next Delivery (`sensor.posti_XXXXX_next_delivery`)

State: next future delivery date (`device_class: date`).

| Attribute | Description |
|---|---|
| `postal_code` | Postal code being tracked |
| `next_scheduled_date` | Next future delivery date (ISO format) |
| `next_scheduled_weekday` | Weekday name, e.g. `"Monday"` |

### Days Until Next Delivery (`sensor.posti_XXXXX_days_until_next_delivery`)

State: integer count of days until the next delivery, in days.

### Last Delivery (`sensor.posti_XXXXX_last_delivery`)

State: most recent past delivery date (`device_class: date`). `null` until the first delivery is detected after installation.

| Attribute | Description |
|---|---|
| `postal_code` | Postal code being tracked |
| `last_scheduled_date` | Last delivery date (ISO format) |
| `last_scheduled_weekday` | Weekday name, e.g. `"Friday"` |

### Days Since Last Delivery (`sensor.posti_XXXXX_days_since_last_delivery`)

State: integer count of days elapsed since the last delivery, in days.

### All Delivery Dates (`sensor.posti_XXXXX_all_delivery_dates`) — diagnostic

State: total count of dates returned by the API.

| Attribute | Description |
|---|---|
| `delivery_count` | Same as state |
| `all_delivery_dates` | Full list of all delivery dates from the API (includes past dates) |

### Last Updated (`sensor.posti_XXXXX_last_updated`) — diagnostic

State: timestamp of the last successful API fetch (`device_class: timestamp`).

## Example Usage

### Dashboard

Simple entity card:
```yaml
type: entity
entity: sensor.posti_00100_next_delivery
```

Entities card:
```yaml
type: entities
entities:
  - entity: sensor.posti_00100_next_delivery
    name: Next Delivery
  - entity: sensor.posti_00100_days_until_next_delivery
    name: Days Until
  - entity: sensor.posti_00100_last_delivery
    name: Last Delivery
  - entity: sensor.posti_00100_days_since_last_delivery
    name: Days Since
```

Markdown card:
```yaml
type: markdown
content: |
  ## 📬 Mail Delivery Schedule

  **Next:** {{ state_attr('sensor.posti_00100_next_delivery', 'next_scheduled_weekday') }} {{ states('sensor.posti_00100_next_delivery') }}
  **In {{ states('sensor.posti_00100_days_until_next_delivery') }} days**

  Last: {{ state_attr('sensor.posti_00100_last_delivery', 'last_scheduled_weekday') }} {{ states('sensor.posti_00100_last_delivery') or 'N/A' }}
```

### Automation Example

```yaml
automation:
  - alias: "Mail Delivery Reminder"
    trigger:
      - platform: time
        at: "08:00:00"
    condition:
      - condition: numeric_state
        entity_id: sensor.posti_00100_days_until_next_delivery
        below: 1
    action:
      - service: notify.mobile_app
        data:
          message: "Mail delivery today!"
```

## API Information

This integration uses Posti Finland's public delivery date API:
- Endpoint: `https://www.posti.fi/maildelivery-api-proxy/?q=<postal_code>`
- Update frequency: Every 12 hours
- No authentication required

## Troubleshooting

### Integration won't add
- Verify the postal code is exactly 5 digits
- Check internet connectivity
- Verify the postal code is valid for Finland

### Sensor shows "Unavailable"
- The integration retains last known data during temporary API outages
- Check the Last Updated sensor to see when data was last refreshed
- The sensor only becomes unavailable if no data has ever been fetched successfully

### No delivery dates returned
- Verify the postal code with Posti Finland's website
- Some postal codes may not have regular delivery schedules

## Development

### Version Scheme
This integration uses date-based versioning (`YYYY.M.MINOR`) similar to Home Assistant core.

## License

MIT — see [LICENSE](LICENSE)
