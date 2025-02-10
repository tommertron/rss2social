import httpx
from atproto import Client, models

def post_to_bluesky(username, password, message, link, summary, image_url=None):
    """
    Posts a message to Bluesky with an embedded link preview ("link card"), including an image if available.

    :param username: The Bluesky username (handle).
    :param password: The Bluesky password.
    :param message: The text message.
    :param link: The URL to embed.
    :param summary: The first 40 characters of the RSS summary.
    :param image_url: The featured image URL (if available).
    """
    try:
        client = Client()
        client.login(username, password)

        # Upload the image (if available)
        uploaded_blob = None
        if image_url:
            try:
                img_data = httpx.get(image_url, timeout=10).content  # Download image
                uploaded_blob = client.upload_blob(img_data).blob  # Upload to Bluesky
            except Exception as e:
                print(f"⚠️ Warning: Failed to upload image {image_url}. Proceeding without it. Error: {e}")

        # Create "link card" embed with optional image
        embed_external = models.AppBskyEmbedExternal.Main(
            external=models.AppBskyEmbedExternal.External(
                title=message[:100],  # Truncate title to avoid issues
                description=summary[:40],  # Limit description to 40 characters
                uri=link,
                thumb=uploaded_blob if uploaded_blob else None  # Only attach if upload succeeded
            )
        )

        # Send the post with an embedded link preview
        client.send_post(text=message, embed=embed_external)

        print(f"✅ Successfully posted to Bluesky ({username}) with link card & image")

    except Exception as e:
        print(f"❌ Error posting to Bluesky ({username}): {e}")