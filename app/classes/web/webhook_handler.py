import json
import logging
import requests

logger = logging.getLogger(__name__)


class WebhookHandler:
    @staticmethod
    def get_providers():
        return [
            "Discord",
            "Home Assistant",
            "Mattermost",
            "Opsgenie",
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
    def send_discord_webhook(title, url, message, color):
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
        requests.post(
            url,
            data=json.dumps(dataset),
            headers={"Content-type": "application/json"},
        )
