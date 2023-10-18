from datetime import datetime
from app.classes.web.webhooks.base_webhook import WebhookProvider


class TeamsWebhook(WebhookProvider):
    def _construct_teams_payload(self, server_name, title, message):
        """
        Constructs the payload required for sending a Teams Adaptive card notification.

        This method prepares a payload for the Teams webhook API using the provided
        message content, the Crafty Controller version, and the current UTC datetime.

        Parameters:
        server_name (str): The name of the server triggering the notification.
        title (str): The title for the notification message.
        message (str): The main content of the notification message.

        Returns:
        tuple: A tuple containing the constructed payload (dict) incl headers (dict).

        Note:
        - Adaptive Card Designer
        - https://www.adaptivecards.io/designer/
        """
        current_datetime = datetime.utcnow()
        formatted_datetime = current_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")

        headers = {"Content-type": "application/json"}
        payload = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "body": [
                            {
                                "type": "TextBlock",
                                "size": "Medium",
                                "weight": "Bolder",
                                "text": f"{title}",
                            },
                            {
                                "type": "ColumnSet",
                                "columns": [
                                    {
                                        "type": "Column",
                                        "items": [
                                            {
                                                "type": "Image",
                                                "style": "Person",
                                                "url": f"{self.WEBHOOK_PFP_URL}",
                                                "size": "Small",
                                            }
                                        ],
                                        "width": "auto",
                                    },
                                    {
                                        "type": "Column",
                                        "items": [
                                            {
                                                "type": "TextBlock",
                                                "weight": "Bolder",
                                                "text": f"{server_name}",
                                                "wrap": True,
                                            },
                                            {
                                                "type": "TextBlock",
                                                "spacing": "None",
                                                "text": "{{DATE("
                                                + f"{formatted_datetime}"
                                                + ",SHORT)}}",
                                                "isSubtle": True,
                                                "wrap": True,
                                            },
                                        ],
                                        "width": "stretch",
                                    },
                                ],
                            },
                            {
                                "type": "TextBlock",
                                "text": f"{message}",
                                "wrap": True,
                            },
                            {
                                "type": "TextBlock",
                                "text": f"Crafty Controller v{self.CRAFTY_VERSION}",
                                "wrap": True,
                                "separator": True,
                                "isSubtle": True,
                            },
                        ],
                        "$schema": (
                            "https://adaptivecards.io/schemas/adaptive-card.json"
                        ),
                        "version": "1.6",
                    },
                }
            ],
        }

        return payload, headers

    def send(self, server_name, title, url, message, **kwargs):
        """
        Sends a Teams Adaptive card notification using the given details.

        The method constructs and dispatches a payload suitable for
        Discords's webhook system.

        Parameters:
        server_name (str): The name of the server triggering the notification.
        title (str): The title for the notification message.
        url (str): The webhook URL to send the notification to.
        message (str): The main content or body of the notification message.
        Defaults to a pretty blue if not provided.

        Returns:
        str: "Dispatch successful!" if the message is sent successfully, otherwise an
        exception is raised.

        Raises:
        Exception: If there's an error in dispatching the webhook.
        """
        payload, headers = self._construct_teams_payload(server_name, title, message)
        return self._send_request(url, payload, headers)
