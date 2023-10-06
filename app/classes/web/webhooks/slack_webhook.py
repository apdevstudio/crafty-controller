from app.classes.web.webhooks.base_webhook import WebhookProvider


class SlackWebhook(WebhookProvider):
    def _construct_slack_payload(self, server_name, title, message, color, bot_name):
        """
        Constructs the payload required for sending a Slack webhook notification.

        The method formats the given information into a Markdown-styled message for MM,
        including an information card containing the Crafty version.

        Parameters:
        server_name (str): The name of the server triggering the notification.
        title (str): The title for the notification message.
        message (str): The main content of the notification message.
        color (int): The color code for the side stripe in the Slack block.
        bot_name (str): Override for the Webhook's name set on creation, (not working).

        Returns:
        tuple: A tuple containing the constructed payload (dict) incl headers (dict).

        Note:
        - Block Builder/designer
        - https://app.slack.com/block-kit-builder/
        """
        headers = {"Content-Type": "application/json"}
        payload = {
            "username": bot_name,
            "attachments": [
                {
                    "color": color,
                    "blocks": [
                        {
                            "type": "section",
                            "text": {"type": "plain_text", "text": server_name},
                        },
                        {"type": "divider"},
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*{title}*\n{message}",
                            },
                            "accessory": {
                                "type": "image",
                                "image_url": self.WEBHOOK_PFP_URL,
                                "alt_text": "Crafty Controller Logo",
                            },
                        },
                        {
                            "type": "context",
                            "elements": [
                                {
                                    "type": "mrkdwn",
                                    "text": (
                                        f"*Crafty Controller "
                                        f"v{self.CRAFTY_VERSION}*"
                                    ),
                                }
                            ],
                        },
                        {"type": "divider"},
                    ],
                }
            ],
        }

        return payload, headers

    def send(self, server_name, title, url, message, **kwargs):
        """
        Sends a Slack webhook notification using the given details.

        The method constructs and dispatches a payload suitable for
        Slack's webhook system.

        Parameters:
        server_name (str): The name of the server triggering the notification.
        title (str): The title for the notification message.
        url (str): The webhook URL to send the notification to.
        message (str): The main content or body of the notification message.
        color (str, optional): The color code for the blocks's colour accent.
        Defaults to a pretty blue if not provided.
        bot_name (str): Override for the Webhook's name set on creation, (not working).

        Returns:
        str: "Dispatch successful!" if the message is sent successfully, otherwise an
        exception is raised.

        Raises:
        Exception: If there's an error in dispatching the webhook.
        """
        color = kwargs.get("color", "#005cd1")  # Default to a color if not provided.
        bot_name = kwargs.get("bot_name", self.WEBHOOK_USERNAME)
        payload, headers = self._construct_slack_payload(
            server_name, title, message, color, bot_name
        )
        return self._send_request(url, payload, headers)
