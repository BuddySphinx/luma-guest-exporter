#!/usr/bin/env python3
"""Export guest lists from Luma events to CSV files."""

import configparser
import csv
import os
import re
import sys
import time
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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


def make_headers(api_key):
    return {"x-luma-api-key": api_key, "Content-Type": "application/json"}


def parse_event_url(url):
    """Parse a Luma URL and return either an api_id or a slug.

    Returns a dict: {"type": "api_id", "value": "evt-xxx"} or {"type": "slug", "value": "abc123"}
    Returns None if the URL doesn't match any known Luma URL pattern.

    Supported URL formats:
      - Public event page:    https://luma.com/qc4qky2n
      - Management overview:  https://luma.com/event/manage/evt-xxx/overview
      - Guest list page:      https://luma.com/event/manage/evt-xxx/guests
    """
    url = url.strip().rstrip("/")

    # Management or guest URL: https://luma.com/event/manage/evt-xxx/overview or /guests
    match = re.match(
        r"https?://(?:www\.)?(?:lu\.ma|luma\.com)/event/manage/(evt-[a-zA-Z0-9_-]+)(?:/|$)",
        url,
    )
    if match:
        return {"type": "api_id", "value": match.group(1)}

    # Public event page: https://luma.com/abc123 or https://lu.ma/abc123
    match = re.match(
        r"https?://(?:www\.)?(?:lu\.ma|luma\.com)/([a-zA-Z0-9_-]+)", url
    )
    if match:
        return {"type": "slug", "value": match.group(1)}

    return None


def lookup_entity(api_key, slug):
    """Resolve a URL slug to an entity via the Luma API. Returns event dict or None."""
    headers = make_headers(api_key)
    resp = requests.get(
        f"{BASE_URL}/v1/entity/lookup",
        headers=headers,
        params={"slug": slug},
        timeout=30,
    )
    if resp.status_code == 401:
        print("Error: Invalid API key. Run --setup to update it.")
        sys.exit(1)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    data = resp.json()
    entity = data.get("entity", {})
    if entity.get("type") == "event":
        return entity.get("event")
    return None


def fetch_guests(api_key, event_api_id):
    """Fetch all guests for an event, handling pagination. Returns list of guest dicts."""
    headers = make_headers(api_key)
    guests = []
    cursor = None
    page = 0

    retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry_strategy))

    while True:
        params = {"event_api_id": event_api_id}
        if cursor:
            params["cursor"] = cursor

        try:
            resp = session.get(
                f"{BASE_URL}/v1/event/get-guests",
                headers=headers,
                params=params,
                timeout=30,
            )
        except requests.exceptions.SSLError:
            if guests:
                print(f"\nWarning: SSL connection lost after fetching {len(guests)} guests.")
                print("This is caused by an outdated SSL library on your Mac.")
                print("Partial results have been saved.")
                break
            print("Error: SSL connection failed. Try running the script again.")
            sys.exit(1)

        if resp.status_code == 401:
            print("Error: Invalid API key. Run --setup to update it.")
            sys.exit(1)
        if resp.status_code == 403:
            print("Error: You don't have access to this event's guest list.")
            print("Make sure your API key belongs to the calendar that owns this event.")
            sys.exit(1)
        if resp.status_code == 429:
            print(f"\n  Rate limited by Luma API. Waiting 65 seconds... (fetched {len(guests)} guests so far)")
            time.sleep(65)
            continue

        resp.raise_for_status()

        data = resp.json()
        entries = data.get("entries", [])
        guests.extend(entries)
        page += 1
        print(f"  Page {page}: {len(entries)} guests (total: {len(guests)})")

        if not entries:
            break
        cursor = data.get("next_cursor")
        if not cursor:
            break

        # Stay under Luma's 300 requests/minute rate limit
        time.sleep(0.25)

    session.close()
    return guests


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
        writer.writerow(["Name", "Email", "First Name", "Last Name", "Status", "Ticket Type", "Registration Date"])
        for guest in guests:
            name = guest.get("name", "")
            email = guest.get("email", "")
            first_name = guest.get("user_first_name", "")
            last_name = guest.get("user_last_name", "")
            status = guest.get("approval_status", "")
            ticket = guest.get("event_ticket", {})
            ticket_type = ticket.get("name", "") if isinstance(ticket, dict) else ""
            reg_date = guest.get("registered_at", "")
            if reg_date:
                reg_date = reg_date[:10]
            writer.writerow([name, email, first_name, last_name, status, ticket_type, reg_date])

    return filepath


def export_guests(api_key):
    """Main export flow: get URL from user, fetch data, save CSV."""
    print("=== Luma Guest Exporter ===")
    print()
    print("Paste any of these URL types:")
    print("  - Event page:     https://luma.com/abc123")
    print("  - Manage page:    https://luma.com/event/manage/evt-xxx/overview")
    print("  - Guest list:     https://luma.com/event/manage/evt-xxx/guests")
    print()
    url = input("Paste your Luma event URL: ").strip()

    parsed = parse_event_url(url)
    if not parsed:
        print(f'Error: "{url}" is not a valid Luma event URL.')
        sys.exit(1)

    if parsed["type"] == "api_id":
        # Management/guest URL — we already have the event API ID
        event_api_id = parsed["value"]
        event_name = event_api_id
        print(f"Event ID detected: {event_api_id}")
    else:
        # Public event page — resolve slug to API ID via entity lookup
        slug = parsed["value"]
        print(f"Looking up event: {slug}...")
        event = lookup_entity(api_key, slug)
        if not event:
            print(f'Error: Event not found for "{slug}". Check the URL and try again.')
            sys.exit(1)
        event_api_id = event.get("api_id", slug)
        event_name = event.get("name", slug)

    print("Fetching guest list...")

    guests = fetch_guests(api_key, event_api_id)
    if not guests:
        print("No guests found for this event.")
        sys.exit(0)

    filepath = write_csv(event_name, guests)
    print()
    print(f"Exported {len(guests)} guests to: {filepath}")


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
