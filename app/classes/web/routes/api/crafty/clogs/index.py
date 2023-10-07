from app.classes.web.base_api_handler import BaseApiHandler


class ApiCraftyLogIndexHandler(BaseApiHandler):
    def get(self, log_type: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return
        (
            _,
            _,
            _,
            superuser,
            _,
        ) = auth_data

        if not superuser:
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        log_types = ["audit", "session", "schedule"]
        if log_type not in log_types:
            raise NotImplementedError

        if log_type == "audit":
            return self.finish_json(
                200,
                {"status": "ok", "data": self.controller.management.get_activity_log()},
            )

        if log_type == "session":
            raise NotImplementedError

        if log_type == "schedule":
            raise NotImplementedError
