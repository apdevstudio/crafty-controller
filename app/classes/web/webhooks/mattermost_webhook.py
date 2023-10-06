from app.classes.web.webhooks.base_webhook import WebhookProvider


class MattermostWebhook(WebhookProvider):
    def _construct_mattermost_payload(self, server_name, title, message, bot_name):
        """
        Constructs the payload required for sending a Mattermost webhook notification.

        The method formats the given information into a Markdown-styled message for MM,
        including an information card containing the Crafty version.

        Parameters:
        server_name (str): The name of the server triggering the notification.
        title (str): The title for the notification message.
        message (str): The main content of the notification message.
        bot_name (str): Override for the Webhook's name set on creation.

        Returns:
        tuple: A tuple containing the constructed payload (dict) incl headers (dict).
        """
        formatted_text = (
            f"-----\n\n"
            f"#### {title}\n"
            f"##### Server: ```{server_name}```\n\n"
            f"```\n{message}\n```\n\n"
            f"-----"
        )

        headers = {"Content-Type": "application/json"}
        payload = {
            "text": formatted_text,
            "username": bot_name,
            "icon_url": self.WEBHOOK_PFP_URL,
            "props": {
                "card": (
                    f"[Crafty Controller "
                    f"v.{self.CRAFTY_VERSION}](https://craftycontrol.com)"
                )
            },
        }

        return payload, headers

    def send(self, server_name, title, url, message, **kwargs):
        """
        Sends a Mattermost webhook notification using the given details.

        The method constructs and dispatches a payload suitable for
        Mattermost's webhook system.

        Parameters:
        server_name (str): The name of the server triggering the notification.
        title (str): The title for the notification message.
        url (str): The webhook URL to send the notification to.
        message (str): The main content or body of the notification message.
        bot_name (str): Override for the Webhook's name set on creation, see note!

        Returns:
        str: "Dispatch successful!" if the message is sent successfully, otherwise an
        exception is raised.

        Raises:
        Exception: If there's an error in dispatching the webhook.

        Note:
        - To set webhook username & pfp Mattermost needs to be configured to allow this!
        - Mattermost's `config.json` setting is `"EnablePostUsernameOverride": true`
        - Mattermost's `config.json` setting is `"EnablePostIconOverride": true`
        """
        bot_name = kwargs.get("bot_name", self.WEBHOOK_USERNAME)
        payload, headers = self._construct_mattermost_payload(
            server_name, title, message, bot_name
        )
        return self._send_request(url, payload, headers)
