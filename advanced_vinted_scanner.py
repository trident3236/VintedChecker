from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
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
    if not os.path.exists(SEEN_ITEMS_FILE):
        open(SEEN_ITEMS_FILE, 'w').close()
        return set()
    with open(SEEN_ITEMS_FILE, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f)

def save_seen_items(item_links):
    with open(SEEN_ITEMS_FILE, 'w', encoding='utf-8') as f:
        for link in sorted(list(item_links)):
            f.write(link + '\n')

# --- This is the correct, original version of the function ---
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
        requests.post(webhook_url, json=payload, timeout=10)
        print("   ✔️ Notification sent to Discord.")
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Failed to send Discord notification: {e}")
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
                page.wait_for_selector('div.feed-grid', timeout=20000)
                print(f"   - Page loaded and item grid found.")

                items = page.locator('div.feed-grid div.feed-grid__item').all()
                print(f"   - Found {len(items)} item cards. Now checking them...")

                for item in items:
                    link_locator = item.locator('a.new-item-box__overlay').first
                    if link_locator.count() == 0: continue
                    
                    item_link = "https://www.vinted.co.uk" + link_locator.get_attribute('href')
                    if not item_link or item_link in seen_items: continue
                    
                    title_locator = item.locator('[data-testid$="--description-title"]')
                    if title_locator.count() == 0: continue

                    title = title_locator.first.text_content().lower().strip()
                    
                    if any(keyword.lower() in title for keyword in search.get('exclude_keywords', [])): continue
                    if search.get('include_keywords') and not any(keyword.lower() in title for keyword in search.get('include_keywords', [])): continue

                    size_locator = item.locator('[data-testid$="--description-subtitle"]')
                    size_text = size_locator.first.text_content().lower().strip() if size_locator.count() > 0 else ""
                    if search.get('sizes') and not any(size.lower() in size_text for size in search.get('sizes', [])): continue
                    
                    print(f"   - MATCH: {title}")
                    newly_found_links.add(item_link)
                    
                    price_locator = item.locator('span.web_ui__Text__text.web_ui__Text__subtitle')
                    image_locator = item.locator('img.web_ui__Image__content')

                    item_data = {
                        'title': title_locator.first.text_content().strip(),
                        'price': price_locator.first.text_content().strip() if price_locator.count() > 0 else "N/A",
                        'size': size_locator.first.text_content().strip() if size_locator.count() > 0 else "N/A",
                        'link': item_link,
                        'image_url': image_locator.first.get_attribute('src') if image_locator.count() > 0 else "",
                    }
                    send_discord_notification(webhook_url, item_data, brand)
            
            except PlaywrightTimeoutError:
                print(f"   ❌ Timed out waiting for page elements for '{brand}'. Vinted may be slow or the layout has changed.")
            except Exception as e:
                print(f"   ❌ An unexpected error occurred for {brand}: {e}")
        
        browser.close()
    return newly_found_links

# --- Main Execution Block ---
if __name__ == "__main__":
    print("--- Starting Vinted Scanner (Playwright Version) ---")
    config = load_config()
    if config:
        if not config.get("discord_webhook_url") or "PASTE_YOUR_DISCORD_WEBHOOK_URL_HERE" in config.get("discord_webhook_url"):
            print("❌ Error: Discord webhook URL is missing or is still a placeholder in config.json.")
        else:
            seen_items = load_seen_items()
            print(f"Loaded {len(seen_items)} previously seen items.")
            new_links = scan_vinted(config, seen_items)
            if new_links:
                print(f"\nFound {len(new_links)} new item(s).")
                updated_seen_items = seen_items.union(new_links)
                save_seen_items(updated_seen_items)
                print(f"💾 Saved {len(updated_seen_items)} total items for next time.")
            else:
                print("\nNo new items found that match your criteria.")
    print("--- Scan complete. ---")
