from datetime import datetime
from app.classes.web.webhooks.base_webhook import WebhookProvider


class DiscordWebhook(WebhookProvider):
    def _construct_discord_payload(self, server_name, title, message, color):
        """
        Constructs the payload required for sending a Discord webhook notification.

        This method prepares a payload for the Discord webhook API using the provided
        message content, the Crafty Controller version, and the current UTC datetime.

        Parameters:
        server_name (str): The name of the server triggering the notification.
        title (str): The title for the notification message.
        message (str): The main content of the notification message.
        color (int): The color code for the side stripe in the Discord embed message.

        Returns:
        tuple: A tuple containing the constructed payload (dict) incl headers (dict).
        """
        current_datetime = datetime.utcnow()
        formatted_datetime = (
            current_datetime.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        )

        # Convert the hex to an integer
        sanitized_hex = color[1:] if color.startswith("#") else color
        color_int = int(sanitized_hex, 16)

        headers = {"Content-type": "application/json"}
        payload = {
            "username": self.WEBHOOK_USERNAME,
            "avatar_url": self.WEBHOOK_PFP_URL,
            "embeds": [
                {
                    "title": title,
                    "description": message,
                    "color": color_int,
                    "author": {"name": server_name},
                    "footer": {"text": f"Crafty Controller v.{self.CRAFTY_VERSION}"},
                    "timestamp": formatted_datetime,
                }
            ],
        }

        return payload, headers

    def send(self, server_name, title, url, message, **kwargs):
        """
        Sends a Discord webhook notification using the given details.

        The method constructs and dispatches a payload suitable for
        Discords's webhook system.

        Parameters:
        server_name (str): The name of the server triggering the notification.
        title (str): The title for the notification message.
        url (str): The webhook URL to send the notification to.
        message (str): The main content or body of the notification message.
        color (str, optional): The color code for the embed's side stripe.
        Defaults to a pretty blue if not provided.

        Returns:
        str: "Dispatch successful!" if the message is sent successfully, otherwise an
        exception is raised.

        Raises:
        Exception: If there's an error in dispatching the webhook.
        """
        color = kwargs.get("color", "#005cd1")  # Default to a color if not provided.
        payload, headers = self._construct_discord_payload(
            server_name, title, message, color
        )
        return self._send_request(url, payload, headers)
