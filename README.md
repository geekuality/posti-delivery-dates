# Posti Delivery Dates - Home Assistant Integration

A custom Home Assistant integration for tracking Posti Finland mail delivery dates by postal code.

## Features

- **UI Configuration**: Add postal codes through Home Assistant's UI
- **Multiple Postal Codes**: Track delivery dates for multiple locations
- **Automatic Updates**: Fetches delivery dates every 12 hours with intelligent jitter to spread API load
- **Device per Postal Code**: Each postal code creates a device with a sensor entity
- **Rich Attributes**: Access all delivery dates, next delivery, and days until delivery
- **Offline Resilience**: Retains last known data when API is temporarily unavailable

## Installation

### HACS (Recommended)

1. Add this repository as a custom repository in HACS
2. Install "Posti Delivery Dates" from HACS
3. Restart Home Assistant

### Manual Installation

1. Download or clone this repository
2. Copy the `posti_delivery` directory to your Home Assistant's `custom_components` directory
3. Your final path should be: `config/custom_components/posti_delivery/`
4. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Posti Delivery Dates"
4. Enter a Finnish postal code (5 digits, e.g., `00100`)
5. The integration will validate the postal code and fetch initial data

To add multiple postal codes, repeat the process.

## Sensor Data

Each postal code creates a sensor with the following:

### State
The next **future** delivery date in ISO format (YYYY-MM-DD). Past dates are automatically filtered out.

### Attributes
- `postal_code`: The postal code being tracked
- `next_scheduled_date`: The next future delivery date (same as state, `null` if no future dates)
- `last_scheduled_date`: The most recent past delivery date (`null` if none or at initial setup)
- `days_until_next`: Number of days until the next delivery
- `delivery_count`: Total number of delivery dates returned by the API
- `all_delivery_dates`: Complete list of all delivery dates from API (includes past dates)
- `last_updated`: Timestamp of last successful API fetch

**Note:** The sensor automatically filters past dates from the state and `next_scheduled_date`, but preserves all dates (including past) in `all_delivery_dates` for reference.

## Example Usage

### Display in Dashboard

Simple entity card:
```yaml
type: entity
entity: sensor.posti_00100_next_delivery
```

Entities card with custom formatting:
```yaml
type: entities
entities:
  - entity: sensor.posti_00100_next_delivery
    name: Next Delivery
  - type: attribute
    entity: sensor.posti_00100_next_delivery
    attribute: days_until_next
    name: Days Until
    suffix: days
  - type: attribute
    entity: sensor.posti_00100_next_delivery
    attribute: last_scheduled_date
    name: Last Delivery
```

Markdown card showing multiple attributes:
```yaml
type: markdown
content: |
  ## 📬 Mail Delivery Schedule

  **Next:** {{ states('sensor.posti_00100_next_delivery') }}
  **In {{ state_attr('sensor.posti_00100_next_delivery', 'days_until_next') }} days**

  Last: {{ state_attr('sensor.posti_00100_next_delivery', 'last_scheduled_date') or 'N/A' }}
```

### Automation Example

```yaml
automation:
  - alias: "Mail Delivery Reminder"
    trigger:
      - platform: time
        at: "08:00:00"
    condition:
      - condition: template
        value_template: "{{ state_attr('sensor.posti_00100_next_delivery', 'days_until_next') == 0 }}"
    action:
      - service: notify.mobile_app
        data:
          message: "Mail delivery today!"
```

### Template Sensor for All Dates

```yaml
template:
  - sensor:
      - name: "All Delivery Dates"
        state: "{{ state_attr('sensor.posti_00100_next_delivery', 'delivery_count') }}"
        attributes:
          dates: "{{ state_attr('sensor.posti_00100_next_delivery', 'all_delivery_dates') }}"
```

## API Information

This integration uses Posti Finland's public delivery date API:
- Endpoint: `https://www.posti.fi/maildelivery-api-proxy/?q=<postal_code>`
- Update frequency: Every 12 hours with randomized jitter
- No authentication required

## Update Strategy

The integration provides **instant sensor availability** by reusing data from the configuration validation step.

To prevent API load spikes during regular updates, the integration implements:
- **Instant first data**: Sensor shows data immediately using cached validation data
- **Scheduled updates**: Next update occurs after 12 hours + random offset (0-30 minutes)
- **Update jitter**: ±2 minute randomization on each subsequent update
- This ensures multiple postal codes don't all update simultaneously

## Troubleshooting

### Integration won't add
- Verify the postal code is exactly 5 digits
- Check internet connectivity
- Verify the postal code is valid for Finland

### Sensor shows "Unavailable"
- The integration retains last known data during temporary API outages
- Check `last_updated` attribute to see when data was last refreshed
- Sensor only becomes unavailable if no data has ever been fetched successfully

### No delivery dates returned
- Verify the postal code with Posti Finland's website
- Some postal codes may not have regular delivery schedules

## Development

### Version Scheme
This integration uses date-based versioning (YYYY.MM.PATCH) similar to Home Assistant core.

### Contributing
Contributions are welcome! Please open an issue or pull request on GitHub.

## License

This integration is provided as-is for personal use.

## Acknowledgments

- Data provided by Posti Finland
- Built for Home Assistant
