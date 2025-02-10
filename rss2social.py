import argparse
import feedparser
import json
import os
import re
import post_to_bluesky
import post_to_mastodon
from html import unescape
from datetime import datetime, timezone

CONFIG_FILE = "config.json"
POSTED_URLS_FILE = "posted_urls.json"


def load_config():
    """Load configuration from config.json."""
    with open(CONFIG_FILE, "r") as file:
        return json.load(file)


def load_posted_urls():
    """Load previously posted URLs from posted_urls.json."""
    if not os.path.exists(POSTED_URLS_FILE):
        return {}

    try:
        with open(POSTED_URLS_FILE, "r") as file:
            return json.load(file)
    except json.JSONDecodeError:
        print("⚠️ Warning: posted_urls.json is corrupted. Resetting it.")
        return {}


def save_posted_urls(posted_urls):
    """Save posted URLs to posted_urls.json."""
    with open(POSTED_URLS_FILE, "w") as file:
        json.dump(posted_urls, file, indent=4)


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


def strip_html(html):
    """Remove all HTML tags and keep only text."""
    text = re.sub(r"<h\d>.*?</h\d>", "", html, flags=re.DOTALL)  # Remove headers
    text = re.sub(r"<[^>]+>", "", text)  # Remove all other HTML tags
    text = unescape(text).strip()  # Convert HTML entities (e.g., &amp; → &)
    return text


def clean_summary(summary, length=50):
    """Clean summary text and truncate to `length` characters with ellipsis."""
    clean_text = strip_html(summary)  # Remove HTML
    return (clean_text[:length] + "...") if len(clean_text) > length else clean_text


def update_posted_urls(posted_urls, url, account_type, account_name):
    """Update the posted_urls JSON with the newly posted URL and account."""
    now = datetime.now(timezone.utc).isoformat()
    
    if url not in posted_urls:
        posted_urls[url] = {"accounts_posted": {}}
    
    if "accounts_posted" not in posted_urls[url]:
        posted_urls[url]["accounts_posted"] = {}

    if account_type not in posted_urls[url]["accounts_posted"]:
        posted_urls[url]["accounts_posted"][account_type] = {}

    posted_urls[url]["accounts_posted"][account_type][account_name] = now
    save_posted_urls(posted_urls)


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

        # Check if this post has already been processed for each account
        already_posted = posted_urls.get(link, {}).get("accounts_posted", {})

        print(f"📢 Processing: {title}")

        # Post to all configured Bluesky accounts
        for account in bluesky_accounts:
            username = account["username"]
            if "bluesky" in already_posted and username in already_posted["bluesky"]:
                print(f"⏭ Skipping {title} for Bluesky ({username}), already posted.")
                continue  # Skip posting to this account

            try:
                post_to_bluesky.post_to_bluesky(username, account["password"], title, link, summary, image_url)
                update_posted_urls(posted_urls, link, "bluesky", username)
                print(f"✅ Successfully posted to Bluesky ({username}) with link card & image")
            except Exception as e:
                print(f"❌ Error posting to Bluesky ({username}): {e}")

        # Post to all configured Mastodon accounts (if not disabled via CLI)
        if not args.no_mastodon:
            for account in mastodon_accounts:
                mastodon_url = account["api_base_url"]
                if "mastodon" in already_posted and mastodon_url in already_posted["mastodon"]:
                    print(f"⏭ Skipping {title} for Mastodon ({mastodon_url}), already posted.")
                    continue  # Skip posting to this account

                try:
                    post_to_mastodon.post_to_mastodon(mastodon_url, account["access_token"], f"{title}\n{link}")
                    update_posted_urls(posted_urls, link, "mastodon", mastodon_url)
                    print(f"✅ Successfully posted to Mastodon ({mastodon_url})")
                except Exception as e:
                    print(f"❌ Error posting to Mastodon ({mastodon_url}): {e}")

    print("✅ Done processing all RSS items.")


if __name__ == "__main__":
    main()