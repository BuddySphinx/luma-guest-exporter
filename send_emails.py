#!/usr/bin/env python3
"""Send emails to guests exported from Luma events."""

import configparser
import csv
import glob
import os
import smtplib
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

CONFIG_FILE = "config.ini"
OUTPUT_DIR = "output"


def get_email_config():
    """Read email config from config file. Returns dict or None."""
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    if not config.has_section("email"):
        return None
    return {
        "address": config.get("email", "address", fallback=None),
        "password": config.get("email", "password", fallback=None),
    }


def save_email_config(address, password):
    """Save email config to config file."""
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    config["email"] = {"address": address, "password": password}
    with open(CONFIG_FILE, "w") as f:
        config.write(f)
    print(f"Email settings saved to {CONFIG_FILE}")


def run_setup_email():
    """Interactive setup to save Gmail credentials."""
    print("=== Email Setup ===")
    print()
    print("To get your Gmail App Password:")
    print("1. Go to https://myaccount.google.com/security")
    print("2. Make sure 2-Step Verification is ON")
    print("3. Go to https://myaccount.google.com/apppasswords")
    print("4. Create a new app password named 'Luma Exporter'")
    print("5. Copy the 16-character password")
    print()
    address = input("Your Gmail address (e.g. you@gmail.com): ").strip()
    if not address:
        print("Error: Email address cannot be empty.")
        sys.exit(1)
    password = input("Paste your 16-character App Password: ").strip()
    if not password:
        print("Error: Password cannot be empty.")
        sys.exit(1)

    # Test the credentials before saving
    print("Testing connection to Gmail...")
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(address, password)
        server.quit()
        print("Connection successful!")
    except smtplib.SMTPAuthenticationError:
        print("Error: Authentication failed. Check your email and app password.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: Could not connect to Gmail: {e}")
        sys.exit(1)

    save_email_config(address, password)
    print("Email setup complete!")


def list_csv_files():
    """List available CSV files in the output directory."""
    files = sorted(glob.glob(os.path.join(OUTPUT_DIR, "*.csv")))
    return files


def choose_csv():
    """Let the user pick a CSV file. Returns file path."""
    files = list_csv_files()
    if not files:
        print(f"No CSV files found in {OUTPUT_DIR}/")
        print("Run export_guests.py first to export guest lists.")
        sys.exit(1)

    print("Available guest lists:")
    for i, f in enumerate(files, 1):
        print(f"  {i}. {os.path.basename(f)}")
    print()

    while True:
        choice = input(f"Choose a file (1-{len(files)}): ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(files):
                return files[idx]
        except ValueError:
            pass
        print(f"Please enter a number between 1 and {len(files)}.")


def read_emails_from_csv(filepath):
    """Read email addresses and names from a CSV file."""
    guests = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = row.get("Email", "").strip()
            name = row.get("Name", "").strip()
            if email:
                guests.append({"name": name, "email": email})
    return guests


def send_emails(config, guests, subject, body):
    """Send emails to all guests via Gmail SMTP."""
    sender = config["address"]
    password = config["password"]
    total = len(guests)
    sent = 0
    failed = []

    print(f"\nSending {total} emails from {sender}...")
    print()

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()

    try:
        server.login(sender, password)

        for i, guest in enumerate(guests, 1):
            msg = MIMEMultipart()
            msg["From"] = sender
            msg["To"] = guest["email"]
            msg["Subject"] = subject

            # Add greeting with name if available
            if guest["name"]:
                personal_body = f"Hi {guest['name']},\n\n{body}"
            else:
                personal_body = body

            msg.attach(MIMEText(personal_body, "plain", "utf-8"))

            try:
                server.send_message(msg)
                sent += 1
                print(f"  [{i}/{total}] Sent to {guest['email']}")
            except Exception as e:
                failed.append(guest["email"])
                print(f"  [{i}/{total}] FAILED: {guest['email']} - {e}")

    finally:
        server.quit()

    return sent, failed


def main():
    if "--setup-email" in sys.argv:
        run_setup_email()
        return

    config = get_email_config()
    if not config or not config["address"] or not config["password"]:
        print("Error: Email not configured.")
        print(f"Run: python3 {sys.argv[0]} --setup-email")
        sys.exit(1)

    # Pick CSV file
    filepath = choose_csv()
    guests = read_emails_from_csv(filepath)
    if not guests:
        print("No email addresses found in the CSV file.")
        sys.exit(1)

    print(f"\nFound {len(guests)} recipients in {os.path.basename(filepath)}")

    # Get email content
    print()
    subject = input("Email subject: ").strip()
    if not subject:
        print("Error: Subject cannot be empty.")
        sys.exit(1)

    print("Email body (type your message, press Enter twice to finish):")
    body_lines = []
    while True:
        line = input()
        if line == "" and body_lines and body_lines[-1] == "":
            body_lines.pop()  # remove the trailing empty line
            break
        body_lines.append(line)
    body = "\n".join(body_lines)

    if not body:
        print("Error: Email body cannot be empty.")
        sys.exit(1)

    # Confirm
    print(f"\n{'='*50}")
    print(f"From:    {config['address']}")
    print(f"To:      {len(guests)} recipients")
    print(f"Subject: {subject}")
    print(f"Preview: Hi {guests[0]['name'] or 'Guest'},")
    print(f"         {body[:100]}{'...' if len(body) > 100 else ''}")
    print(f"{'='*50}")

    confirm = input("\nSend these emails? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Cancelled.")
        sys.exit(0)

    sent, failed = send_emails(config, guests, subject, body)

    print(f"\nDone! Sent: {sent}, Failed: {len(failed)}")
    if failed:
        print("Failed addresses:")
        for email in failed:
            print(f"  - {email}")


if __name__ == "__main__":
    main()
