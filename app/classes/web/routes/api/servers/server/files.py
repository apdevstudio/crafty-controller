import os
import logging
import json
import html
from jsonschema import validate
from jsonschema.exceptions import ValidationError
from app.classes.models.server_permissions import EnumPermissionsServer
from app.classes.shared.helpers import Helpers
from app.classes.shared.file_helpers import FileHelpers
from app.classes.web.base_api_handler import BaseApiHandler

logger = logging.getLogger(__name__)

files_get_schema = {
    "type": "object",
    "properties": {
        "page": {"type": "string", "minLength": 1},
        "path": {"type": "string"},
    },
    "additionalProperties": False,
    "minProperties": 1,
}

files_patch_schema = {
    "type": "object",
    "properties": {
        "path": {"type": "string"},
        "contents": {"type": "string"},
    },
    "additionalProperties": False,
    "minProperties": 1,
}

files_unzip_schema = {
    "type": "object",
    "properties": {
        "folder": {"type": "string"},
    },
    "additionalProperties": False,
    "minProperties": 1,
}

files_create_schema = {
    "type": "object",
    "properties": {
        "parent": {"type": "string"},
        "name": {"type": "string"},
        "directory": {"type": "boolean"},
    },
    "additionalProperties": False,
    "minProperties": 1,
}

files_rename_schema = {
    "type": "object",
    "properties": {
        "path": {"type": "string"},
        "new_name": {"type": "string"},
    },
    "additionalProperties": False,
    "minProperties": 1,
}

file_delete_schema = {
    "type": "object",
    "properties": {
        "filename": {"type": "string", "minLength": 5},
    },
    "additionalProperties": False,
    "minProperties": 1,
}


class ApiServersServerFilesIndexHandler(BaseApiHandler):
    def post(self, server_id: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return

        if server_id not in [str(x["server_id"]) for x in auth_data[0]]:
            # if the user doesn't have access to the server, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        if (
            EnumPermissionsServer.FILES
            not in self.controller.server_perms.get_user_id_permissions_list(
                auth_data[4]["user_id"], server_id
            )
            or EnumPermissionsServer.BACKUP
            not in self.controller.server_perms.get_user_id_permissions_list(
                auth_data[4]["user_id"], server_id
            )
        ):
            # if the user doesn't have Files or Backup permission, return an error
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
            data["path"],
        ):
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "TRAVERSAL DETECTED",
                    "error_data": str(e),
                },
            )
        if os.path.isdir(data["path"]):
            # TODO: limit some columns for specific permissions?
            folder = data["path"]
            return_json = {
                "root_path": {
                    "path": folder,
                    "top": data["path"]
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
        else:
            try:
                with open(data["path"], encoding="utf-8") as file:
                    file_contents = file.read()
            except UnicodeDecodeError as ex:
                self.finish_json(
                    400,
                    {"status": "error", "error": "DECODE_ERROR", "error_data": str(ex)},
                )
            self.finish_json(200, {"status": "ok", "data": file_contents})

    def delete(self, server_id: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return

        if server_id not in [str(x["server_id"]) for x in auth_data[0]]:
            # if the user doesn't have access to the server, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        if (
            EnumPermissionsServer.FILES
            not in self.controller.server_perms.get_user_id_permissions_list(
                auth_data[4]["user_id"], server_id
            )
        ):
            # if the user doesn't have Files permission, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})
        try:
            data = json.loads(self.request.body)
        except json.decoder.JSONDecodeError as e:
            return self.finish_json(
                400, {"status": "error", "error": "INVALID_JSON", "error_data": str(e)}
            )
        try:
            validate(data, file_delete_schema)
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
            data["filename"],
        ):
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "TRAVERSAL DETECTED",
                    "error_data": str(e),
                },
            )

        if os.path.isdir(data["filename"]):
            FileHelpers.del_dirs(data["filename"])
        else:
            FileHelpers.del_file(data["filename"])
        return self.finish_json(200, {"status": "ok"})

    def patch(self, server_id: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return

        if server_id not in [str(x["server_id"]) for x in auth_data[0]]:
            # if the user doesn't have access to the server, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        if (
            EnumPermissionsServer.FILES
            not in self.controller.server_perms.get_user_id_permissions_list(
                auth_data[4]["user_id"], server_id
            )
        ):
            # if the user doesn't have Files permission, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})
        try:
            data = json.loads(self.request.body)
        except json.decoder.JSONDecodeError as e:
            return self.finish_json(
                400, {"status": "error", "error": "INVALID_JSON", "error_data": str(e)}
            )
        try:
            validate(data, files_patch_schema)
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
            data["path"],
        ):
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "TRAVERSAL DETECTED",
                    "error_data": str(e),
                },
            )
        file_path = Helpers.get_os_understandable_path(data["path"])
        file_contents = data["contents"]
        # Open the file in write mode and store the content in file_object
        with open(file_path, "w", encoding="utf-8") as file_object:
            file_object.write(file_contents)
        return self.finish_json(200, {"status": "ok"})

    def put(self, server_id: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return

        if server_id not in [str(x["server_id"]) for x in auth_data[0]]:
            # if the user doesn't have access to the server, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        if (
            EnumPermissionsServer.FILES
            not in self.controller.server_perms.get_user_id_permissions_list(
                auth_data[4]["user_id"], server_id
            )
        ):
            # if the user doesn't have Files permission, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})
        try:
            data = json.loads(self.request.body)
        except json.decoder.JSONDecodeError as e:
            return self.finish_json(
                400, {"status": "error", "error": "INVALID_JSON", "error_data": str(e)}
            )
        try:
            validate(data, files_create_schema)
        except ValidationError as e:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "INVALID_JSON_SCHEMA",
                    "error_data": str(e),
                },
            )
        path = os.path.join(data["parent"], data["name"])
        if not Helpers.validate_traversal(
            self.controller.servers.get_server_data_by_id(server_id)["path"],
            path,
        ):
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "TRAVERSAL DETECTED",
                    "error_data": str(e),
                },
            )
        if Helpers.check_path_exists(os.path.abspath(path)):
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "FILE EXISTS",
                    "error_data": str(e),
                },
            )
        if data["directory"]:
            os.mkdir(path)
        else:
            # Create the file by opening it
            with open(path, "w", encoding="utf-8") as file_object:
                file_object.close()
        return self.finish_json(200, {"status": "ok"})


class ApiServersServerFilesCreateHandler(BaseApiHandler):
    def patch(self, server_id: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return

        if server_id not in [str(x["server_id"]) for x in auth_data[0]]:
            # if the user doesn't have access to the server, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        if (
            EnumPermissionsServer.FILES
            not in self.controller.server_perms.get_user_id_permissions_list(
                auth_data[4]["user_id"], server_id
            )
        ):
            # if the user doesn't have Files permission, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})
        try:
            data = json.loads(self.request.body)
        except json.decoder.JSONDecodeError as e:
            return self.finish_json(
                400, {"status": "error", "error": "INVALID_JSON", "error_data": str(e)}
            )
        try:
            validate(data, files_rename_schema)
        except ValidationError as e:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "INVALID_JSON_SCHEMA",
                    "error_data": str(e),
                },
            )
        path = data["path"]
        new_item_name = data["new_name"]
        new_item_path = os.path.join(os.path.split(path)[0], new_item_name)
        if not Helpers.validate_traversal(
            self.controller.servers.get_server_data_by_id(server_id)["path"],
            path,
        ) or not Helpers.validate_traversal(
            self.controller.servers.get_server_data_by_id(server_id)["path"],
            new_item_path,
        ):
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "TRAVERSAL DETECTED",
                    "error_data": str(e),
                },
            )
        if Helpers.check_path_exists(os.path.abspath(new_item_path)):
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "FILE EXISTS",
                    "error_data": {},
                },
            )

        os.rename(path, new_item_path)
        return self.finish_json(200, {"status": "ok"})

    def put(self, server_id: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return

        if server_id not in [str(x["server_id"]) for x in auth_data[0]]:
            # if the user doesn't have access to the server, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        if (
            EnumPermissionsServer.FILES
            not in self.controller.server_perms.get_user_id_permissions_list(
                auth_data[4]["user_id"], server_id
            )
        ):
            # if the user doesn't have Files permission, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})
        try:
            data = json.loads(self.request.body)
        except json.decoder.JSONDecodeError as e:
            return self.finish_json(
                400, {"status": "error", "error": "INVALID_JSON", "error_data": str(e)}
            )
        try:
            validate(data, files_create_schema)
        except ValidationError as e:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "INVALID_JSON_SCHEMA",
                    "error_data": str(e),
                },
            )
        path = os.path.join(data["parent"], data["name"])
        if not Helpers.validate_traversal(
            self.controller.servers.get_server_data_by_id(server_id)["path"],
            path,
        ):
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "TRAVERSAL DETECTED",
                    "error_data": str(e),
                },
            )
        if Helpers.check_path_exists(os.path.abspath(path)):
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "FILE EXISTS",
                    "error_data": str(e),
                },
            )
        if data["directory"]:
            os.mkdir(path)
        else:
            # Create the file by opening it
            with open(path, "w", encoding="utf-8") as file_object:
                file_object.close()
        return self.finish_json(200, {"status": "ok"})


class ApiServersServerFilesZipHandler(BaseApiHandler):
    def post(self, server_id: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return

        if server_id not in [str(x["server_id"]) for x in auth_data[0]]:
            # if the user doesn't have access to the server, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        if (
            EnumPermissionsServer.FILES
            not in self.controller.server_perms.get_user_id_permissions_list(
                auth_data[4]["user_id"], server_id
            )
        ):
            # if the user doesn't have Files permission, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})
        try:
            data = json.loads(self.request.body)
        except json.decoder.JSONDecodeError as e:
            return self.finish_json(
                400, {"status": "error", "error": "INVALID_JSON", "error_data": str(e)}
            )
        try:
            validate(data, files_unzip_schema)
        except ValidationError as e:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "INVALID_JSON_SCHEMA",
                    "error_data": str(e),
                },
            )
        folder = data["folder"]
        user_id = auth_data[4]["user_id"]
        if not Helpers.validate_traversal(
            self.controller.servers.get_server_data_by_id(server_id)["path"],
            folder,
        ):
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "TRAVERSAL DETECTED",
                    "error_data": str(e),
                },
            )
        if Helpers.check_file_exists(folder):
            folder = self.file_helper.unzip_file(folder, user_id)
        else:
            if user_id:
                return self.finish_json(
                    400,
                    {
                        "status": "error",
                        "error": "FILE_DOES_NOT_EXIST",
                        "error_data": str(e),
                    },
                )
        return self.finish_json(200, {"status": "ok"})
