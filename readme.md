# RSS to Social Media Poster

This script reads an RSS feed and posts the latest entries to Mastodon, Bluesky, and optionally other platforms via a webhook. It also tracks previously posted URLs to prevent duplicate posts.

## Installation

### Prerequisites
Ensure you have Python 3 installed on your system.

### Install Dependencies
Run the following command to install the required Python modules:

```sh
pip install feedparser requests mastodon.py atproto
```

Alternatively, if you are using Python 3:

```sh
pip3 install feedparser requests mastodon.py atproto
```

## Configuration
Create a `config.json` file in the same directory as the script with the following structure:

```json
{
    "rss_feed": "https://example.com/rss.xml",
    "mastodon": [
        {
            "api_base_url": "https://mastodon.instance1",
            "access_token": "your_access_token_1"
        },
        {
            "api_base_url": "https://mastodon.instance2",
            "access_token": "your_access_token_2"
        }
    ],
    "bluesky": {
        "username": "your-bluesky-username",
        "password": "your-bluesky-password"
    },
    "webhook": "https://example.com/webhook-endpoint"
}
```

## Handling Previously Posted URLs
The script maintains a list of previously posted URLs in `posted_urls.json`. This prevents reposting the same content multiple times.

### How It Works:
- **When the script runs**, it checks `posted_urls.json` for previously posted links.
- **If an entry has already been posted**, it is skipped.
- **If an entry is new**, it is posted and added to `posted_urls.json`.

If `posted_urls.json` does not exist, the script will create it automatically.

### Resetting `posted_urls.json`
If you ever need to reset the list of posted URLs, simply delete `posted_urls.json` or replace its contents with:
```json
[]
```

## Usage

### **Running the Script**
Run the script with:

```sh
python3 rss2social.py
```

You'll probably want to run this as a CRON job.

## Features
- Fetches the latest entries from the specified RSS feed.
- Posts to multiple Mastodon accounts.
- Posts to Bluesky.
- Supports additional platforms via webhooks.
- Tracks previously posted URLs to prevent reposting.

## Troubleshooting
- **ModuleNotFoundError**: Ensure the virtual environment is activated before running the script.
- **UnauthorizedError on Bluesky**: Check your Bluesky login credentials in `config.json`.
- **JSON Errors**: If `posted_urls.json` is corrupt, manually reset it by replacing its contents with `[]`.

## License
This project is licensed under the MIT License.

