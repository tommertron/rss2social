from mastodon import Mastodon

def post_to_mastodon(instance_url, access_token, message):
    """
    Post a message to Mastodon.

    :param instance_url: The URL of the Mastodon instance (e.g., "https://mastodon.social").
    :param access_token: The user's access token.
    :param message: The message to post.
    """
    try:
        mastodon = Mastodon(
            access_token=access_token,
            api_base_url=instance_url
        )
        mastodon.status_post(message)
        print("✅ Successfully posted to Mastodon")
    except Exception as e:
        print(f"❌ Error posting to Mastodon: {e}")