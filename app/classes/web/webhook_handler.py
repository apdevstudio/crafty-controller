import json
import logging
import requests

logger = logging.getLogger(__name__)


class WebhookHandler:
    @staticmethod
    def send_discord_webhook(title, message, color):
        dataset = {
            "username": "Crafty Webhooks",
            "avatar_url": "https://docs.craftycontrol.com/img/favicon.ico",
            "embeds": [
                {
                    "title": title,
                    "description": message,
                    "color": color,
                }
            ],
        }

        logger.debug(
            "Webhook response: "
            + requests.post(
                "https://discord.com/api/webhooks/1107017140004995081/leFCJ4g_Uw6ZwxaZXTLmi-L7njIFwVvFbf3JEHnAvUJAd90PoMknlivel0rosfnFed77",
                data=json.dumps(dataset),
                headers={"Content-type": "application/json"},
            ),
        )
