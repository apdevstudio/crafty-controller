import logging

from app.classes.models.management import HelpersManagement
from app.classes.models.servers import HelperServers

logger = logging.getLogger(__name__)


class ManagementController:
    def __init__(self, management_helper):
        self.management_helper = management_helper

    # **********************************************************************************
    #                                   Host_Stats Methods
    # **********************************************************************************
    @staticmethod
    def get_latest_hosts_stats():
        return HelpersManagement.get_latest_hosts_stats()

    @staticmethod
    def set_crafty_api_key(key):
        HelpersManagement.set_secret_api_key(key)

    @staticmethod
    def get_crafty_api_key():
        return HelpersManagement.get_secret_api_key()

    # **********************************************************************************
    #                                   Commands Methods
    # **********************************************************************************
    @staticmethod
    def get_unactioned_commands():
        return HelpersManagement.get_unactioned_commands()

    def send_command(self, user_id, server_id, remote_ip, command):
        server_name = HelperServers.get_server_friendly_name(server_id)

        # Example: Admin issued command start_server for server Survival
        self.management_helper.add_to_audit_log(
            user_id,
            f"issued command {command} for server {server_name}",
            server_id,
            remote_ip,
        )
        HelpersManagement.add_command(server_id, user_id, remote_ip, command)

    @staticmethod
    def mark_command_complete(command_id=None):
        return HelpersManagement.mark_command_complete(command_id)

    # **********************************************************************************
    #                                   Audit_Log Methods
    # **********************************************************************************
    @staticmethod
    def get_actity_log():
        return HelpersManagement.get_actity_log()

    def add_to_audit_log(self, user_id, log_msg, server_id=None, source_ip=None):
        return self.management_helper.add_to_audit_log(
            user_id, log_msg, server_id, source_ip
        )

    def add_to_audit_log_raw(self, user_name, user_id, server_id, log_msg, source_ip):
        return self.management_helper.add_to_audit_log_raw(
            user_name, user_id, server_id, log_msg, source_ip
        )

    # **********************************************************************************
    #                                  Schedules Methods
    # **********************************************************************************
    @staticmethod
    def create_scheduled_task(
        server_id,
        action,
        interval,
        interval_type,
        start_time,
        command,
        name,
        enabled=True,
    ):
        return HelpersManagement.create_scheduled_task(
            server_id,
            action,
            interval,
            interval_type,
            start_time,
            command,
            name,
            enabled,
        )

    @staticmethod
    def delete_scheduled_task(schedule_id):
        return HelpersManagement.delete_scheduled_task(schedule_id)

    @staticmethod
    def set_login_image(path):
        HelpersManagement.set_login_image(path)

    @staticmethod
    def get_login_image():
        return HelpersManagement.get_login_image()

    @staticmethod
    def update_scheduled_task(schedule_id, updates):
        return HelpersManagement.update_scheduled_task(schedule_id, updates)

    @staticmethod
    def get_scheduled_task(schedule_id):
        return HelpersManagement.get_scheduled_task(schedule_id)

    @staticmethod
    def get_scheduled_task_model(schedule_id):
        return HelpersManagement.get_scheduled_task_model(schedule_id)

    @staticmethod
    def get_child_schedules(sch_id):
        return HelpersManagement.get_child_schedules(sch_id)

    @staticmethod
    def get_schedules_by_server(server_id):
        return HelpersManagement.get_schedules_by_server(server_id)

    @staticmethod
    def get_schedules_all():
        return HelpersManagement.get_schedules_all()

    @staticmethod
    def get_schedules_enabled():
        return HelpersManagement.get_schedules_enabled()

    # **********************************************************************************
    #                                   Backups Methods
    # **********************************************************************************
    @staticmethod
    def get_backup_config(server_id):
        return HelpersManagement.get_backup_config(server_id)

    def set_backup_config(
        self,
        server_id: int,
        backup_path: str = None,
        max_backups: int = None,
        excluded_dirs: list = None,
        compress: bool = False,
        shutdown: bool = False,
        before: str = "",
        after: str = "",
    ):
        return self.management_helper.set_backup_config(
            server_id,
            backup_path,
            max_backups,
            excluded_dirs,
            compress,
            shutdown,
            before,
            after,
        )

    @staticmethod
    def get_excluded_backup_dirs(server_id: int):
        return HelpersManagement.get_excluded_backup_dirs(server_id)

    def add_excluded_backup_dir(self, server_id: int, dir_to_add: str):
        self.management_helper.add_excluded_backup_dir(server_id, dir_to_add)

    def del_excluded_backup_dir(self, server_id: int, dir_to_del: str):
        self.management_helper.del_excluded_backup_dir(server_id, dir_to_del)
