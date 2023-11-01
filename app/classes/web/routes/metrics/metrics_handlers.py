from app.classes.web.routes.metrics.index import ApiOpenMetricsIndexHandler
from app.classes.web.routes.metrics.host import ApiOpenMetricsCraftyHandler
from app.classes.web.routes.metrics.servers import ApiOpenMetricsServersHandler


def metrics_handlers(handler_args):
    return [
        # OpenMetrics routes
        (
            r"/metrics/?",
            ApiOpenMetricsIndexHandler,
            handler_args,
        ),
        (
            r"/metrics/host/?",
            ApiOpenMetricsCraftyHandler,
            handler_args,
        ),
        (
            r"/metrics/servers/([a-z0-9-]+)/?",
            ApiOpenMetricsServersHandler,
            handler_args,
        ),
    ]
