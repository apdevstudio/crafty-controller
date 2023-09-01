import logging
import json
from jsonschema import ValidationError, validate
from app.classes.web.base_api_handler import BaseApiHandler

logger = logging.getLogger(__name__)

notif_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
    },
    "additionalProperties": False,
    "minProperties": 1,
}


class ApiAnnounceIndexHandler(BaseApiHandler):
    def get(self):
        auth_data = self.authenticate_user()
        if not auth_data:
            return
        (
            _,
            _exec_user_crafty_permissions,
            _,
            _,
            _user,
        ) = auth_data

        data = self.helper.get_announcements()
        cleared = str(
            self.controller.users.get_user_by_id(auth_data[4]["user_id"])[
                "cleared_notifs"
            ]
        ).split(",")
        res = [d.get("id", None) for d in data]
        # remove notifs that are no longer in Crafty.
        for item in cleared[:]:
            if item not in res:
                cleared.remove(item)
        if len(cleared) > 0:
            for item in data[:]:
                if item["id"] in cleared:
                    data.remove(item)

        self.finish_json(
            200,
            {
                "status": "ok",
                "data": data,
            },
        )

    def post(self):
        auth_data = self.authenticate_user()
        if not auth_data:
            return
        (
            _,
            _exec_user_crafty_permissions,
            _,
            _,
            _user,
        ) = auth_data
        try:
            data = json.loads(self.request.body)
        except json.decoder.JSONDecodeError as e:
            return self.finish_json(
                400, {"status": "error", "error": "INVALID_JSON", "error_data": str(e)}
            )

        try:
            validate(data, notif_schema)
        except ValidationError as e:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "INVALID_JSON_SCHEMA",
                    "error_data": str(e),
                },
            )
        announcements = self.helper.get_announcements()
        res = [d.get("id", None) for d in announcements]
        cleared_notifs = str(
            self.controller.users.get_user_by_id(auth_data[4]["user_id"])[
                "cleared_notifs"
            ]
        ).split(",")
        # remove notifs that are no longer in Crafty.
        for item in cleared_notifs[:]:
            if item not in res:
                cleared_notifs.remove(item)
        cleared_notifs.append(data["id"])
        updata = {"cleared_notifs": ",".join(cleared_notifs)}
        self.controller.users.update_user(auth_data[4]["user_id"], updata)
        self.finish_json(
            200,
            {
                "status": "ok",
                "data": {},
            },
        )
