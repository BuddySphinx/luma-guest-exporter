# Luma Guest Exporter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python script that exports event guest lists (names + emails) from Luma via their API and saves them as CSV files.

**Architecture:** Single-script CLI tool. User runs it, pastes a Luma event URL, the script calls the Luma API to fetch guests, and writes a CSV file to an `output/` directory. Config (API key) stored in `config.ini`. No external framework beyond `requests`.

**Tech Stack:** Python 3.9, `requests` library, `csv` (stdlib), `configparser` (stdlib)

---

## File Structure

| File | Responsibility |
|------|---------------|
| `export_guests.py` | Main script — config setup, API calls, CSV export, user interaction |
| `config.ini` | Stores API key (gitignored, created by `--setup`) |
| `.gitignore` | Prevents `config.ini`, `output/`, and `__pycache__` from being tracked |
| `output/` | Directory where CSV files are saved (gitignored, created by script) |

No test files — this is a simple user-facing script with no internal modules worth unit testing. Verification is done by running the script against a real Luma event.

---

### Task 1: Project scaffolding

**Files:**
- Create: `.gitignore`

- [ ] **Step 1: Initialize git repo and create .gitignore**

```bash
cd "/Users/buddygu/Documents/luma page email scrapping"
git init
```

Create `.gitignore`:

```
config.ini
output/
__pycache__/
*.pyc
.DS_Store
```

- [ ] **Step 2: Install requests library**

```bash
pip3 install requests
```

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: initialize project with gitignore"
```

---

### Task 2: Config management (setup mode)

**Files:**
- Create: `export_guests.py`

This task creates the script skeleton with the `--setup` flag that saves the API key to `config.ini`.

- [ ] **Step 1: Write the setup mode and config reading code**

Create `export_guests.py`:

```python
#!/usr/bin/env python3
"""Export guest lists from Luma events to CSV files."""

import configparser
import csv
import os
import re
import sys
from datetime import datetime

import requests

BASE_URL = "https://public-api.luma.com"
CONFIG_FILE = "config.ini"
OUTPUT_DIR = "output"


def get_api_key():
    """Read API key from config file. Returns None if not found."""
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    return config.get("luma", "api_key", fallback=None)


def save_api_key(api_key):
    """Save API key to config file."""
    config = configparser.ConfigParser()
    config["luma"] = {"api_key": api_key}
    with open(CONFIG_FILE, "w") as f:
        config.write(f)
    print(f"API key saved to {CONFIG_FILE}")


def run_setup():
    """Interactive setup to save Luma API key."""
    print("=== Luma Guest Exporter Setup ===")
    print()
    print("To get your API key:")
    print("1. Go to https://lu.ma and log in")
    print("2. Select your calendar")
    print("3. Go to Settings > Developer")
    print("4. Copy the API key")
    print()
    api_key = input("Paste your Luma API key: ").strip()
    if not api_key:
        print("Error: API key cannot be empty.")
        sys.exit(1)
    save_api_key(api_key)
    print("Setup complete! You can now run the exporter.")
    print(f"Usage: python3 {sys.argv[0]}")


def main():
    if "--setup" in sys.argv:
        run_setup()
        return

    api_key = get_api_key()
    if not api_key:
        print("Error: API key not found.")
        print(f"Run: python3 {sys.argv[0]} --setup")
        sys.exit(1)

    export_guests(api_key)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Test setup mode**

```bash
cd "/Users/buddygu/Documents/luma page email scrapping"
python3 export_guests.py
```

Expected output: `Error: API key not found.` followed by the setup instructions.

- [ ] **Step 3: Commit**

```bash
git add export_guests.py
git commit -m "feat: add config management and setup mode"
```

---

### Task 3: API client — fetch event and guests

**Files:**
- Modify: `export_guests.py`

Add the API functions that call Luma's endpoints.

- [ ] **Step 1: Add API functions after the `save_api_key` function**

Insert these functions into `export_guests.py` between `save_api_key` and `run_setup`:

```python
def make_headers(api_key):
    return {"x-luma-api-key": api_key, "Content-Type": "application/json"}


def extract_event_slug(url):
    """Extract event slug from a Luma URL like https://lu.ma/abc123."""
    url = url.strip().rstrip("/")
    match = re.match(r"https?://(?:www\.)?lu\.ma/([a-zA-Z0-9_-]+)", url)
    if not match:
        return None
    return match.group(1)


def fetch_event(api_key, event_slug):
    """Fetch event details by slug. Returns event JSON or None."""
    headers = make_headers(api_key)
    resp = requests.get(
        f"{BASE_URL}/event/get",
        headers=headers,
        params={"event_api_id": event_slug},
        timeout=30,
    )
    if resp.status_code == 401:
        print("Error: Invalid API key. Run --setup to update it.")
        sys.exit(1)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def fetch_guests(api_key, event_api_id):
    """Fetch all guests for an event, handling pagination. Returns list of guest dicts."""
    headers = make_headers(api_key)
    guests = []
    cursor = None

    while True:
        params = {"event_api_id": event_api_id}
        if cursor:
            params["cursor"] = cursor

        resp = requests.get(
            f"{BASE_URL}/event/get-guests",
            headers=headers,
            params=params,
            timeout=30,
        )
        if resp.status_code == 401:
            print("Error: Invalid API key. Run --setup to update it.")
            sys.exit(1)
        resp.raise_for_status()

        data = resp.json()
        entries = data.get("entries", [])
        guests.extend(entries)

        if not entries:
            break
        cursor = data.get("next_cursor")
        if not cursor:
            break

    return guests
```

- [ ] **Step 2: Verify script still runs without errors**

```bash
python3 -c "import export_guests; print('Import OK')"
```

Expected: `Import OK`

- [ ] **Step 3: Commit**

```bash
git add export_guests.py
git commit -m "feat: add Luma API client functions"
```

---

### Task 4: CSV export and main flow

**Files:**
- Modify: `export_guests.py`

Add the CSV writer and the `export_guests` function that ties everything together.

- [ ] **Step 1: Add CSV export function**

Insert before the `main()` function:

```python
def sanitize_filename(name):
    """Remove characters that are unsafe in filenames."""
    return re.sub(r'[<>:"/\\|?*]', '', name).strip()


def write_csv(event_name, guests):
    """Write guest list to a CSV file in the output directory."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    safe_name = sanitize_filename(event_name)
    filename = f"{safe_name}_{today}.csv"
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Email", "Status", "Ticket Type", "Registration Date"])
        for guest in guests:
            name = guest.get("name", guest.get("guest_name", ""))
            email = guest.get("email", guest.get("guest_email", ""))
            status = guest.get("status", "")
            ticket_type = guest.get("ticket_type", {}).get("name", "") if isinstance(guest.get("ticket_type"), dict) else ""
            reg_date = guest.get("created_at", "")
            if reg_date:
                reg_date = reg_date[:10]
            writer.writerow([name, email, status, ticket_type, reg_date])

    return filepath


def export_guests(api_key):
    """Main export flow: get URL from user, fetch data, save CSV."""
    print("=== Luma Guest Exporter ===")
    print()
    url = input("Paste your Luma event URL (e.g. https://lu.ma/abc123): ").strip()

    slug = extract_event_slug(url)
    if not slug:
        print(f'Error: "{url}" is not a valid Luma event URL.')
        print("Expected format: https://lu.ma/your-event-slug")
        sys.exit(1)

    print(f"Looking up event: {slug}...")
    event = fetch_event(api_key, slug)
    if not event:
        print(f'Error: Event not found for "{slug}". Check the URL and try again.')
        sys.exit(1)

    event_name = event.get("name", slug)
    event_api_id = event.get("api_id", event.get("event_api_id", slug))
    print(f"Event found: {event_name}")
    print("Fetching guest list...")

    guests = fetch_guests(api_key, event_api_id)
    if not guests:
        print("No guests found for this event.")
        sys.exit(0)

    filepath = write_csv(event_name, guests)
    print()
    print(f"Exported {len(guests)} guests to: {filepath}")
```

- [ ] **Step 2: Test the full flow (without API key)**

```bash
python3 export_guests.py
```

Expected: `Error: API key not found.` with setup instructions.

```bash
python3 export_guests.py --setup
```

Expected: Interactive prompt asking for API key.

- [ ] **Step 3: Commit**

```bash
git add export_guests.py
git commit -m "feat: add CSV export and main interactive flow"
```

---

### Task 5: End-to-end verification with a real event

**Files:** None (verification only)

- [ ] **Step 1: Run setup with your real API key**

```bash
cd "/Users/buddygu/Documents/luma page email scrapping"
python3 export_guests.py --setup
```

Paste your actual Luma API key when prompted.

- [ ] **Step 2: Export guests from a real event**

```bash
python3 export_guests.py
```

Paste a real Luma event URL. Expected: CSV file created in `output/` with correct guest data.

- [ ] **Step 3: Open the CSV file**

Open the CSV file in Numbers or Excel and verify:
- Column headers: Name, Email, Status, Ticket Type, Registration Date
- Guest data is correct and matches what you see in Luma's dashboard
- No encoding issues with special characters in names

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore: initial working version"
```
