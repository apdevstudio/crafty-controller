import os
import logging
import json
import html
from jsonschema import validate
from jsonschema.exceptions import ValidationError
from app.classes.models.server_permissions import EnumPermissionsServer
from app.classes.shared.helpers import Helpers
from app.classes.web.base_api_handler import BaseApiHandler

logger = logging.getLogger(__name__)

files_get_schema = {
    "type": "object",
    "properties": {
        "page": {"type": "string", "minLength": 1},
        "folder": {"type": "string"},
    },
    "additionalProperties": False,
    "minProperties": 1,
}


class ApiServersServerBackupsFilesIndexHandler(BaseApiHandler):
    def post(self, server_id: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return

        if server_id not in [str(x["server_id"]) for x in auth_data[0]]:
            # if the user doesn't have access to the server, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        if (
            EnumPermissionsServer.BACKUP
            not in self.controller.server_perms.get_user_id_permissions_list(
                auth_data[4]["user_id"], server_id
            )
        ):
            # if the user doesn't have Config permission, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        try:
            data = json.loads(self.request.body)
        except json.decoder.JSONDecodeError as e:
            return self.finish_json(
                400, {"status": "error", "error": "INVALID_JSON", "error_data": str(e)}
            )
        try:
            validate(data, files_get_schema)
        except ValidationError as e:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "INVALID_JSON_SCHEMA",
                    "error_data": str(e),
                },
            )
        if not Helpers.validate_traversal(
            self.controller.servers.get_server_data_by_id(server_id)["path"],
            data["folder"],
        ):
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "TRAVERSAL DETECTED",
                    "error_data": str(e),
                },
            )
        # TODO: limit some columns for specific permissions?
        folder = data["folder"]
        return_json = {
            "root_path": {
                "path": folder,
                "top": data["folder"]
                == self.controller.servers.get_server_data_by_id(server_id)["path"],
            }
        }

        dir_list = []
        unsorted_files = []
        file_list = os.listdir(folder)
        for item in file_list:
            if os.path.isdir(os.path.join(folder, item)):
                dir_list.append(item)
            else:
                unsorted_files.append(item)
        file_list = sorted(dir_list, key=str.casefold) + sorted(
            unsorted_files, key=str.casefold
        )
        for raw_filename in file_list:
            filename = html.escape(raw_filename)
            rel = os.path.join(folder, raw_filename)
            dpath = os.path.join(folder, filename)
            if str(dpath) in self.controller.management.get_excluded_backup_dirs(
                server_id
            ):
                if os.path.isdir(rel):
                    return_json[filename] = {
                        "path": dpath,
                        "dir": True,
                        "excluded": True,
                    }
                else:
                    return_json[filename] = {
                        "path": dpath,
                        "dir": False,
                        "excluded": True,
                    }
            else:
                if os.path.isdir(rel):
                    return_json[filename] = {
                        "path": dpath,
                        "dir": True,
                        "excluded": False,
                    }
                else:
                    return_json[filename] = {
                        "path": dpath,
                        "dir": False,
                        "excluded": False,
                    }
        self.finish_json(200, {"status": "ok", "data": return_json})
