import logging
import datetime
from peewee import (
    ForeignKeyField,
    CharField,
    IntegerField,
    DateTimeField,
    FloatField,
    TextField,
    AutoField,
    BooleanField,
)
from playhouse.shortcuts import model_to_dict

from app.classes.models.base_model import BaseModel
from app.classes.models.users import HelperUsers
from app.classes.models.servers import Servers
from app.classes.models.server_permissions import PermissionsServers
from app.classes.shared.main_models import DatabaseShortcuts

logger = logging.getLogger(__name__)

# **********************************************************************************
#                                   Audit_Log Class
# **********************************************************************************
class AuditLog(BaseModel):
    audit_id = AutoField()
    created = DateTimeField(default=datetime.datetime.now)
    user_name = CharField(default="")
    user_id = IntegerField(default=0, index=True)
    source_ip = CharField(default="127.0.0.1")
    server_id = IntegerField(
        default=None, index=True
    )  # When auditing global events, use server ID 0
    log_msg = TextField(default="")

    class Meta:
        table_name = "audit_log"


# **********************************************************************************
#                                Crafty Settings Class
# **********************************************************************************
class CraftySettings(BaseModel):
    secret_api_key = CharField(default="")
    cookie_secret = CharField(default="")
    login_photo = CharField(default="login_1.jpg")
    login_opacity = IntegerField(default=100)

    class Meta:
        table_name = "crafty_settings"


# **********************************************************************************
#                                   Host_Stats Class
# **********************************************************************************
class HostStats(BaseModel):
    time = DateTimeField(default=datetime.datetime.now, index=True)
    boot_time = CharField(default="")
    cpu_usage = FloatField(default=0)
    cpu_cores = IntegerField(default=0)
    cpu_cur_freq = FloatField(default=0)
    cpu_max_freq = FloatField(default=0)
    mem_percent = FloatField(default=0)
    mem_usage = CharField(default="")
    mem_total = CharField(default="")
    disk_json = TextField(default="")

    class Meta:
        table_name = "host_stats"


# **********************************************************************************
#                                   Webhooks Class
# **********************************************************************************
class Webhooks(BaseModel):
    id = AutoField()
    name = CharField(max_length=64, unique=True, index=True)
    method = CharField(default="POST")
    url = CharField(unique=True)
    event = CharField(default="")
    send_data = BooleanField(default=True)

    class Meta:
        table_name = "webhooks"


# **********************************************************************************
#                                   Schedules Class
# **********************************************************************************
class Schedules(BaseModel):
    schedule_id = IntegerField(unique=True, primary_key=True)
    server_id = ForeignKeyField(Servers, backref="schedule_server")
    enabled = BooleanField()
    action = CharField()
    interval = IntegerField()
    interval_type = CharField()
    start_time = CharField(null=True)
    command = CharField(null=True)
    name = CharField()
    one_time = BooleanField(default=False)
    cron_string = CharField(default="")
    parent = IntegerField(null=True)
    delay = IntegerField(default=0)
    next_run = CharField(default="")

    class Meta:
        table_name = "schedules"


# **********************************************************************************
#                                   Backups Class
# **********************************************************************************
class Backups(BaseModel):
    excluded_dirs = CharField(null=True)
    max_backups = IntegerField()
    server_id = ForeignKeyField(Servers, backref="backups_server")
    compress = BooleanField(default=False)
    shutdown = BooleanField(default=False)
    before = CharField(default="")
    after = CharField(default="")

    class Meta:
        table_name = "backups"


class HelpersManagement:
    def __init__(self, database, helper):
        self.database = database
        self.helper = helper

    # **********************************************************************************
    #                                   Host_Stats Methods
    # **********************************************************************************
    @staticmethod
    def get_latest_hosts_stats():
        # pylint: disable=no-member
        query = HostStats.select().order_by(HostStats.id.desc()).get()
        return model_to_dict(query)

    # **********************************************************************************
    #                                   Audit_Log Methods
    # **********************************************************************************
    @staticmethod
    def get_actity_log():
        query = AuditLog.select()
        return DatabaseShortcuts.return_db_rows(query)

    def add_to_audit_log(self, user_id, log_msg, server_id=None, source_ip=None):
        logger.debug(f"Adding to audit log User:{user_id} - Message: {log_msg} ")
        user_data = HelperUsers.get_user(user_id)

        audit_msg = f"{str(user_data['username']).capitalize()} {log_msg}"

        server_users = PermissionsServers.get_server_user_list(server_id)
        for user in server_users:
            try:
                self.helper.websocket_helper.broadcast_user(
                    user, "notification", audit_msg
                )
            except Exception as e:
                logger.error(f"Error broadcasting to user {user} - {e}")

        AuditLog.insert(
            {
                AuditLog.user_name: user_data["username"],
                AuditLog.user_id: user_id,
                AuditLog.server_id: server_id,
                AuditLog.log_msg: audit_msg,
                AuditLog.source_ip: source_ip,
            }
        ).execute()
        # deletes records when there's more than 300
        ordered = AuditLog.select().order_by(+AuditLog.created)
        for item in ordered:
            if not self.helper.get_setting("max_audit_entries"):
                max_entries = 300
            else:
                max_entries = self.helper.get_setting("max_audit_entries")
            if AuditLog.select().count() > max_entries:
                AuditLog.delete().where(AuditLog.audit_id == item.audit_id).execute()
            else:
                return

    def add_to_audit_log_raw(self, user_name, user_id, server_id, log_msg, source_ip):
        AuditLog.insert(
            {
                AuditLog.user_name: user_name,
                AuditLog.user_id: user_id,
                AuditLog.server_id: server_id,
                AuditLog.log_msg: log_msg,
                AuditLog.source_ip: source_ip,
            }
        ).execute()
        # deletes records when there's more than 300
        ordered = AuditLog.select().order_by(+AuditLog.created)
        for item in ordered:
            # configurable through app/config/config.json
            if not self.helper.get_setting("max_audit_entries"):
                max_entries = 300
            else:
                max_entries = self.helper.get_setting("max_audit_entries")
            if AuditLog.select().count() > max_entries:
                AuditLog.delete().where(AuditLog.audit_id == item.audit_id).execute()
            else:
                return

    @staticmethod
    def create_crafty_row():
        CraftySettings.insert(
            {
                CraftySettings.secret_api_key: "",
                CraftySettings.cookie_secret: "",
                CraftySettings.login_photo: "login_1.jpg",
                CraftySettings.login_opacity: 100,
            }
        ).execute()

    @staticmethod
    def set_secret_api_key(key):
        CraftySettings.update({CraftySettings.secret_api_key: key}).where(
            CraftySettings.id == 1
        ).execute()

    @staticmethod
    def get_secret_api_key():
        settings = CraftySettings.select(CraftySettings.secret_api_key).where(
            CraftySettings.id == 1
        )
        return settings[0].secret_api_key

    @staticmethod
    def get_cookie_secret():
        settings = CraftySettings.select(CraftySettings.cookie_secret).where(
            CraftySettings.id == 1
        )
        return settings[0].cookie_secret

    @staticmethod
    def set_cookie_secret(key):
        CraftySettings.update({CraftySettings.cookie_secret: key}).where(
            CraftySettings.id == 1
        ).execute()

    # **********************************************************************************
    #                                  Config Methods
    # **********************************************************************************
    @staticmethod
    def get_login_image():
        settings = CraftySettings.select(CraftySettings.login_photo).where(
            CraftySettings.id == 1
        )
        return settings[0].login_photo

    @staticmethod
    def set_login_image(photo):
        CraftySettings.update({CraftySettings.login_photo: photo}).where(
            CraftySettings.id == 1
        ).execute()

    @staticmethod
    def get_login_opacity():
        settings = CraftySettings.select(CraftySettings.login_opacity).where(
            CraftySettings.id == 1
        )
        return settings[0].login_opacity

    @staticmethod
    def set_login_opacity(opacity):
        CraftySettings.update({CraftySettings.login_opacity: opacity}).where(
            CraftySettings.id == 1
        ).execute()

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
        one_time=False,
        cron_string="* * * * *",
        parent=None,
        delay=0,
    ):
        sch_id = Schedules.insert(
            {
                Schedules.server_id: server_id,
                Schedules.action: action,
                Schedules.enabled: enabled,
                Schedules.interval: interval,
                Schedules.interval_type: interval_type,
                Schedules.start_time: start_time,
                Schedules.command: command,
                Schedules.name: name,
                Schedules.one_time: one_time,
                Schedules.cron_string: cron_string,
                Schedules.parent: parent,
                Schedules.delay: delay,
                Schedules.next_run: "",
            }
        ).execute()
        return sch_id

    @staticmethod
    def delete_scheduled_task(schedule_id):
        return Schedules.delete().where(Schedules.schedule_id == schedule_id).execute()

    @staticmethod
    def update_scheduled_task(schedule_id, updates):
        Schedules.update(updates).where(Schedules.schedule_id == schedule_id).execute()

    @staticmethod
    def delete_scheduled_task_by_server(server_id):
        Schedules.delete().where(Schedules.server_id == int(server_id)).execute()

    @staticmethod
    def get_scheduled_task(schedule_id):
        return model_to_dict(Schedules.get(Schedules.schedule_id == schedule_id))

    @staticmethod
    def get_scheduled_task_model(schedule_id):
        return Schedules.select().where(Schedules.schedule_id == schedule_id).get()

    @staticmethod
    def get_schedules_by_server(server_id):
        return Schedules.select().where(Schedules.server_id == server_id).execute()

    @staticmethod
    def get_child_schedules_by_server(schedule_id, server_id):
        return (
            Schedules.select()
            .where(Schedules.server_id == server_id, Schedules.parent == schedule_id)
            .execute()
        )

    @staticmethod
    def get_child_schedules(schedule_id):
        return Schedules.select().where(Schedules.parent == schedule_id)

    @staticmethod
    def get_schedules_all():
        return Schedules.select().execute()

    @staticmethod
    def get_schedules_enabled():
        return (
            Schedules.select()
            .where(Schedules.enabled == True)  # pylint: disable=singleton-comparison
            .execute()
        )

    # **********************************************************************************
    #                                   Backups Methods
    # **********************************************************************************
    @staticmethod
    def get_backup_config(server_id):
        try:
            row = (
                Backups.select().where(Backups.server_id == server_id).join(Servers)[0]
            )
            conf = {
                "backup_path": row.server_id.backup_path,
                "excluded_dirs": row.excluded_dirs,
                "max_backups": row.max_backups,
                "server_id": row.server_id_id,
                "compress": row.compress,
                "shutdown": row.shutdown,
                "before": row.before,
                "after": row.after,
            }
        except IndexError:
            conf = {
                "backup_path": None,
                "excluded_dirs": None,
                "max_backups": 0,
                "server_id": server_id,
                "compress": False,
                "shutdown": False,
                "before": "",
                "after": "",
            }
        return conf

    @staticmethod
    def remove_backup_config(server_id):
        Backups.delete().where(Backups.server_id == server_id).execute()

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
        logger.debug(f"Updating server {server_id} backup config with {locals()}")
        if Backups.select().where(Backups.server_id == server_id).exists():
            new_row = False
            conf = {}
        else:
            conf = {
                "excluded_dirs": None,
                "max_backups": 0,
                "server_id": server_id,
                "compress": False,
                "shutdown": False,
                "before": "",
                "after": "",
            }
            new_row = True
        if max_backups is not None:
            conf["max_backups"] = max_backups
        if excluded_dirs is not None:
            dirs_to_exclude = ",".join(excluded_dirs)
            conf["excluded_dirs"] = dirs_to_exclude
        conf["compress"] = compress
        conf["shutdown"] = shutdown
        conf["before"] = before
        conf["after"] = after
        if not new_row:
            with self.database.atomic():
                if backup_path is not None:
                    server_rows = (
                        Servers.update(backup_path=backup_path)
                        .where(Servers.server_id == server_id)
                        .execute()
                    )
                else:
                    server_rows = 0
                backup_rows = (
                    Backups.update(conf).where(Backups.server_id == server_id).execute()
                )
            logger.debug(
                f"Updating existing backup record. "
                f"{server_rows}+{backup_rows} rows affected"
            )
        else:
            with self.database.atomic():
                conf["server_id"] = server_id
                if backup_path is not None:
                    Servers.update(backup_path=backup_path).where(
                        Servers.server_id == server_id
                    )
                Backups.create(**conf)
            logger.debug("Creating new backup record.")

    @staticmethod
    def get_excluded_backup_dirs(server_id: int):
        excluded_dirs = HelpersManagement.get_backup_config(server_id)["excluded_dirs"]
        if excluded_dirs is not None and excluded_dirs != "":
            dir_list = excluded_dirs.split(",")
        else:
            dir_list = []
        return dir_list

    def add_excluded_backup_dir(self, server_id: int, dir_to_add: str):
        dir_list = self.get_excluded_backup_dirs(server_id)
        if dir_to_add not in dir_list:
            dir_list.append(dir_to_add)
            excluded_dirs = ",".join(dir_list)
            self.set_backup_config(server_id=server_id, excluded_dirs=excluded_dirs)
        else:
            logger.debug(
                f"Not adding {dir_to_add} to excluded directories - "
                f"already in the excluded directory list for server ID {server_id}"
            )

    def del_excluded_backup_dir(self, server_id: int, dir_to_del: str):
        dir_list = self.get_excluded_backup_dirs(server_id)
        if dir_to_del in dir_list:
            dir_list.remove(dir_to_del)
            excluded_dirs = ",".join(dir_list)
            self.set_backup_config(server_id=server_id, excluded_dirs=excluded_dirs)
        else:
            logger.debug(
                f"Not removing {dir_to_del} from excluded directories - "
                f"not in the excluded directory list for server ID {server_id}"
            )
