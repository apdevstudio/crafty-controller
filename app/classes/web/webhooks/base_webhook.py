from abc import ABC, abstractmethod
import logging
import requests

from app.classes.shared.helpers import Helpers

logger = logging.getLogger(__name__)
helper = Helpers()


class WebhookProvider(ABC):
    """
    Base class for all webhook providers.

    Provides a common interface for all webhook provider implementations,
    ensuring that each provider will have a send method.
    """

    WEBHOOK_USERNAME = "Crafty Webhooks"
    WEBHOOK_PFP_URL = (
        "https://gitlab.com/crafty-controller/crafty-4/-"
        + "/raw/master/app/frontend/static/assets/images/"
        + "Crafty_4-0.png"
    )
    CRAFTY_VERSION = helper.get_version_string()

    def _send_request(self, url, payload, headers=None):
        """Send a POST request to the given URL with the provided payload."""
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            return "Dispatch successful"
        except requests.RequestException as error:
            logger.error(error)
            raise RuntimeError(f"Failed to dispatch notification: {error}") from error

    @abstractmethod
    def send(self, server_name, title, url, message, **kwargs):
        """Abstract method that derived classes will implement for sending webhooks."""
