from app.classes.web.webhooks.discord_webhook import DiscordWebhook
from app.classes.web.webhooks.mattermost_webhook import MattermostWebhook
from app.classes.web.webhooks.slack_webhook import SlackWebhook
from app.classes.web.webhooks.teams_adaptive_webhook import TeamsWebhook


class WebhookFactory:
    """
    A factory class responsible for the creation and management of webhook providers.

    This class provides methods to instantiate specific webhook providers based on
    their name and to retrieve a list of supported providers. It uses a registry pattern
    to manage the available providers.

    Attributes:
    - _registry (dict): A dictionary mapping provider names to their classes.
    """

    _registry = {
        "Discord": DiscordWebhook,
        "Mattermost": MattermostWebhook,
        "Slack": SlackWebhook,
        "Teams": TeamsWebhook,
    }

    @classmethod
    def create_provider(cls, provider_name, *args, **kwargs):
        """
        Creates and returns an instance of the specified webhook provider.

        This method looks up the provider in the registry, then instantiates it w/ the
        provided arguments. If the provider is not recognized, a ValueError is raised.

        Arguments:
        - provider_name (str): The name of the desired webhook provider.

        Additional arguments supported that we may use for if a provider
        requires initialization:
        - *args: Positional arguments to pass to the provider's constructor.
        - **kwargs: Keyword arguments to pass to the provider's constructor.

        Returns:
        WebhookProvider: An instance of the desired webhook provider.

        Raises:
        ValueError: If the specified provider name is not recognized.
        """
        if provider_name not in cls._registry:
            raise ValueError(f"Provider {provider_name} is not supported.")
        return cls._registry[provider_name](*args, **kwargs)

    @classmethod
    def get_supported_providers(cls):
        """
        Retrieves the names of all supported webhook providers.

        This method returns a list containing the names of all providers
        currently registered in the factory's registry.

        Returns:
        List[str]: A list of supported provider names.
        """
        return list(cls._registry.keys())

    @staticmethod
    def get_monitored_events():
        """
        Retrieves the list of supported events for monitoring.

        This method provides a list of common server events that the webhook system can
        monitor and notify about.

        Returns:
        List[str]: A list of supported monitored actions.
        """
        return [
            "start_server",
            "stop_server",
            "crash_detected",
            "backup_server",
            "jar_update",
            "send_command",
            "kill",
        ]
