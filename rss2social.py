import argparse
import feedparser
import json
import os
import re
import post_to_bluesky
import post_to_mastodon
from html import unescape

CONFIG_FILE = "config.json"
POSTED_URLS_FILE = "posted_urls.json"

def load_config():
    """Load configuration from config.json."""
    with open(CONFIG_FILE, "r") as file:
        return json.load(file)

def load_posted_urls():
    """Load previously posted URLs from posted_urls.json."""
    if not os.path.exists(POSTED_URLS_FILE):
        return set()

    try:
        with open(POSTED_URLS_FILE, "r") as file:
            return set(json.load(file))
    except json.JSONDecodeError:
        print("⚠️ Warning: posted_urls.json is corrupted. Resetting it.")
        return set()

def save_posted_urls(posted_urls):
    """Save posted URLs to posted_urls.json."""
    with open(POSTED_URLS_FILE, "w") as file:
        json.dump(list(posted_urls), file, indent=4)

def fetch_rss(feed_url, limit):
    """Fetch latest RSS feed entries, limited by the `limit` argument."""
    feed = feedparser.parse(feed_url)
    return feed.entries[:limit]  # Limit number of entries if specified

def extract_featured_image(entry):
    """Attempt to extract the featured image from the RSS entry."""
    if "media_content" in entry:  # Some feeds use media:content
        return entry["media_content"][0]["url"]
    if "links" in entry:
        for link in entry["links"]:
            if link["rel"] == "enclosure" and "image" in link["type"]:
                return link["href"]
    if "summary" in entry and "<img" in entry["summary"]:  # Extract from summary
        match = re.search(r'<img.*?src=["\'](.*?)["\']', entry["summary"])
        if match:
            return match.group(1)
    return None  # No image found

## Clean RSS HTML Description For Posting

import re
from html import unescape

def strip_html(html):
    """Remove headers completely, strip all HTML tags, normalize spaces, and decode entities."""
    html = re.sub(r"<h\d[^>]*>.*?</h\d>", "", html, flags=re.DOTALL)  # Remove entire header blocks
    html = re.sub(r"<[^>]+>", "", html)  # Remove all remaining HTML tags
    html = re.sub(r"\s+", " ", html).strip()  # Normalize whitespace
    return unescape(html)  # Decode HTML entities

def clean_summary(summary, length=40):
    """Clean summary text, remove headers completely, and truncate."""
    clean_text = strip_html(summary)
    clean_text = clean_text.replace("#", "").strip()  # Remove standalone "#" symbols
    return (clean_text[:length] + "...") if len(clean_text) > length else clean_text

def main():
    """Fetch RSS and post each item to configured platforms."""

    # 🔹 Parse CLI Arguments
    parser = argparse.ArgumentParser(description="Post RSS feed entries to Bluesky and Mastodon.")
    parser.add_argument("--limit", type=int, default=5, help="Number of RSS feed entries to process (default: 5).")
    parser.add_argument("--no-mastodon", action="store_true", help="Disable posting to Mastodon (for debugging).")
    args = parser.parse_args()

    config = load_config()
    posted_urls = load_posted_urls()

    feed_url = config["rss_feed"]
    bluesky_accounts = config.get("bluesky", [])  # List of Bluesky accounts
    mastodon_accounts = config.get("mastodon", [])  # List of Mastodon accounts

    entries = fetch_rss(feed_url, args.limit)

    for entry in entries:
        title = entry.title
        link = entry.link
        summary = clean_summary(entry.summary) if hasattr(entry, "summary") else "New post from RSS feed"
        image_url = extract_featured_image(entry)

        if link in posted_urls:
            print(f"⏭ Skipping already posted: {link}")
            continue  # Skip this entry

        print(f"📢 Posting: {title}")

        # Post to all configured Bluesky accounts
        for account in bluesky_accounts:
            try:
                post_to_bluesky.post_to_bluesky(account["username"], account["password"], title, link, summary, image_url)
            except Exception as e:
                print(f"❌ Error posting to Bluesky ({account['username']}): {e}")

        # Post to all configured Mastodon accounts (if not disabled via CLI)
        if not args.no_mastodon:
            for account in mastodon_accounts:
                try:
                    post_to_mastodon.post_to_mastodon(account["api_base_url"], account["access_token"], f"{title}\n{link}")
                except Exception as e:
                    print(f"❌ Error posting to Mastodon ({account['api_base_url']}): {e}")

        # ✅ Add to posted URLs only if at least one post succeeded
        posted_urls.add(link)
        save_posted_urls(posted_urls)

if __name__ == "__main__":
    main()