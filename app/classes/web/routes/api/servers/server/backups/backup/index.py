import logging
import json
import os
from apscheduler.jobstores.base import JobLookupError
from jsonschema import validate
from jsonschema.exceptions import ValidationError
from app.classes.models.server_permissions import EnumPermissionsServer
from app.classes.shared.file_helpers import FileHelpers
from app.classes.web.base_api_handler import BaseApiHandler
from app.classes.shared.helpers import Helpers

logger = logging.getLogger(__name__)

backup_schema = {
    "type": "object",
    "properties": {
        "filename": {"type": "string", "minLength": 5},
    },
    "additionalProperties": False,
    "minProperties": 1,
}


class ApiServersServerBackupsBackupIndexHandler(BaseApiHandler):
    def get(self, server_uuid: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return
        if (
            EnumPermissionsServer.BACKUP
            not in self.controller.server_perms.get_user_id_permissions_list(
                auth_data[4]["user_id"], server_uuid
            )
        ):
            # if the user doesn't have Schedule permission, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})
        self.finish_json(200, self.controller.management.get_backup_config(server_uuid))

    def delete(self, server_uuid: str):
        auth_data = self.authenticate_user()
        backup_conf = self.controller.management.get_backup_config(server_uuid)
        if not auth_data:
            return
        if (
            EnumPermissionsServer.BACKUP
            not in self.controller.server_perms.get_user_id_permissions_list(
                auth_data[4]["user_id"], server_uuid
            )
        ):
            # if the user doesn't have Schedule permission, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        try:
            data = json.loads(self.request.body)
        except json.decoder.JSONDecodeError as e:
            return self.finish_json(
                400, {"status": "error", "error": "INVALID_JSON", "error_data": str(e)}
            )
        try:
            validate(data, backup_schema)
        except ValidationError as e:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "INVALID_JSON_SCHEMA",
                    "error_data": str(e),
                },
            )

        try:
            FileHelpers.del_file(
                os.path.join(backup_conf["backup_path"], data["filename"])
            )
        except Exception:
            return self.finish_json(
                400, {"status": "error", "error": "NO BACKUP FOUND"}
            )
        self.controller.management.add_to_audit_log(
            auth_data[4]["user_id"],
            f"Edited server {server_uuid}: removed backup {data['filename']}",
            server_uuid,
            self.get_remote_ip(),
        )

        return self.finish_json(200, {"status": "ok"})

    def post(self, server_uuid: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return
        if (
            EnumPermissionsServer.BACKUP
            not in self.controller.server_perms.get_user_id_permissions_list(
                auth_data[4]["user_id"], server_uuid
            )
        ):
            # if the user doesn't have Schedule permission, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        try:
            data = json.loads(self.request.body)
        except json.decoder.JSONDecodeError as e:
            return self.finish_json(
                400, {"status": "error", "error": "INVALID_JSON", "error_data": str(e)}
            )
        try:
            validate(data, backup_schema)
        except ValidationError as e:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "INVALID_JSON_SCHEMA",
                    "error_data": str(e),
                },
            )

        try:
            svr_obj = self.controller.servers.get_server_obj(server_uuid)
            server_data = self.controller.servers.get_server_data_by_id(server_uuid)
            zip_name = data["filename"]
            # import the server again based on zipfile
            backup_path = svr_obj.backup_path
            if Helpers.validate_traversal(backup_path, zip_name):
                temp_dir = Helpers.unzip_backup_archive(backup_path, zip_name)
                if server_data["type"] == "minecraft-java":
                    new_server = self.controller.restore_java_zip_server(
                        svr_obj.server_name,
                        temp_dir,
                        server_data["executable"],
                        "1",
                        "2",
                        server_data["server_port"],
                        server_data["created_by"],
                    )
                elif server_data["type"] == "minecraft-bedrock":
                    new_server = self.controller.restore_bedrock_zip_server(
                        svr_obj.server_name,
                        temp_dir,
                        server_data["executable"],
                        server_data["server_port"],
                        server_data["created_by"],
                    )
                new_server_uuid = new_server
                new_server = self.controller.servers.get_server_data(new_server)
                self.controller.rename_backup_dir(
                    server_uuid, new_server_uuid, new_server["server_uuid"]
                )
                # preserve current schedules
                for schedule in self.controller.management.get_schedules_by_server(
                    server_uuid
                ):
                    job_data = self.controller.management.get_scheduled_task(
                        schedule.schedule_id
                    )
                    job_data["server_uuid"] = new_server_uuid
                    del job_data["schedule_id"]
                    self.tasks_manager.update_job(schedule.schedule_id, job_data)
                # preserve execution command
                new_server_obj = self.controller.servers.get_server_obj(new_server_uuid)
                new_server_obj.execution_command = server_data["execution_command"]
                # reset executable path
                if svr_obj.path in svr_obj.executable:
                    new_server_obj.executable = str(svr_obj.executable).replace(
                        svr_obj.path, new_server_obj.path
                    )
                # reset run command path
                if svr_obj.path in svr_obj.execution_command:
                    new_server_obj.execution_command = str(
                        svr_obj.execution_command
                    ).replace(svr_obj.path, new_server_obj.path)
                # reset log path
                if svr_obj.path in svr_obj.log_path:
                    new_server_obj.log_path = str(svr_obj.log_path).replace(
                        svr_obj.path, new_server_obj.path
                    )
                self.controller.servers.update_server(new_server_obj)

                # preserve backup config
                backup_config = self.controller.management.get_backup_config(
                    server_uuid
                )
                excluded_dirs = []
                server_obj = self.controller.servers.get_server_obj(server_uuid)
                loop_backup_path = self.helper.wtol_path(server_obj.path)
                for item in self.controller.management.get_excluded_backup_dirs(
                    server_uuid
                ):
                    item_path = self.helper.wtol_path(item)
                    bu_path = os.path.relpath(item_path, loop_backup_path)
                    bu_path = os.path.join(new_server_obj.path, bu_path)
                    excluded_dirs.append(bu_path)
                self.controller.management.set_backup_config(
                    new_server_uuid,
                    new_server_obj.backup_path,
                    backup_config["max_backups"],
                    excluded_dirs,
                    backup_config["compress"],
                    backup_config["shutdown"],
                )
                # remove old server's tasks
                try:
                    self.tasks_manager.remove_all_server_tasks(server_uuid)
                except JobLookupError as e:
                    logger.info("No active tasks found for server: {e}")
                self.controller.remove_server(server_uuid, True)
        except Exception as e:
            return self.finish_json(
                400, {"status": "error", "error": f"NO BACKUP FOUND {e}"}
            )
        self.controller.management.add_to_audit_log(
            auth_data[4]["user_id"],
            f"Restored server {server_uuid} backup {data['filename']}",
            server_uuid,
            self.get_remote_ip(),
        )

        return self.finish_json(200, {"status": "ok"})
