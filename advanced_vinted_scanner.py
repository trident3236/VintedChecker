from playwright.sync_api import sync_playwright
import time
import json
import os
import requests

# --- File to remember seen items ---
SEEN_ITEMS_FILE = "seen_items.txt"

# --- Helper Functions ---
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

def send_ntfy_notification(topic_url: str, item_title: str, item_link: str):
    """Sends a simple notification to an ntfy.sh topic."""
    try:
        requests.post(
            topic_url,
            data=f"New Vinted item found!".encode(encoding='utf-8'),
            headers={
                "Title": item_title,
                "Click": item_link,
                "Tags": "tshirt,vinted"
            },
            timeout=10
        )
        print("   ✔️ Notification sent to ntfy.")
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Failed to send ntfy notification: {e}")

# --- Main Simplified Scraper ---
def run_simple_scan():
    # --- ⚙️ PASTE YOUR NTFY TOPIC URL HERE ---
    ntfy_url = "https://ntfy.sh/nhag-vinted-alerts-2025"
    
    # A simple, broad search that is likely to have results
    vinted_search_url = "https://www.vinted.co.uk/catalog?order=newest_first"
    
    print("--- Starting Simplified Vinted Scanner ---")
    seen_items = load_seen_items()
    print(f"Loaded {len(seen_items)} previously seen items.")
    
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        try:
            print(f"Navigating to {vinted_search_url}...")
            page.goto(vinted_search_url, timeout=45000)
            page.wait_for_selector('div.feed-grid', timeout=20000)
            print("   - Page loaded and item grid found.")

            items = page.locator('div.feed-grid div.feed-grid__item').all()
            print(f"   - Found {len(items)} item cards. Now looking for the first new item...")

            for item in items:
                link_locator = item.locator('a.new-item-box__overlay').first
                if link_locator.count() == 0: continue
                
                item_link = "https://www.vinted.co.uk" + link_locator.get_attribute('href')
                if item_link in seen_items: continue
                
                title_locator = item.locator('[data-testid$="--description-title"]')
                if title_locator.count() == 0: continue

                title = title_locator.first.text_content().strip()
                
                print(f"   - ✅ FOUND FIRST NEW ITEM: {title}")
                
                # Send the notification
                send_ntfy_notification(ntfy_url, title, item_link)
                
                # Add it to our list and save
                seen_items.add(item_link)
                save_seen_items(seen_items)
                print("   - Item saved. Stopping scan.")
                
                # Stop after finding the first one
                break
        
        except Exception as e:
            print(f"   ❌ An error occurred: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    run_simple_scan()
    print("--- Scan complete. ---")
