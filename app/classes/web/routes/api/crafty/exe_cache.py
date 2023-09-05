from app.classes.web.base_api_handler import BaseApiHandler


class ApiCraftyExeCacheIndexHandler(BaseApiHandler):
    def get(self):
        auth_data = self.authenticate_user()
        if not auth_data:
            return
        (
            _,
            _,
            _,
            _,
            _,
        ) = auth_data

        if not auth_data[4]["superuser"]:
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        self.controller.server_jars.manual_refresh_cache()
        self.finish_json(
            200,
            {
                "status": "ok",
                "data": self.controller.server_jars.get_serverjar_data(),
            },
        )
