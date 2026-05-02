# Luma Event Guest Exporter

## Problem

As an event organizer on Luma with multiple events, manually exporting guest lists (names + emails) from each event is tedious. Need an automated tool to pull attendee data via the Luma API and save it locally as CSV files, so the data can be used to send emails to participants.

## User Profile

- Event organizer on Luma with a Luma Plus subscription (required for API access)
- No coding background
- Uses a Mac
- Wants CSV files to keep locally and use for sending emails via Gmail

## Solution

A Python script that uses the Luma API to export guest lists from any event into CSV files.

## Architecture

Single Python script (`export_guests.py`) that:

1. Reads API key from a local config file (`config.ini`)
2. Prompts user to paste a Luma event URL
3. Extracts the event slug from the URL (e.g. `abc123` from `https://lu.ma/abc123`)
4. Looks up the event ID via the Luma API (slug-based lookup if needed)
5. Calls the Luma API `Get Guests` endpoint with pagination
6. Saves results to a CSV file named `{event_name}_{date}.csv`

### Components

- **`export_guests.py`** — Main script, handles user interaction and API calls
- **`config.ini`** — Stores the Luma API key (created once during setup, never committed to git)
- **`.gitignore`** — Ensures `config.ini` and CSV files are not tracked in git

### Data Flow

```
User runs script -> Script reads API key from config.ini
                 -> User pastes event URL (e.g. https://lu.ma/abc123)
                 -> Script extracts event slug/ID
                 -> Script calls Luma API Get Guests endpoint
                 -> API returns guest data (name, email, status, ticket type)
                 -> Script writes CSV to output/ directory
                 -> Script prints summary (number of guests, file location)
```

## CSV Output Format

| Name | Email | Status | Ticket Type | Registration Date |
|------|-------|--------|-------------|-------------------|

Files saved to `output/{event_name}_{YYYY-MM-DD}.csv`.

## API Details

- **Base URL**: `https://api.lu.ma`
- **Authentication**: Bearer token via `x-luma-api-key` header
- **Endpoint**: `GET /v1/event/get-guests?event_api_id={event_id}`
- **Pagination**: API returns paginated results; script handles pagination automatically
- **Required**: Luma Plus subscription on the target calendar

## Error Handling

- Missing or invalid API key: clear message telling user to check config.ini
- Invalid event URL: message explaining the expected URL format
- API error (rate limit, network): retry with backoff, then show user-friendly error
- No guests found: message indicating the event has no registered guests

## Setup Steps (one-time)

1. Ensure Python 3 is installed on Mac
2. Install `requests` library: `pip3 install requests`
3. Get API key from Luma: Calendar Settings > Developer > API Keys
4. Run setup: `python3 export_guests.py --setup` and paste API key when prompted
5. Script creates `config.ini` with the key

## Usage

```bash
python3 export_guests.py
# Paste event URL when prompted: https://lu.ma/your-event
# Output: output/Your Event_2026-05-02.csv
```

## Constraints

- API key stored locally only, never shared or committed to version control
- Script must work without coding knowledge — clear prompts and error messages
- Must handle multiple events (user provides URL each time)
- Output must be openable in Excel, Google Sheets, and Apple Numbers
