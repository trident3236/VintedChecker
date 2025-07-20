from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError
import time
import json
import os
import requests
from datetime import datetime, timedelta
import re

# --- Configuration & File Paths ---
CONFIG_FILE = "config.json"
SEEN_ITEMS_FILE = "seen_items.txt"


# --- Helper Functions ---
def load_config():
    """Loads the config.json file."""
    if not os.path.exists(CONFIG_FILE):
        print(f"❌ Error: {CONFIG_FILE} not found. Please create it.")
        return None
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"❌ Error: Could not decode {CONFIG_FILE}. Check for syntax errors.")
        return None


def load_seen_items():
    """Loads the set of seen item links from a file."""
    if not os.path.exists(SEEN_ITEMS_FILE):
        # If the file doesn't exist, create an empty one.
        # This is important for the GitHub Actions workflow to have a file to commit.
        open(SEEN_ITEMS_FILE, 'w').close()
        return set()
    with open(SEEN_ITEMS_FILE, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f)


def save_seen_items(item_links):
    """Saves the set of seen item links to a file."""
    with open(SEEN_ITEMS_FILE, 'w', encoding='utf-8') as f:
        for link in sorted(list(item_links)):
            f.write(link + '\n')


def send_discord_notification(webhook_url: str, item: dict, brand_name: str):
    """Sends a formatted embed notification to a Discord webhook."""
    embed = {
        "title": item['title'],
        "url": item['link'],
        "color": 990066,
        "fields": [
            {"name": "Price", "value": item['price'], "inline": True},
            {"name": "Brand", "value": brand_name, "inline": True},
            {"name": "Size", "value": item['size'], "inline": True}
        ],
        "image": {"url": item['image_url']},
        "footer": {"text": f"Vinted Alerter | {time.strftime('%Y-%m-%d %H:%M:%S')}"}
    }
    payload = {"embeds": [embed]}
    try:
        # Use the standard requests library to send the webhook
        requests.post(webhook_url, json=payload, timeout=10)
        print("   ✔️ Notification sent to Discord.")
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Failed to send Discord notification: {e}")
    # A short sleep to be respectful to Discord's API
    time.sleep(2)


# --- Main Scanning Logic ---
def scan_vinted(config, seen_items):
    newly_found_links = set()
    webhook_url = config.get("discord_webhook_url")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        for search in config.get('searches', []):
            brand = search.get('brand')
            if not brand: continue

            print(f"\n🔎 Scanning for brand: '{brand}'...")
            search_url = f"https://www.vinted.co.uk/catalog?search_text={brand}&order=newest_first"
            try:
                page.goto(search_url, wait_until='domcontentloaded', timeout=45000)
                page.wait_for_selector('div.feed-grid',
