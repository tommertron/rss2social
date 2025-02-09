#!/Users/tommertron/coding/rss2social/myenv/bin/python

import json
import feedparser
import requests
from mastodon import Mastodon
from atproto import Client  # For Bluesky

# Load configuration from a JSON file
def load_config(config_path):
    with open(config_path, "r") as file:
        return json.load(file)

# Fetch latest RSS feed entries
def fetch_rss_entries(feed_url):
    feed = feedparser.parse(feed_url)
    return feed.entries[:5]  # Limit to latest 5 entries

# Post to Mastodon
def post_to_mastodon(config, message):
    for account in config["mastodon"]:
        try:
            mastodon = Mastodon(
                access_token=account["access_token"],
                api_base_url=account["api_base_url"]
            )
            mastodon.status_post(message)
            print(f"Posted to Mastodon ({account['api_base_url']})")
        except Exception as e:
            print(f"Error posting to {account['api_base_url']}: {e}")

# Post to Bluesky
def post_to_bluesky(config, message):
    if "bluesky" not in config or not config["bluesky"].get("username") or not config["bluesky"].get("password"):
        print("Bluesky not configured. Skipping...")
        return
    
    try:
        client = Client()
        client.login(config["bluesky"]["username"], config["bluesky"]["password"])
        client.send_post(message)
        print("Posted to Bluesky")
    except Exception as e:
        print(f"Error posting to Bluesky: {e}")

# Post to other platforms (expand as needed)
def post_to_other_platforms(config, message):
    if "webhook" not in config or not config["webhook"]:
        print("No webhook configured. Skipping...")
        return

    try:
        requests.post(config["webhook"], json={"text": message})
        print("Posted to webhook endpoint")
    except Exception as e:
        print(f"Error posting to webhook: {e}")

# Handle Posted URLs file 
import json
import os

POSTED_URLS_FILE = "posted_urls.json"

def load_posted_urls():
    """Load previously posted URLs, handling empty or missing files."""
    if not os.path.exists(POSTED_URLS_FILE):
        return []  # Return an empty list if the file doesn't exist
    
    try:
        with open(POSTED_URLS_FILE, "r") as file:
            data = file.read().strip()
            return json.loads(data) if data else []  # Return an empty list if file is blank
    except json.JSONDecodeError:
        print("Warning: posted_urls.json is corrupted. Resetting it.")
        return []

def save_posted_urls(urls):
    """Save posted URLs to file."""
    with open(POSTED_URLS_FILE, "w") as file:
        json.dump(urls, file, indent=4)
        
        
# Main function
def main():
    config = load_config("config.json")
    feed_entries = fetch_rss_entries(config["rss_feed"]) 

    posted_urls = load_posted_urls()  # Load previously posted URLs

    for entry in feed_entries:
        if entry.link in posted_urls:
            print(f"Skipping already posted: {entry.link}")
            continue  # Skip if already posted

        message = f"{entry.title} - {entry.link}"
        post_to_mastodon(config, message)
        post_to_bluesky(config, message)
        post_to_other_platforms(config, message)

        # Save the new post's URL
        posted_urls.append(entry.link)
        save_posted_urls(posted_urls)


if __name__ == "__main__":
    main()
