import logging
import datetime
import typing as t
from peewee import (
    UUIDField,
    CharField,
    # AutoField,
    DateTimeField,
    BooleanField,
    IntegerField,
    ForeignKeyField,
)
from playhouse.shortcuts import model_to_dict

from app.classes.shared.main_models import DatabaseShortcuts
from app.classes.models.base_model import BaseModel
from app.classes.models.users import Users
from app.classes.shared.helpers import Helpers

logger = logging.getLogger(__name__)


# **********************************************************************************
#                                   Servers Model
# **********************************************************************************
class Servers(BaseModel):
    server_uuid = UUIDField(
        primary_key=True, unique=True, default=Helpers.create_uuid()
    )
    created = DateTimeField(default=datetime.datetime.now)
    server_name = CharField(default="Server", index=True)
    path = CharField(default="")
    backup_path = CharField(default="")
    executable = CharField(default="")
    log_path = CharField(default="")
    execution_command = CharField(default="")
    auto_start = BooleanField(default=0)
    auto_start_delay = IntegerField(default=10)
    crash_detection = BooleanField(default=0)
    stop_command = CharField(default="stop")
    executable_update_url = CharField(default="")
    server_ip = CharField(default="127.0.0.1")
    server_port = IntegerField(default=25565)
    logs_delete_after = IntegerField(default=0)
    type = CharField(default="minecraft-java")
    show_status = BooleanField(default=1)
    created_by = ForeignKeyField(Users, backref="creator_server", null=True)
    shutdown_timeout = IntegerField(default=60)
    ignored_exits = CharField(default="0")

    class Meta:
        table_name = "servers"


# **********************************************************************************
#                                   Servers Class
# **********************************************************************************
class HelperServers:
    def __init__(self, database):
        self.database = database

    # **********************************************************************************
    #                                   Generic Servers Methods
    # **********************************************************************************
    @staticmethod
    def create_server(
        name: str,
        server_dir: str,
        backup_path: str,
        server_command: str,
        server_file: str,
        server_log_file: str,
        server_stop: str,
        server_type: str,
        created_by: int,
        server_port: int = 25565,
        server_host: str = "127.0.0.1",
    ) -> int:
        """Create a server in the database

        Args:
            name: The name of the server
            server_dir: The directory where the server is located
            backup_path: The path to the backup folder
            server_command: The command to start the server
            server_file: The name of the server file
            server_log_file: The path to the server log file
            server_stop: This is the command to stop the server
            server_type: This is the type of server you're creating.
            server_port: The port the server will be monitored on, defaults to 25565
            server_host: The host the server will be monitored on, defaults to 127.0.0.1
            show_status: Should Crafty show this server on the public status page

        Returns:
            int: The new server's id

        Raises:
            PeeweeException: If the server already exists
        """
        # return Servers.create(
        #    server_uuid=Helpers.create_uuid(),
        #    server_name=name,
        #    path=server_dir,
        #    executable=server_file,
        #    execution_command=server_command,
        #    auto_start=False,
        #    auto_start_delay=10,
        #    crash_detection=False,
        #    log_path=server_log_file,
        #    server_port=server_port,
        #    server_ip=server_host,
        #    stop_command=server_stop,
        #    backup_path=backup_path,
        #    type=server_type,
        #    created_by=created_by,
        # )

        return Servers.insert(
            {
                Servers.server_uuid: Helpers.create_uuid(),
                Servers.server_name: name,
                Servers.path: server_dir,
                Servers.executable: server_file,
                Servers.execution_command: server_command,
                Servers.auto_start: False,
                Servers.auto_start_delay: 10,
                Servers.crash_detection: False,
                Servers.log_path: server_log_file,
                Servers.server_port: server_port,
                Servers.server_ip: server_host,
                Servers.stop_command: server_stop,
                Servers.backup_path: backup_path,
                Servers.type: server_type,
                Servers.created_by: created_by,
            }
        ).execute()

    @staticmethod
    def get_server_obj(server_uuid):
        return Servers.get_by_id(server_uuid)

    @staticmethod
    def get_total_owned_servers(user_id):
        return Servers.select().where(Servers.created_by == user_id).count()

    @staticmethod
    def get_server_type_by_id(server_uuid):
        server_type = Servers.select().where(Servers.server_uuid == server_uuid).get()
        return server_type.type

    @staticmethod
    def update_server(server_obj):
        return server_obj.save()

    def remove_server(self, server_uuid):
        Servers.delete().where(Servers.server_uuid == server_uuid).execute()

    @staticmethod
    def get_server_data_by_id(server_uuid):
        query = Servers.select().where(Servers.server_uuid == server_uuid).limit(1)
        try:
            return DatabaseShortcuts.return_rows(query)[0]
        except IndexError:
            return {}

    @staticmethod
    def get_server_columns(
        server_uuid: t.Union[str, int], column_names: t.List[str]
    ) -> t.List[t.Any]:
        columns = [getattr(Servers, column) for column in column_names]
        return model_to_dict(
            Servers.select(*columns).where(Servers.server_uuid == server_uuid).get(),
            only=columns,
        )

    @staticmethod
    def get_server_column(server_uuid: t.Union[str, int], column_name: str) -> t.Any:
        column = getattr(Servers, column_name)
        return getattr(
            Servers.select(column).where(Servers.server_uuid == server_uuid).get(),
            column_name,
        )

    # **********************************************************************************
    #                                     Servers Methods
    # **********************************************************************************
    @staticmethod
    def get_all_defined_servers():
        query = Servers.select()
        return DatabaseShortcuts.return_rows(query)

    @staticmethod
    def get_all_server_uuids() -> t.List[int]:
        return [server.server_uuid for server in Servers.select(Servers.server_uuid)]

    @staticmethod
    def get_server_friendly_name(server_uuid):
        server_data = HelperServers.get_server_data_by_id(server_uuid)
        friendly_name = (
            f"{server_data.get('server_name', None)} "
            f"with ID: {server_data.get('server_uuid', 0)}"
        )
        return friendly_name
