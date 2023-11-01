import logging

from app.classes.shared.console import Console

from app.classes.shared.main_controller import Controller
from app.classes.models.servers import Servers
from app.classes.models.management import (
    AuditLog,
    Webhooks,
    Schedules,
    Backups,
)
from app.classes.models.server_permissions import RoleServers

logger = logging.getLogger(__name__)


class MigrateUUID:
    def __init__(self, helper, controller: Controller):
        self.helper = helper
        self.controller = controller

    def start_migrate(self):
        success = self.update_backreferences_tables()
        if success:
            self.migrate_servers()

    def update_backreferences_tables(self):
        try:
            # Changes on Audit Log Table
            for audit_log in AuditLog.select():
                old_server_id = audit_log.server_id_id
                if old_server_id == "0" or old_server_id is None:
                    server_uuid = None
                else:
                    try:
                        server = Servers.get_by_id(old_server_id)
                        server_uuid = server.server_uuid
                    except:
                        server_uuid = old_server_id
                AuditLog.update(server_id=server_uuid).where(
                    AuditLog.audit_id == audit_log.audit_id
                ).execute()

            # Changes on Webhooks Log Table
            for webhook in Webhooks.select():
                old_server_id = webhook.server_id_id
                try:
                    server = Servers.get_by_id(old_server_id)
                    server_uuid = server.server_uuid
                except:
                    server_uuid = old_server_id
                Webhooks.update(server_id=server_uuid).where(
                    Webhooks.id == webhook.id
                ).execute()

            # Changes on Schedules Log Table
            for schedule in Schedules.select():
                old_server_id = schedule.server_id_id
                try:
                    server = Servers.get_by_id(old_server_id)
                    server_uuid = server.server_uuid
                except:
                    server_uuid = old_server_id
                Schedules.update(server_id=server_uuid).where(
                    Schedules.schedule_id == schedule.schedule_id
                ).execute()

            # Changes on Backups Log Table
            for backup in Backups.select():
                old_server_id = backup.server_id_id
                try:
                    server = Servers.get_by_id(old_server_id)
                    server_uuid = server.server_uuid
                except:
                    server_uuid = old_server_id
                Backups.update(server_id=server_uuid).where(
                    Backups.server_id == old_server_id
                ).execute()

            # Changes on RoleServers Log Table
            for role_servers in RoleServers.select():
                old_server_id = role_servers.server_id_id
                try:
                    server = Servers.get_by_id(old_server_id)
                    server_uuid = server.server_uuid
                except:
                    server_uuid = old_server_id
                RoleServers.update(server_id=server_uuid).where(
                    RoleServers.role_id == role_servers.id
                    and RoleServers.server_id == old_server_id
                ).execute()

        except Exception as ex:
            logger.error("Error while migrating Data from Int to UUID")
            logger.error(ex)
            Console.error("Error while migrating Data from Int to UUID")
            Console.error(ex)
            return False
        return True

    def migrate_servers(self):
        try:
            # Migrating servers from the old id type to the new one
            for server in Servers.select():
                Servers.update(server_id=server.server_uuid).where(
                    Servers.server_id == server.server_id
                ).execute()

        except Exception as ex:
            logger.error("Error while migrating Data from Int to UUID")
            logger.error(ex)
            Console.error("Error while migrating Data from Int to UUID")
            Console.error(ex)
            return False
        return True
