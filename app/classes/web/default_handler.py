import logging

from app.classes.web.base_handler import BaseHandler

logger = logging.getLogger(__name__)


class DefaultHandler(BaseHandler):
    # Override prepare() instead of get() to cover all possible HTTP methods.
    def prepare(self, page=None):  # pylint: disable=arguments-differ
        if page is not None:
            self.set_status(404)
            self.render(
                "public/404.html",
                translate=self.translator.translate,
            )
        else:
            self.redirect(
                "/panel/dashboard",
            )
