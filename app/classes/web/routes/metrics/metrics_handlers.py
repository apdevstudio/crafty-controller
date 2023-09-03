from app.classes.web.routes.metrics.index import ApiOpenMetricsIndexHandler
from app.classes.web.routes.metrics.servers import ApiOpenMetricsServersHandler


def metrics_handlers(handler_args):
    return [
        # OpenMetrics routes
        (
            r"/metrics?",
            ApiOpenMetricsIndexHandler,
            handler_args,
        ),
        (
            r"/metrics/servers/(0-9)+?",
            ApiOpenMetricsServersHandler,
            handler_args,
        ),
    ]
