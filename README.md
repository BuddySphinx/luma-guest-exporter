# Luma Guest Exporter

Export guest lists (names + emails) from Luma events to CSV files using the Luma API.

## Prerequisites

- Python 3.9+
- A Luma account with **Luma Plus** subscription on the calendar you want to access
- pip (Python package manager)

## Setup

### 1. Install dependencies

```bash
pip3 install requests
```

### 2. Get your Luma API key

1. Log in to [lu.ma](https://lu.ma)
2. Select your calendar
3. Go to **Settings > Developer**
4. Copy the API key

### 3. Save your API key

```bash
python3 export_guests.py --setup
```

Paste your API key when prompted. It will be saved locally in `config.ini` (this file is gitignored and never uploaded).

## Usage

```bash
python3 export_guests.py
```

The script will prompt you to paste a Luma event URL. It accepts three types of URLs:

| URL Type | Example |
|----------|---------|
| Public event page | `https://luma.com/abc123` or `https://lu.ma/abc123` |
| Manage page | `https://luma.com/event/manage/evt-xxx/overview` |
| Guest list page | `https://luma.com/event/manage/evt-xxx/guests` |

You can use whichever URL you have access to. The management/guest URLs are fastest since they skip a lookup step.

### Output

Guest data is saved to `output/<Event Name>_<Date>.csv` with these columns:

| Column | Description |
|--------|-------------|
| Name | Display name |
| Email | Email address |
| First Name | First name from user profile |
| Last Name | Last name from user profile |
| Status | Approval status (approved, pending_approval, declined) |
| Ticket Type | Ticket name (e.g. Standard, VIP) |
| Registration Date | Date the guest registered (YYYY-MM-DD) |

The CSV file can be opened in Excel, Google Sheets, or Apple Numbers.

## Notes

- **API key security**: Your API key is stored in `config.ini` locally. Never commit this file to git.
- **Rate limits**: Luma limits API requests to 300 per minute. The script handles this automatically.
- **Pagination**: The script fetches all guests across multiple pages and deduplicates results.
- **Multiple events**: Run the script again with a different event URL to export another event's guests.
- **Access**: You can only export guests for events on calendars where you have a Luma Plus subscription and a valid API key.

## How to run it for the first time

```bash
# Clone the repo
git clone https://github.com/BuddySphinx/luma-guest-exporter.git
cd luma-guest-exporter

# Install dependency
pip3 install requests

# Save your API key (one-time)
python3 export_guests.py --setup

# Export guests from an event
python3 export_guests.py
```
