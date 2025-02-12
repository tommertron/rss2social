import argparse
import feedparser
import json
import os
import re
import post_to_bluesky
import post_to_mastodon
from html import unescape
from datetime import datetime

CONFIG_FILE = "config.json"
POSTED_URLS_FILE = "posted_urls.json"
LOG_FILE = "rss2social.log"
MAX_LOG_LINES = 1000


def log_message(message):
    """Logs a message with a timestamp to both console and log file."""
    timestamp = datetime.utcnow().strftime("[%Y-%m-%d %H:%M:%S UTC]")
    log_entry = f"{timestamp} {message}"

    # Print to console
    print(log_entry)

    # Ensure log file exists
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            f.write("")

    # Append to log file and trim if necessary
    with open(LOG_FILE, "r") as f:
        log_lines = f.readlines()

    log_lines.append(log_entry + "\n")

    # Trim log if too long
    if len(log_lines) > MAX_LOG_LINES:
        log_lines = log_lines[-MAX_LOG_LINES:]

    with open(LOG_FILE, "w") as f:
        f.writelines(log_lines)


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
        log_message("⚠️ Warning: posted_urls.json is corrupted. Resetting it.")
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
    if "media_content" in entry:
        return entry["media_content"][0]["url"]
    if "links" in entry:
        for link in entry["links"]:
            if link["rel"] == "enclosure" and "image" in link["type"]:
                return link["href"]
    if "summary" in entry and "<img" in entry["summary"]:
        match = re.search(r'<img.*?src=["\'](.*?)["\']', entry["summary"])
        if match:
            return match.group(1)
    return None


def strip_html(html):
    """Remove all HTML tags and keep only text."""
    text = re.sub(r"<h\d>.*?</h\d>", "", html, flags=re.DOTALL)  # Remove headers
    text = re.sub(r"<[^>]+>", "", text)  # Remove all other HTML tags
    text = unescape(text).strip()  # Convert HTML entities (e.g., &amp; → &)
    return text


def clean_summary(summary, length=50):
    """Clean summary text and truncate to `length` characters with ellipsis."""
    clean_text = strip_html(summary)
    return (clean_text[:length] + "...") if len(clean_text) > length else clean_text


def main():
    """Fetch RSS and post each item to configured platforms."""

    # 🔹 Parse CLI Arguments
    parser = argparse.ArgumentParser(description="Post RSS feed entries to Bluesky and Mastodon.")
    parser.add_argument("--limit", type=int, default=10, help="Number of RSS feed entries to process (default: 10).")
    parser.add_argument("--no-mastodon", action="store_true", help="Disable posting to Mastodon (for debugging).")
    args = parser.parse_args()

    log_message("🚀 Starting rss2social script...")

    config = load_config()
    posted_urls = load_posted_urls()

    feed_url = config["rss_feed"]
    bluesky_accounts = config.get("bluesky", [])
    mastodon_accounts = config.get("mastodon", [])

    log_message(f"🔄 Fetching RSS feed: {feed_url} (Limit: {args.limit})")
    entries = fetch_rss(feed_url, args.limit)

    for entry in entries:
        title = entry.title
        link = entry.link
        summary = clean_summary(entry.summary) if hasattr(entry, "summary") else "New post from RSS feed"
        image_url = extract_featured_image(entry)

        if link in posted_urls:
            log_message(f"⏭ Skipping {title}, already posted to all accounts.")
            continue  # Skip this entry

        log_message(f"📢 Processing: {title}")

        # Store accounts that successfully posted
        posted_accounts = {}

        # Post to all configured Bluesky accounts
        for account in bluesky_accounts:
            try:
                post_to_bluesky.post_to_bluesky(account["username"], account["password"], title, link, summary, image_url)
                log_message(f"✅ Successfully posted to Bluesky ({account['username']})")
                posted_accounts.setdefault("bluesky", {})[account["username"]] = datetime.utcnow().isoformat() + "Z"
            except Exception as e:
                log_message(f"❌ Error posting to Bluesky ({account['username']}): {e}")

        # Post to all configured Mastodon accounts (if not disabled via CLI)
        if not args.no_mastodon:
            for account in mastodon_accounts:
                try:
                    post_to_mastodon.post_to_mastodon(account["api_base_url"], account["access_token"], f"{title}\n{link}")
                    log_message(f"✅ Successfully posted to Mastodon ({account['api_base_url']})")
                    posted_accounts.setdefault("mastodon", {})[account["api_base_url"]] = datetime.utcnow().isoformat() + "Z"
                except Exception as e:
                    log_message(f"❌ Error posting to Mastodon ({account['api_base_url']}): {e}")

        # ✅ Add to posted URLs only if at least one post succeeded
        if posted_accounts:
            posted_urls[link] = {"accounts_posted": posted_accounts}
            save_posted_urls(posted_urls)

    log_message("✅ Done processing all RSS items.")
    log_message("🎉 rss2social script completed successfully.")


if __name__ == "__main__":
    main()