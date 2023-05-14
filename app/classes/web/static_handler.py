from typing import Optional

try:
    import tornado.web

except ModuleNotFoundError as e:
    from app.classes.shared.helpers import helper

    helper.auto_installer_fix(e)


class CustomStaticHandler(tornado.web.StaticFileHandler):
    def validate_absolute_path(self, root: str, absolute_path: str) -> Optional[str]:
        # This is for the mobile app service worker
        if self.request.path.find("service-worker.js") != -1:
            self.set_header("Service-Worker-Allowed", "/")
        try:
            return super().validate_absolute_path(root, absolute_path)
        except tornado.web.HTTPError as error:
            if "HTTP 404: Not Found" in str(error):
                self.set_status(404)
                self.finish(
                    {
                        "error": "NOT_FOUND",
                        "info": "The requested resource was not found on the server",
                    }
                )
