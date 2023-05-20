import logging
import json
import os
from app.classes.models.server_permissions import EnumPermissionsServer
from app.classes.shared.file_helpers import FileHelpers
from app.classes.web.base_api_handler import BaseApiHandler

logger = logging.getLogger(__name__)


class ApiServersServerBackupsBackupIndexHandler(BaseApiHandler):
    def get(self, server_id: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return
        if (
            EnumPermissionsServer.BACKUP
            not in self.controller.server_perms.get_user_id_permissions_list(
                auth_data[4]["user_id"], server_id
            )
        ):
            # if the user doesn't have Schedule permission, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})
        self.finish_json(200, self.controller.management.get_backup_config(server_id))

    def delete(self, server_id: str, backup_name: str):
        auth_data = self.authenticate_user()
        backup_conf = self.controller.management.get_backup_config(server_id)
        if not auth_data:
            return
        if (
            EnumPermissionsServer.BACKUP
            not in self.controller.server_perms.get_user_id_permissions_list(
                auth_data[4]["user_id"], server_id
            )
        ):
            # if the user doesn't have Schedule permission, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        try:
            FileHelpers.del_file(os.path.join(backup_conf["backup_path"], backup_name))
        except Exception:
            return self.finish_json(
                400, {"status": "error", "error": "NO BACKUP FOUND"}
            )
        self.controller.management.add_to_audit_log(
            auth_data[4]["user_id"],
            f"Edited server {server_id}: removed backup {backup_name}",
            server_id,
            self.get_remote_ip(),
        )

        return self.finish_json(200, {"status": "ok"})
