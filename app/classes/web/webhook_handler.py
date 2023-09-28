import json
import logging
from datetime import datetime
import requests

from app.classes.shared.helpers import Helpers

logger = logging.getLogger(__name__)
helper = Helpers()

class WebhookHandler:
    @staticmethod
    def get_providers():
        return [
            "Discord",
            "Mattermost",
            "Signal",
            "Slack",
            "SMTP",
            "Splunk",
            "Teams",
            "Telegram",
            "Custom",
        ]

    @staticmethod
    def get_monitored_actions():
        return ["server_start", "server_stop", "server_crash", "server_backup"]

    @staticmethod
    def send_discord_webhook(server_name, title, url, message, color):
        """
        Sends a message to a Discord channel via a webhook.

        This method prepares a payload for the Discord webhook API using
        the message content, Crafty Controller version, and the current UTC datetime.
        It dispatches this payload to the specified webhook URL.

        Parameters:
        - server_name (str): Name of the server, used as 'author' in the Discord embed.
        - title (str): Title of the message in the Discord embed.
        - url (str): URL of the Discord webhook.
        - message (str): Main content of the message in the Discord embed.
        - color (int): Color code for the side stripe in the Discord message.

        Returns:
        str: "Dispatch successful!" if the message is sent successfully, otherwise an
        exception is raised.

        Raises:
        Exception: If there's an error in dispatching the webhook.

        Note:
        Webhook request times out after 10 seconds to prevent indefinite hanging.
        """
        # Grab Crafty System version
        version = helper.get_version_string()

        # Get the current UTC datetime
        current_datetime = datetime.utcnow()

        # Format the datetime to discord's required UTC string format
        # "YYYY-MM-DDTHH:MM:SS.MSSZ"
        formatted_datetime = (current_datetime.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
                            + 'Z')

        # Prepare webhook payload
        headers={"Content-type": "application/json"}
        payload = {
            "username": "Crafty Webhooks",
            "avatar_url": ("https://gitlab.com/crafty-controller/crafty-4/-"
                        + "/raw/master/app/frontend/static/assets/images/"
                        + "Crafty_4-0.png"),

            "embeds": [
                {
                "title": title,
                "description": message,
                "color": color,
                "author": {
                    "name": server_name
                },
                "footer": {
                    "text": f"Crafty Controller v.{version}"
                },
                "timestamp": formatted_datetime
                }
            ],
        }

        # Dispatch webhook
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            return "Dispatch successful"
        except requests.RequestException as error:
            logger.error(error)
            raise RuntimeError(f"Failed to send notification: {error}") from error
